"""Media asset domain model (§2.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from av_editor.domain.evidence import utcnow


class ColorMetadata(BaseModel):
    color_space: str = "unknown"       # e.g. bt709
    color_primaries: str = "unknown"
    color_transfer: str = "unknown"
    pixel_format: str = "unknown"


class AudioStreamInfo(BaseModel):
    sample_rate: int = 0
    channels: int = 0
    codec: str = ""
    bitrate_bps: int | None = None
    disposition: dict[str, bool] = Field(default_factory=dict)


class VideoStreamInfo(BaseModel):
    width: int = 0
    height: int = 0
    frame_rate: float = 0.0
    avg_frame_rate: float = 0.0
    codec: str = ""
    pix_fmt: str = ""
    bitrate_bps: int | None = None
    timebase: str = ""
    nb_frames: int | None = None
    disposition: dict[str, bool] = Field(default_factory=dict)
    variable_frame_rate: bool = False


class MediaAsset(BaseModel):
    """Validated representation of an ingested media file."""

    asset_id: str
    original_path: str
    proxy_path: str | None = None
    analysis_audio_path: str | None = None
    media_type: Literal["video", "audio", "image"]
    duration_seconds: float = Field(ge=0)
    start_time_seconds: float = 0.0
    frame_rate: float = 0.0
    width: int = 0
    height: int = 0
    pixel_aspect_ratio: float = 1.0
    color_metadata: ColorMetadata = Field(default_factory=ColorMetadata)
    video_stream: VideoStreamInfo | None = None
    audio_stream: AudioStreamInfo | None = None
    audio_sample_rate: int = 0
    audio_channels: int = 0
    codec_metadata: dict[str, Any] = Field(default_factory=dict)
    checksum_sha256: str = ""
    phash: str = ""
    keyframe_times: list[float] = Field(default_factory=list)
    has_audio: bool = False
    unsupported_codec: bool = False
    license_status: Literal["owned", "licensed", "stock", "unverified", "not_applicable"] = "unverified"
    license_note: str = ""
    ingested_at: datetime = Field(default_factory=utcnow)

    def is_license_cleared(self) -> bool:
        return self.license_status in ("owned", "licensed", "stock", "not_applicable")
