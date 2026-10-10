"""Evidence and event model (§1.6).

Every ``EditDecision`` must reference at least one ``Evidence`` id — enforced by
model validation, implementing LAW 1 ("no edit without evidence") at the schema
level so it cannot be bypassed by any agent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class EvidenceType(str, Enum):
    """The nine admissible evidence families (LAW 1)."""

    TRANSCRIPT = "transcript"
    AUDIO_TRANSIENT = "audio_transient"
    VISUAL_SHOT_BOUNDARY = "visual_shot_boundary"
    FACE_GAZE = "face_gaze"
    MOTION_VECTOR = "motion_vector"
    COMPOSITION = "composition"
    VLM_SEMANTIC = "vlm_semantic"
    BENCHMARK_STYLE = "benchmark_style"
    USER_RETENTION = "user_retention"
    AUDIO_LOUDNESS = "audio_loudness"
    PAUSE_POLICY = "pause_policy"
    LICENSE = "license"


class TimeRange(BaseModel):
    start: float = Field(ge=0, description="seconds")
    end: float = Field(ge=0, description="seconds")

    @model_validator(mode="after")
    def _ordered(self) -> "TimeRange":
        if self.end < self.start:
            raise ValueError("TimeRange end must be >= start")
        return self

    @property
    def duration(self) -> float:
        return self.end - self.start

    def overlaps(self, other: "TimeRange", tolerance: float = 0.0) -> bool:
        return not (self.end + tolerance < other.start or other.end + tolerance < self.start)


class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: new_id("ev"))
    type: EvidenceType
    source_agent: str
    time_range: TimeRange | None = None
    asset_id: str | None = None
    frame_index: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("confidence")
    @classmethod
    def _sane_confidence(cls, v: float) -> float:
        return v


class ActionType(str, Enum):
    CUT = "cut"
    TRIM_START = "trim_start"
    TRIM_END = "trim_end"
    REMOVE_PAUSE = "remove_pause"
    SHORTEN_PAUSE = "shorten_pause"
    PRESERVE_PAUSE = "preserve_pause"
    J_CUT = "j_cut"
    L_CUT = "l_cut"
    PUNCH_IN = "punch_in"
    PUNCH_OUT = "punch_out"
    BROLL_INSERT = "broll_insert"
    BROLL_REMOVE = "broll_remove"
    CAPTION_POP = "caption_pop"
    KEYWORD_ANIMATION = "keyword_animation"
    SFX_ACCENT = "sfx_accent"
    MUSIC_CHANGE = "music_change"
    ZOOM_MOVE = "zoom_move"
    REFRAME = "reframe"
    SUBTITLE_ADD = "subtitle_add"
    SUBTITLE_MOVE = "subtitle_move"
    SUBTITLE_RESTYLE = "subtitle_restyle"
    DUCKING_APPLY = "ducking_apply"
    GAIN_ADJUST = "gain_adjust"
    CROSSFADE = "crossfade"
    COLOR_APPLY = "color_apply"
    HOOK_RESTRUCTURE = "hook_restructure"
    COLD_OPEN_TEASE = "cold_open_tease"
    TRANSITION_ADD = "transition_add"
    PATCH = "patch"
    NO_EDIT = "no_edit"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EditDecision(BaseModel):
    """A single editorial decision with mandatory evidence linkage (LAW 1)."""

    decision_id: str = Field(default_factory=lambda: new_id("dec"))
    timeline_id: str
    source_asset_id: str | None = None
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    action_type: ActionType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_retention_effect: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    reversible: bool = True
    edit_score: float | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _validate(self) -> "EditDecision":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be >= start_time")
        if not self.evidence_ids:
            raise ValueError("EditDecision requires at least one evidence_id (LAW 1)")
        return self


class TimelineMutation(BaseModel):
    mutation_id: str = Field(default_factory=lambda: new_id("mut"))
    timeline_id: str
    decision_id: str
    operation: Literal["insert_item", "remove_item", "move_item", "trim_item",
                       "add_track", "set_marker", "update_cue", "update_bus", "update_effect"]
    target_item_id: str | None = None
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    applied_at: datetime = Field(default_factory=utcnow)


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QAViolation(BaseModel):
    violation_id: str = Field(default_factory=lambda: new_id("vio"))
    category: str
    severity: Severity
    description: str
    timeline_id: str
    time_range: TimeRange | None = None
    frame_path: str | None = None
    bounding_box: tuple[float, float, float, float] | None = Field(
        default=None, description="normalized x0, y0, x1, y1")
    detector: Literal["deterministic", "vlm", "merged"] = "deterministic"
    suggested_fix: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class PatchProposal(BaseModel):
    patch_id: str = Field(default_factory=lambda: new_id("pat"))
    violation_id: str
    timeline_id: str
    action: ActionType
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    predicted_edit_score_delta: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)
    approved: bool | None = None
    applied: bool = False


class DecisionLedgerEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: new_id("led"))
    run_id: str
    timeline_id: str
    decision_id: str
    agent_name: str
    summary: str
    edit_score: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    rejected: bool = False
    rejection_reason: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class AgentTask(BaseModel):
    task_id: str = Field(default_factory=lambda: new_id("task"))
    agent_name: str
    stage: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = ""


class AgentResult(BaseModel):
    task_id: str
    agent_name: str
    stage: str
    outcome: Literal["success", "failed", "skipped", "cached"]
    outputs: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    error: dict[str, Any] | None = None
    duration_ms: float = 0.0
    finished_at: datetime = Field(default_factory=utcnow)
