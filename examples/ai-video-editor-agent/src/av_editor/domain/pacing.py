"""Pacing + style domain models (§3, §3.10)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeadSpaceScore(BaseModel):
    t: float
    value: float
    silence_excess: float = 0.0
    low_visual_motion: float = 0.0
    low_speech_density: float = 0.0
    low_focal_change: float = 0.0
    low_semantic_progress: float = 0.0
    emotional_hold: bool = False
    comedic_window: bool = False
    evidence_ids: list[str] = Field(default_factory=list)


class HookScore(BaseModel):
    value: float
    visual_change_first5s: float = 0.0
    speech_onset_density: float = 0.0
    face_presence: float = 0.0
    motion_energy_first5s: float = 0.0
    text_or_caption_presence: float = 0.0
    loudness_delta: float = 0.0
    niche_hook_pattern_fit: float = 0.5
    weak: bool = False
    evidence_ids: list[str] = Field(default_factory=list)


InterruptType = Literal["hard_cut", "punch_in", "punch_out", "broll_insert", "caption_pop",
                        "keyword_animation", "sfx_accent", "music_change", "zoom_move",
                        "reframe", "screen_element", "j_cut", "l_cut"]


class InterruptNeed(BaseModel):
    t: float
    value: float
    time_since_last_interrupt_pressure: float = 0.0
    energy_decline: float = 0.0
    low_visual_novelty: float = 0.0
    speech_segment_boundary: float = 0.0
    style_cadence_pressure: float = 0.0
    retention_risk: float = 0.0
    emotional_hold: bool = False
    hold_delay_seconds: float = 0.0


class ScheduledInterrupt(BaseModel):
    interrupt_id: str
    t: float
    kind: InterruptType
    duration_seconds: float = 0.25
    strength: Literal["soft", "strong"] = "strong"
    tied_keyword: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    delay_reason: str | None = None


class CutPointCandidate(BaseModel):
    t: float
    score: float
    anchors: list[str] = Field(default_factory=list)   # e.g. ["sentence_boundary","audio_onset"]
    components: dict[str, float] = Field(default_factory=dict)
    hard_constraint_violations: list[str] = Field(default_factory=list)
    transient_sync_score: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)


class JLCutPlan(BaseModel):
    cut_index: int
    kind: Literal["j_cut", "l_cut", "hard"]
    offset_ms: int = 0
    rationale: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class RetentionRisk(BaseModel):
    t: float
    risk: float
    drivers: dict[str, float] = Field(default_factory=dict)


class NicheSubtitleStyle(BaseModel):
    cps_target: float = 15.0
    max_lines: int = 2
    placement_bias: Literal["bottom", "top", "dynamic"] = "bottom"
    keyword_emphasis: bool = True
    animation_intensity: float = 0.4


class NicheAudioStyle(BaseModel):
    speech_lufs_target: float = -14.0
    music_ducking_db: float = 12.0
    sfx_density_per_minute: float = 4.0


class NicheHookStyle(BaseModel):
    cold_open_allowed: bool = True
    caption_in_first_second: bool = True
    visual_energy_target: float = 0.65


class NicheInterruptStyle(BaseModel):
    min_interval_seconds: float = 3.0
    max_interval_seconds: float = 7.0
    max_strong_interrupts_per_minute: int = 12


class NicheColorStyle(BaseModel):
    palette: list[str] = Field(default_factory=list)
    contrast_preference: float = 0.5


class SourceReference(BaseModel):
    reference_id: str
    label: str
    origin: Literal["user_local_file", "official_api_metadata", "user_analytics_export",
                    "authorized_scrape"]
    licensed: bool = False
    notes: str = ""


class NicheStyleProfile(BaseModel):
    """Machine-readable style profile distilled from benchmarks (LAW 4 / §3.10)."""

    niche_id: str
    niche_name: str
    source_references: list[SourceReference] = Field(default_factory=list)
    cut_frequency_per_minute: float = 0.0
    median_shot_length_seconds: float = 0.0
    shot_length_histogram: list[float] = Field(default_factory=list)
    broll_density: float = 0.0
    subtitle_present_ratio: float = 0.0
    subtitle_style: NicheSubtitleStyle = Field(default_factory=NicheSubtitleStyle)
    audio_style: NicheAudioStyle = Field(default_factory=NicheAudioStyle)
    hook_style: NicheHookStyle = Field(default_factory=NicheHookStyle)
    interrupt_style: NicheInterruptStyle = Field(default_factory=NicheInterruptStyle)
    color_style: NicheColorStyle = Field(default_factory=NicheColorStyle)
    chars_per_second: float = 0.0
    typography_placement_heatmap: list[list[float]] = Field(default_factory=list)
    keyword_density: dict[str, float] = Field(default_factory=dict)
    sfx_density_per_minute: float = 0.0
    music_ducking_curve: list[dict[str, float]] = Field(default_factory=list)
    first5s_hook_energy: float = 0.0
    motion_energy_distribution: list[float] = Field(default_factory=list)
    framing_tendencies: dict[str, float] = Field(default_factory=dict)
    interrupt_cadence_seconds: float = 5.0
    retention_findings: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str = ""
