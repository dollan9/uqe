"""Pipeline state (§1.3): the typed payload flowing between LangGraph nodes.

``PipelineState`` is intentionally a Pydantic model with JSON-serializable
fields so it can be checkpointed to disk for resume, and mirrored into the
LangGraph state dict (which uses plain dicts).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import orjson
from pydantic import BaseModel, Field

from av_editor.core.scheduler import Stage
from av_editor.domain.evidence import EditDecision, Evidence
from av_editor.domain.media import MediaAsset
from av_editor.domain.pacing import NicheStyleProfile
from av_editor.domain.timeline import CanonicalTimeline


class PipelineState(BaseModel):
    run_id: str
    mode: Literal["fresh", "resume", "partial_rerun", "dry_run", "audit_only"] = "fresh"
    config_path: str
    completed_stages: list[Stage] = Field(default_factory=list)
    skipped_stages: list[Stage] = Field(default_factory=list)
    route_override: str | None = None  # conditional edge target set by critic/compliance
    assets: dict[str, MediaAsset] = Field(default_factory=dict)
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    decisions: dict[str, EditDecision] = Field(default_factory=dict)
    timeline: CanonicalTimeline | None = None
    style_profile: NicheStyleProfile | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)   # stage -> artifact path
    qc_cycle: int = 0
    patch_attempts: int = 0
    human_review_required: bool = False
    compliance_failure: str | None = None
    vision_unavailable: str | None = None
    final_report_path: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)

    # -- persistence --------------------------------------------------------
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(self.model_dump_json().encode("utf-8"))
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "PipelineState":
        return cls.model_validate(orjson.loads(path.read_bytes()))

    def add_evidence(self, ev: Evidence) -> None:
        self.evidence[ev.evidence_id] = ev

    def add_decision(self, dec: EditDecision) -> None:
        self.decisions[dec.decision_id] = dec

    def has_stage(self, stage: Stage) -> bool:
        return stage in self.completed_stages
