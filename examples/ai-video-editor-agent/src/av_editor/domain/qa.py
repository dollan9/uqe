"""QA domain models (§4)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class InspectionFrame(BaseModel):
    frame_id: str
    path: str
    timeline_time: float
    source_asset_id: str | None = None
    mode: Literal["around_cut", "subtitle", "transition", "broll_window",
                  "hook_window", "full_sparse"] = "full_sparse"
    context: dict[str, Any] = Field(default_factory=dict)  # sidecar JSON content (§4.1)


class DeterministicCheckResult(BaseModel):
    check: str
    passed: bool
    severity: Literal["critical", "high", "medium", "low", "info"] = "info"
    detail: str = ""
    frame_id: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class QACycleReport(BaseModel):
    cycle: int
    frames_rendered: int
    deterministic_results: list[DeterministicCheckResult] = Field(default_factory=list)
    vlm_critiques: list[dict[str, Any]] = Field(default_factory=list)
    violations: list[dict[str, Any]] = Field(default_factory=list)
    patches_proposed: list[dict[str, Any]] = Field(default_factory=list)
    patches_applied: list[dict[str, Any]] = Field(default_factory=list)
    approved: bool = False
    human_review_required: bool = False
