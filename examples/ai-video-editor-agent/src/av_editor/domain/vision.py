"""Vision domain models (§2.5): shots, flow, faces/gaze, composition, focal points,
visual energy and VLM frame semantics."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ShotBoundary(BaseModel):
    shot_id: str
    asset_id: str
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    duration: float
    detector: Literal["content", "adaptive", "keyframe", "hybrid"] = "content"
    confidence: float = 0.0
    boundary_strength: float = 0.0  # combined delta + flow discontinuity + luminance + face + audio proximity


class FlowFrame(BaseModel):
    frame_time: float
    flow_magnitude: float
    flow_direction: float          # radians
    flow_variance: float
    pan_estimate: float
    tilt_estimate: float
    zoom_estimate: float
    motion_stability: float        # 0..1, 1 = stable camera


class ShotFlow(BaseModel):
    shot_id: str
    frames: list[FlowFrame] = Field(default_factory=list)
    mean_magnitude: float = 0.0
    max_magnitude: float = 0.0
    dominant_direction: float = 0.0
    motion_class: Literal["static", "subtle", "moderate", "fast", "whip"] = "static"


class FaceTrack(BaseModel):
    frame_time: float
    face_id: str
    bbox: tuple[float, float, float, float]  # normalized x0,y0,x1,y1
    landmarks: list[tuple[float, float]] = Field(default_factory=list)
    head_pose: tuple[float, float, float] = (0.0, 0.0, 0.0)  # yaw, pitch, roll (deg)
    gaze_vector: tuple[float, float, float] = (0.0, 0.0, 1.0)
    gaze_target: Literal["camera", "off_screen_left", "off_screen_right", "down", "up",
                         "another_subject", "object", "unknown"] = "unknown"
    eye_openness: float = 1.0
    mouth_openness: float = 0.0
    expression_estimate: str | None = None
    expression_confidence: float = 0.0
    interpolated: bool = False
    confidence: float = 0.0


class CompositionMetrics(BaseModel):
    frame_time: float
    rule_of_thirds_score: float = 0.0     # 0..1 alignment of subject to thirds intersections
    headroom_ratio: float | None = None   # normalized gap above head
    lead_room_ratio: float | None = None  # space in direction of gaze/motion
    horizon_tilt_degrees: float = 0.0
    center_weighted_score: float = 0.0
    frame_balance: float = 0.0            # left/right saliency balance 0..1
    negative_space_ratio: float = 0.0
    occlusion_risk: float = 0.0
    distraction_score: float = 0.0
    on_screen_text_boxes: list[tuple[float, float, float, float]] = Field(default_factory=list)
    safe_title_margin_ok: bool = True
    subject_type: Literal["talking_head", "standing_person", "group", "product",
                          "landscape", "screen_recording", "none"] = "none"


class FocalPoint(BaseModel):
    frame_time: float
    focal_x: float
    focal_y: float
    focal_radius: float
    confidence: float
    components_used: dict[str, float] = Field(default_factory=dict)


ShotType = Literal["extreme_close_up", "close_up", "medium_close_up", "medium",
                   "medium_wide", "wide", "extreme_wide", "over_the_shoulder",
                   "two_shot", "group", "product", "screen_recording",
                   "broll_object", "empty_scene", "unknown"]


class ShotClassification(BaseModel):
    shot_id: str
    shot_type: ShotType
    confidence: float
    method: Literal["geometry", "vlm", "hybrid"] = "geometry"
    subject_count: int = 0


class VisualEnergySample(BaseModel):
    frame_time: float
    value: float
    components: dict[str, float] = Field(default_factory=dict)


class ShotVisualEnergy(BaseModel):
    shot_id: str
    samples: list[VisualEnergySample] = Field(default_factory=list)
    mean: float = 0.0
    maximum: float = 0.0
    variance: float = 0.0
    slope: float = 0.0
    peaks: list[float] = Field(default_factory=list)


class VLMComposition(BaseModel):
    rule_of_thirds: float = 0.0
    headroom: float = 0.0
    lead_room: float = 0.0


class VLMFrameAnalysis(BaseModel):
    """Strict schema for per-frame VLM semantic output (§2.6)."""

    shot_id: str
    frame_time: float
    shot_type: ShotType = "unknown"
    subjects: list[str] = Field(default_factory=list)
    action: str = ""
    emotion: str = "neutral"
    emotion_confidence: float = 0.0
    composition: VLMComposition = Field(default_factory=VLMComposition)
    distractions: list[str] = Field(default_factory=list)
    visual_interest: float = 0.0
    motion_description: str = ""
    on_screen_text: list[str] = Field(default_factory=list)
    brand_safety_flags: list[str] = Field(default_factory=list)
    recommended_use: list[Literal["a_roll", "b_roll", "hook", "cutaway"]] = Field(default_factory=list)
    notes: str = ""
    model: str = ""
    prompt_version: str = ""


class VLMQAIssue(BaseModel):
    category: str
    severity: Literal["critical", "high", "medium", "low"]
    description: str
    bounding_box: tuple[float, float, float, float] | None = None
    suggested_fix: str | None = None


class VLMQACritique(BaseModel):
    """Strict schema for QA-critic VLM output (§4.3)."""

    issues: list[VLMQAIssue] = Field(default_factory=list)
    overall_quality: float = 0.0
    readability: float = 0.0
    continuity: float = 0.0
    visual_comfort: float = 0.0
    approve: bool = False
    model: str = ""
    prompt_version: str = ""


class SaliencyMap(BaseModel):
    frame_time: float
    peak: tuple[float, float]           # normalized coordinates of saliency peak
    entropy: float = 0.0                # spread of saliency; high = diffuse attention
    coarse_grid: list[list[float]] = Field(default_factory=list)


class FrameSemanticsBundle(BaseModel):
    """All vision evidence attached to a single sampled frame."""

    asset_id: str
    frame_time: float
    frame_index: int
    path: str = ""
    flow: FlowFrame | None = None
    faces: list[FaceTrack] = Field(default_factory=list)
    composition: CompositionMetrics | None = None
    focal: FocalPoint | None = None
    saliency: SaliencyMap | None = None
    vlm: VLMFrameAnalysis | None = None
    extras: dict[str, Any] = Field(default_factory=dict)
