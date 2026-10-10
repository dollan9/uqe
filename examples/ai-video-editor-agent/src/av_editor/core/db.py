"""SQLite pipeline state store (§6.5).

Tables: runs, assets, analysis_jobs, evidence, decisions, timelines,
qa_violations, patches, exports. Used for resumability, idempotency and audit.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import orjson

from av_editor.logging import get_logger

log = get_logger("av_editor.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    current_stage TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    phash TEXT,
    media_type TEXT NOT NULL,
    duration REAL,
    json TEXT NOT NULL,
    UNIQUE(run_id, checksum)
);
CREATE TABLE IF NOT EXISTS analysis_jobs (
    job_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    asset_id TEXT,
    module TEXT NOT NULL,
    cache_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT,
    finished_at TEXT,
    result_path TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    type TEXT NOT NULL,
    source_agent TEXT NOT NULL,
    asset_id TEXT,
    t0 REAL, t1 REAL,
    confidence REAL,
    json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    start_time REAL, end_time REAL,
    confidence REAL,
    risk_level TEXT,
    edit_score REAL,
    json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS timelines (
    timeline_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 0,
    path TEXT NOT NULL,
    duration REAL,
    qa_approved INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS qa_violations (
    violation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    detector TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patches (
    patch_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    violation_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    approved INTEGER,
    applied INTEGER NOT NULL DEFAULT 0,
    json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exports (
    export_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    timeline_id TEXT NOT NULL,
    target TEXT NOT NULL,
    path TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_run ON analysis_jobs(run_id);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence(run_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tl ON decisions(timeline_id);
"""


class PipelineDB:
    """Thin typed wrapper over SQLite with JSON payload columns."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- runs ---------------------------------------------------------------
    def create_run(self, run_id: str, config_hash: str, mode: str, created_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs(run_id, created_at, config_hash, mode) VALUES(?,?,?,?)",
                (run_id, created_at, config_hash, mode))

    def set_run_stage(self, run_id: str, stage: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE runs SET current_stage=? WHERE run_id=?", (stage, run_id))

    def finish_run(self, run_id: str, status: str, error: str | None = None) -> None:
        with self._conn() as c:
            c.execute("UPDATE runs SET status=?, error=? WHERE run_id=?", (status, error, run_id))

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            return dict(row) if row else None

    # -- jobs / cache -------------------------------------------------------
    def job_status(self, cache_key: str) -> tuple[str, str | None] | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT status, result_path FROM analysis_jobs WHERE cache_key=?",
                (cache_key,)).fetchone()
            return (row["status"], row["result_path"]) if row else None

    def start_job(self, job_id: str, run_id: str, cache_key: str, module: str,
                  asset_id: str | None, started_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO analysis_jobs"
                "(job_id, run_id, asset_id, module, cache_key, status, started_at)"
                " VALUES(?,?,?,?,?,'running',?)",
                (job_id, run_id, asset_id, module, cache_key, started_at))

    def complete_job(self, cache_key: str, result_path: str | None, finished_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE analysis_jobs SET status='done', result_path=?, finished_at=? "
                "WHERE cache_key=?", (result_path, finished_at, cache_key))

    def fail_job(self, cache_key: str, error: str, finished_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE analysis_jobs SET status='failed', error=?, finished_at=? "
                "WHERE cache_key=?", (error, finished_at, cache_key))

    def jobs_for_checksum(self, checksum: str) -> list[tuple[str, str | None]]:
        """Return (cache_key, result_path) for all jobs of assets with this checksum."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT j.cache_key, j.result_path FROM analysis_jobs j "
                "JOIN assets a ON a.asset_id = j.asset_id WHERE a.checksum = ?",
                (checksum,)).fetchall()
            return [(row["cache_key"], row["result_path"]) for row in rows]

    def delete_jobs_for_checksum(self, checksum: str) -> int:
        """Delete all job rows for assets with this checksum; returns row count."""
        with self._conn() as c:
            cur = c.execute(
                "DELETE FROM analysis_jobs WHERE asset_id IN "
                "(SELECT asset_id FROM assets WHERE checksum = ?)", (checksum,))
            return cur.rowcount

    # -- records ------------------------------------------------------------
    def insert_evidence(self, run_id: str, evidence_json: dict[str, Any]) -> None:
        with self._conn() as c:
            tr = evidence_json.get("time_range") or {}
            c.execute(
                "INSERT OR REPLACE INTO evidence(evidence_id, run_id, type, source_agent,"
                " asset_id, t0, t1, confidence, json) VALUES(?,?,?,?,?,?,?,?,?)",
                (evidence_json["evidence_id"], run_id, evidence_json["type"],
                 evidence_json["source_agent"], evidence_json.get("asset_id"),
                 tr.get("start"), tr.get("end"), evidence_json.get("confidence"),
                 orjson.dumps(evidence_json).decode()))

    def insert_decision(self, run_id: str, decision_json: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO decisions(decision_id, run_id, timeline_id, action_type,"
                " start_time, end_time, confidence, risk_level, edit_score, json)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (decision_json["decision_id"], run_id, decision_json["timeline_id"],
                 decision_json["action_type"], decision_json["start_time"],
                 decision_json["end_time"], decision_json["confidence"],
                 decision_json.get("risk_level"), decision_json.get("edit_score"),
                 orjson.dumps(decision_json).decode()))

    def insert_asset(self, run_id: str, asset_json: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO assets(asset_id, run_id, path, checksum, phash,"
                " media_type, duration, json) VALUES(?,?,?,?,?,?,?,?)",
                (asset_json["asset_id"], run_id, asset_json["original_path"],
                 asset_json["checksum_sha256"], asset_json.get("phash"),
                 asset_json["media_type"], asset_json["duration_seconds"],
                 orjson.dumps(asset_json).decode()))

    def upsert_timeline(self, run_id: str, timeline_id: str, path: str, duration: float,
                        updated_at: str, qa_approved: bool) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO timelines(timeline_id, run_id, version, path, duration,"
                " qa_approved, updated_at) VALUES(?,?,1,?,?,?,?)"
                " ON CONFLICT(timeline_id) DO UPDATE SET version=version+1, path=excluded.path,"
                " duration=excluded.duration, qa_approved=excluded.qa_approved,"
                " updated_at=excluded.updated_at",
                (timeline_id, run_id, path, duration, int(qa_approved), updated_at))

    def insert_violation(self, run_id: str, timeline_id: str, cycle: int,
                         vio_json: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO qa_violations(violation_id, run_id, timeline_id, cycle,"
                " category, severity, detector, json) VALUES(?,?,?,?,?,?,?,?)",
                (vio_json["violation_id"], run_id, timeline_id, cycle,
                 vio_json["category"], vio_json["severity"], vio_json.get("detector", "deterministic"),
                 orjson.dumps(vio_json).decode()))

    def insert_patch(self, run_id: str, patch_json: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO patches(patch_id, run_id, violation_id, timeline_id,"
                " approved, applied, json) VALUES(?,?,?,?,?,?,?)",
                (patch_json["patch_id"], run_id, patch_json["violation_id"],
                 patch_json["timeline_id"], patch_json.get("approved"),
                 int(bool(patch_json.get("applied"))), orjson.dumps(patch_json).decode()))

    def record_export(self, export_id: str, run_id: str, timeline_id: str, target: str,
                      path: str, status: str, created_at: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO exports(export_id, run_id, timeline_id, target, path,"
                " status, created_at) VALUES(?,?,?,?,?,?,?)",
                (export_id, run_id, timeline_id, target, path, status, created_at))

    def list_evidence_ids(self, run_id: str) -> set[str]:
        with self._conn() as c:
            rows = c.execute("SELECT evidence_id FROM evidence WHERE run_id=?", (run_id,)).fetchall()
            return {r["evidence_id"] for r in rows}

    def list_decisions(self, run_id: str) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT json FROM decisions WHERE run_id=? ORDER BY start_time", (run_id,)).fetchall()
            return [orjson.loads(r["json"]) for r in rows]
