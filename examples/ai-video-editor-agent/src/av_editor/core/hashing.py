"""Hashing helpers for cache keys, checksums and config identity (§6.5).

Cache invalidation triggers: media checksum change, config hash change, module
version change, VLM model change, prompt version change.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

import orjson

CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Streaming SHA-256 of a file (media checksum validation)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            data = fh.read(CHUNK)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON encoding used for parameter hashing."""
    return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS | orjson.OPT_NON_STR_KEYS)


def config_hash(config_dump: dict[str, Any]) -> str:
    """Stable hash over the full resolved configuration."""
    return sha256_bytes(canonical_json(config_dump))[:16]


def parameter_hash(params: Iterable[tuple[str, Any]]) -> str:
    return sha256_bytes(canonical_json(dict(params)))[:16]


def cache_key(*, asset_checksum: str, cfg_hash: str, module: str,
              module_version: str, params_digest: str) -> str:
    """Compose a §6.5 cache key: checksum + config + module@version + params."""
    return sha256_bytes(canonical_json({
        "asset": asset_checksum,
        "config": cfg_hash,
        "module": module,
        "module_version": module_version,
        "params": params_digest,
    }))[:32]


def short_hash(text: str, length: int = 8) -> str:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=max(4, length // 2)).hexdigest()
