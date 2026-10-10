"""Content-addressed analysis cache (§6.5, §6.9).

Cache keys combine: asset checksum + config hash + module name + module
version + parameter digest. Entries are JSON artifacts under the cache dir;
the DB records job status for resumability. A cached hit is only valid when
both the DB row says ``done`` and the artifact file exists.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable

import orjson

from av_editor import MODULE_VERSION
from av_editor.core.db import PipelineDB
from av_editor.core.hashing import cache_key, config_hash, parameter_hash
from av_editor.domain.evidence import new_id, utcnow
from av_editor.logging import get_logger

log = get_logger("av_editor.cache")


class AnalysisCache:
    def __init__(self, cache_dir: Path, db: PipelineDB, run_id: str,
                 cfg_dump: dict[str, Any], seed: int = 1337) -> None:
        self.root = cache_dir / "analysis"
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = db
        self.run_id = run_id
        self.cfg_hash = config_hash(cfg_dump)
        random.seed(seed)  # reproducible jitter (§6.9)

    def key(self, *, asset_checksum: str, module: str, params: dict[str, Any] | None = None,
             version: str = MODULE_VERSION) -> str:
        return cache_key(
            asset_checksum=asset_checksum,
            cfg_hash=self.cfg_hash,
            module=module,
            module_version=version,
            params_digest=parameter_hash(sorted((params or {}).items())),
        )

    def path_for(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> Any | None:
        status = self.db.job_status(key)
        if not status or status[0] != "done":
            return None
        p = self.path_for(key)
        if not p.exists():
            log.warning("cache_artifact_missing", key=key[:8])
            return None
        return orjson.loads(p.read_bytes())

    def put(self, key: str, payload: Any) -> Path:
        p = self.path_for(key)
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS))
        tmp.replace(p)  # atomic on POSIX; idempotent writes
        self.db.complete_job(key, str(p), utcnow().isoformat())
        return p

    def memoized(self, *, asset_checksum: str, module: str,
                 params: dict[str, Any] | None,
                 compute: Callable[[], Any],
                 asset_id: str | None = None) -> tuple[Any, bool]:
        """Return (value, cache_hit). Marks jobs in DB for resume support.

        Pass ``asset_id`` when known so :meth:`invalidate_asset` can later
        find and drop this job through the assets table.
        """
        key = self.key(asset_checksum=asset_checksum, module=module, params=params)
        hit = self.get(key)
        if hit is not None:
            log.info("cache_hit", module=module, key=key[:8])
            return hit, True
        self.db.start_job(new_id("job"), self.run_id, key, module, asset_id, utcnow().isoformat())
        try:
            value = compute()
        except Exception as exc:
            self.db.fail_job(key, str(exc), utcnow().isoformat())
            raise
        self.put(key, value)
        log.info("cache_miss_computed", module=module, key=key[:8])
        return value, False

    def invalidate_asset(self, asset_checksum: str) -> int:
        """Invalidate all cached analysis jobs for one asset.

        Cache keys are content-addressed hashes and cannot be reversed to a
        checksum, so invalidation works through the DB: every job row whose
        ``asset_id`` belongs to an asset with this checksum is deleted (and
        its artifact file removed when present). :meth:`get` only trusts
        ``done`` rows, so removing them makes entries recomputable on next
        access. For a full wipe use :meth:`clear`.
        """
        jobs = self.db.jobs_for_checksum(asset_checksum)
        removed = 0
        for cache_key_str, result_path in jobs:
            if result_path:
                p = Path(result_path)
                if p.exists():
                    p.unlink()
            removed += 1
        self.db.delete_jobs_for_checksum(asset_checksum)
        log.info("cache_invalidated", checksum=asset_checksum[:12], rows=removed)
        return removed

    def clear(self) -> None:
        for f in self.root.glob("*.json"):
            f.unlink()
        log.info("cache_cleared", root=str(self.root))
