"""Audio-domain models (§2.7): loudness, pauses, transients, pause policy."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LoudnessSnapshot(BaseModel):
    time: float
    momentary_lufs: float
    short_term_lufs: float


class LoudnessReport(BaseModel):
    asset_id: str
    integrated_lufs: float
    true_peak_dbtp: float
    dynamic_range_db: float
    momentary_max_lufs: float = 0.0
    speech_integrated_lufs: float | None = None
    music_integrated_lufs: float | None = None
    sfx_peak_dbtp: float | None = None
    snapshots: list[LoudnessSnapshot] = Field(default_factory=list)


class SilenceRegion(BaseModel):
    start: float
    end: float
    kind: Literal["absolute_silence", "low_energy_pause", "breath", "mouth_noise",
                  "long_pause", "sentence_final_pause"] = "low_energy_pause"
    rms_dbfs: float = -60.0
    evidence_ids: list[str] = Field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(self.end - self.start, 0.0)


class AudioTransient(BaseModel):
    time: float
    strength: float
    type: Literal["onset", "beat", "impact", "speech_start"] = "onset"
    frequency_band: str = "wide"
    source: str = "librosa"
    evidence_ids: list[str] = Field(default_factory=list)


PauseDecision = Literal["remove", "shorten", "preserve"]


class PausePolicyEntry(BaseModel):
    pause_id: str
    start_time: float
    end_time: float
    duration: float
    context_type: Literal["emotional_hold", "comedic_timing", "payoff_setup",
                          "direct_gaze", "nonverbal_action", "dead_air", "breath",
                          "sentence_boundary", "unknown"] = "unknown"
    decision: PauseDecision
    target_duration: float | None = None
    gain_reduction_db: float | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class VocalActivity(BaseModel):
    """Simple VAD result used by the pause/dead-space engine."""

    start: float
    end: float
    probability: float = 1.0
