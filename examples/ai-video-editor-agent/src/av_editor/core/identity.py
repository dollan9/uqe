"""Identity helpers: run ids, asset ids and sanitized filesystem names (§6.10).

Filename sanitization prevents path traversal when building cache/export paths
from user-supplied strings.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{ts}_{uuid.uuid4().hex[:8]}"


def new_asset_id(path: Path) -> str:
    stem = sanitize_name(path.stem)
    return f"asset_{stem}_{uuid.uuid4().hex[:8]}"


def sanitize_name(name: str, max_len: int = 80) -> str:
    """Strip anything unsafe; never allow separators or dot-only segments."""
    cleaned = _SAFE_RE.sub("_", name).strip("._-") or "unnamed"
    return cleaned[:max_len]


def safe_join(base: Path, *parts: str) -> Path:
    """Join path parts ensuring the result stays under ``base`` (traversal guard)."""
    resolved_base = base.resolve()
    candidate = (resolved_base / Path(*[sanitize_name(p) for p in parts])).resolve() if parts else resolved_base
    # os.path.commonpath-based containment check; a plain str.startswith test
    # would wrongly accept siblings like /base_evil when base is /base.
    try:
        inside = os.path.commonpath([resolved_base, candidate]) == str(resolved_base)
    except ValueError:  # different drives on Windows
        inside = False
    if not inside:
        raise ValueError(f"Path traversal blocked: {candidate} outside {resolved_base}")
    return candidate
