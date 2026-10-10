"""Canonical timeline model (§5.1) — the single source of truth for all exports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from av_editor.domain.evidence import TimeRange, new_id, utcnow

TrackKind = Literal["video", "audio", "subtitle", "effect", "marker"]
TrackRole = Literal["primary", "broll", "caption", "music", "sfx", "vo", "composite"]
MarkerKind = Literal["hook", "interrupt", "payoff", "sfx", "caption", "risk", "qa", "chapter"]


class Transition(BaseModel):
    transition_id: str = Field(default_factory=lambda: new_id("trn"))
    kind: Literal["cut", "crossfade", "dip_to_black", "whip_pan", "zoom_blur", "wipe"] = "cut"
    duration_seconds: float = Field(ge=0, default=0.0)
    easing: str = "linear"


class ItemEffect(BaseModel):
    effect_id: str = Field(default_factory=lambda: new_id("fx"))
    kind: Literal["punch_in", "reframe", "crop", "zoom_move", "lut", "cdl",
                  "animation", "background_box", "gain", "eq"]
    parameters: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class TimelineItem(BaseModel):
    item_id: str = Field(default_factory=lambda: new_id("itm"))
    track_id: str
    asset_id: str | None = None
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    speed: float = 1.0
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    blend_mode: str = "normal"
    transition_in: Transition | None = None
    transition_out: Transition | None = None
    markers: list[str] = Field(default_factory=list)
    effects: list[ItemEffect] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    # Source range within the referenced asset (source in/out)
    source_in: float = Field(default=0.0, ge=0)
    source_out: float | None = None
    gain_db: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> "TimelineItem":
        if self.end_time <= self.start_time:
            raise ValueError(f"item {self.item_id}: end_time must be > start_time")
        if self.source_out is not None and self.source_out <= self.source_in:
            raise ValueError(f"item {self.item_id}: source_out must be > source_in")
        return self

    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time) / max(self.speed, 1e-9)

    @property
    def time_range(self) -> TimeRange:
        return TimeRange(start=self.start_time, end=self.end_time)


class SubtitleWord(BaseModel):
    text: str
    start: float
    end: float
    emphasis: bool = False


class SubtitleStyle(BaseModel):
    font: str = "Inter"
    size_ratio: float = 0.052          # fraction of frame height
    color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: float = 0.08        # fraction of font size
    background: bool = False
    background_color: str = "#000000"
    background_alpha: float = 0.55
    placement: Literal["bottom", "top", "dynamic"] = "bottom"
    safe_area_inset: float = 0.05
    animation: str = "none"            # none | pop | fade | slide_up | keyword_kinetic


class SubtitleCue(BaseModel):
    cue_id: str = Field(default_factory=lambda: new_id("cue"))
    track_id: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str
    words: list[SubtitleWord] = Field(default_factory=list)
    style: SubtitleStyle = Field(default_factory=SubtitleStyle)
    emphasis_words: list[str] = Field(default_factory=list)
    bounding_box: tuple[float, float, float, float] | None = None  # normalized x0,y0,x1,y1
    collision_safe: bool | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "SubtitleCue":
        if self.end <= self.start:
            raise ValueError(f"cue {self.cue_id}: end must be > start")
        return self

    @property
    def cps(self) -> float:
        """Characters per second reading rate."""
        dur = self.end - self.start
        return (len(self.text) / dur) if dur > 0 else float(len(self.text)) * 100.0


class AudioAutomationPoint(BaseModel):
    time: float
    gain_db: float


class DuckingConfig(BaseModel):
    enabled: bool = False
    sidechain_source: str = "speech"
    threshold_db: float = -30.0
    ratio: float = 4.0
    attack_ms: float = 25.0
    release_ms: float = 350.0
    target_reduction_db: float = 12.0


class AudioBus(BaseModel):
    bus_id: str = Field(default_factory=lambda: new_id("bus"))
    name: str
    kind: Literal["speech", "music", "sfx", "master"]
    inputs: list[str] = Field(default_factory=list)   # track ids routed into this bus
    gain_db: float = 0.0
    automation: list[AudioAutomationPoint] = Field(default_factory=list)
    ducking: DuckingConfig = Field(default_factory=DuckingConfig)


class TimelineMarker(BaseModel):
    marker_id: str = Field(default_factory=lambda: new_id("mrk"))
    time: float = Field(ge=0)
    duration: float = 0.0
    color: str = "BLUE"
    name: str = ""
    note: str = ""
    kind: MarkerKind = "chapter"


class Track(BaseModel):
    track_id: str = Field(default_factory=lambda: new_id("trk"))
    kind: TrackKind
    index: int = 0
    role: TrackRole = "primary"
    items: list[TimelineItem] = Field(default_factory=list)
    cues: list[SubtitleCue] = Field(default_factory=list)  # only for subtitle tracks

    def sorted_items(self) -> list[TimelineItem]:
        return sorted(self.items, key=lambda i: (i.start_time, i.end_time))

    def validate_no_overlap(self) -> None:
        prev: TimelineItem | None = None
        for item in self.sorted_items():
            if prev is not None and item.start_time < prev.end_time - 1e-6:
                raise ValueError(
                    f"track {self.track_id}: overlap between {prev.item_id} and {item.item_id}")
            prev = item


class QAStatus(BaseModel):
    approved: bool = False
    attempts: int = 0
    blocking_violations: list[str] = Field(default_factory=list)
    report_path: str | None = None
    last_checked_at: datetime | None = None


class CanonicalTimeline(BaseModel):
    """JSON-serializable canonical timeline (§5.1)."""

    timeline_id: str = Field(default_factory=lambda: new_id("tl"))
    name: str = "timeline"
    frame_rate: float = 30.0
    width: int = 1920
    height: int = 1080
    pixel_aspect_ratio: float = 1.0
    duration_seconds: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)
    tracks: list[Track] = Field(default_factory=list)
    markers: list[TimelineMarker] = Field(default_factory=list)
    audio_buses: list[AudioBus] = Field(default_factory=list)
    decision_ledger: list[dict[str, Any]] = Field(default_factory=list)
    qa_report: QAStatus = Field(default_factory=QAStatus)
    color_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def recompute_duration(self) -> float:
        ends = [i.end_time for t in self.tracks for i in t.items]
        ends += [c.end for t in self.tracks for c in t.cues]
        self.duration_seconds = max(ends, default=0.0)
        return self.duration_seconds

    def track(self, track_id: str) -> Track | None:
        return next((t for t in self.tracks if t.track_id == track_id), None)

    def item(self, item_id: str) -> TimelineItem | None:
        for t in self.tracks:
            for i in t.items:
                if i.item_id == item_id:
                    return i
        return None

    def cue(self, cue_id: str) -> SubtitleCue | None:
        for t in self.tracks:
            for c in t.cues:
                if c.cue_id == cue_id:
                    return c
        return None

    def all_evidence_ids(self) -> set[str]:
        out: set[str] = set()
        for t in self.tracks:
            out.update(i.evidence_ids for i in t.items)
            out.update(c.evidence_ids for c in t.cues)
            for i in t.items:
                out.update(e.evidence_ids for e in i.effects)
        return out

    def structural_validate(self) -> None:
        """Raise on invariant violations; called before every export."""
        seen_ids: set[str] = set()
        for t in self.tracks:
            if t.track_id in seen_ids:
                raise ValueError(f"duplicate track id {t.track_id}")
            seen_ids.add(t.track_id)
            if t.kind != "subtitle":
                t.validate_no_overlap()
            for i in t.items:
                if i.item_id in seen_ids:
                    raise ValueError(f"duplicate item id {i.item_id}")
                seen_ids.add(i.item_id)
                if i.track_id != t.track_id:
                    raise ValueError(f"item {i.item_id} track_id mismatch")
            for c in t.cues:
                if c.cue_id in seen_ids:
                    raise ValueError(f"duplicate cue id {c.cue_id}")
                seen_ids.add(c.cue_id)
                if c.track_id != t.track_id:
                    raise ValueError(f"cue {c.cue_id} track_id mismatch")
        self.recompute_duration()
