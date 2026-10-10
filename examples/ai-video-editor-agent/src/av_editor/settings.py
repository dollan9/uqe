"""Pydantic v2 configuration schema (§6.3) with YAML + environment overrides.

Secrets (API keys) are never stored in the config file itself — only the *name*
of the environment variable to read them from, resolved lazily at use time.
Loading uses ``yaml.safe_load`` (no arbitrary object deserialization, §6.10).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from av_editor.errors import ConfigurationError


class ProjectConfig(BaseModel):
    name: str = "default-project"
    output_dir: Path = Path("output")
    cache_dir: Path = Path(".cache")
    seed: int = 1337  # reproducible seeds (§6.9 / LAW 5)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    json_logs: bool = False


class MediaConfig(BaseModel):
    proxy_height: Literal[720, 1080] = 720
    proxy_codec: Literal["h264", "prores"] = "h264"
    checksum_enabled: bool = True
    preserve_proxy_frame_rate: bool = True
    analysis_sample_rate: int = 48000


class FrameSamplingConfig(BaseModel):
    baseline_fps_short_shot: float = 2.0
    baseline_fps_long_shot: float = 1.0
    long_shot_seconds: float = 30.0
    hook_fps: float = 15.0
    hook_window_seconds: float = 5.0
    high_energy_fps: float = 10.0
    high_energy_percentile: float = 85.0
    high_energy_window_seconds: float = 2.0
    boundary_proximity_seconds: float = 0.75
    onset_proximity_seconds: float = 1.0
    sentence_proximity_seconds: float = 0.5


class VisionConfig(BaseModel):
    frame_sampling: FrameSamplingConfig = Field(default_factory=FrameSamplingConfig)
    scene_detect_threshold: float = 27.0
    scene_detect_threshold_talking_head: float = 22.0
    scene_detect_threshold_high_motion: float = 30.0
    min_scene_len_frames: int = 15
    use_gpu_optical_flow: bool = False
    optical_flow_backend: Literal["farneback", "raft"] = "farneback"
    face_interp_max_gap_ms: float = 250.0
    emotion_min_confidence: float = 0.60
    emotion_min_luminance: float = 40.0  # mean gray level threshold for lighting
    focal_weights: dict[str, float] = {
        "face_attention": 0.35,
        "gaze_convergence": 0.20,
        "saliency": 0.20,
        "motion_energy": 0.15,
        "rule_of_thirds": 0.10,
    }
    visual_energy_weights: dict[str, float] = {
        "optical_flow": 0.30,
        "luminance_contrast": 0.20,
        "colorfulness": 0.15,
        "face_attention": 0.15,
        "edge_density_delta": 0.10,
        "saliency_change": 0.10,
    }

    @model_validator(mode="after")
    def _check_weights(self) -> "VisionConfig":
        for name, weights in (("focal_weights", self.focal_weights),
                              ("visual_energy_weights", self.visual_energy_weights)):
            total = sum(weights.values())
            if abs(total - 1.0) > 1e-6:
                raise ConfigurationError(f"{name} must sum to 1.0, got {total}")
        return self


class VLMConfig(BaseModel):
    provider: Literal["openai_compatible", "hf_local", "disabled"] = "disabled"
    model: str = ""
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "AV_EDITOR_VLM_API_KEY"  # secret only from env (§6.10)
    temperature: float = 0.0
    max_retries: int = 3
    timeout_seconds: float = 60.0
    max_image_tokens_budget: int = 1200
    image_max_side: int = 768
    prompt_version: str = "v1"  # participates in cache invalidation (§6.5)
    allow_cv_only_fallback: bool = False  # explicit user opt-in for reduced semantics

    def resolve_api_key(self) -> str | None:
        val = os.environ.get(self.api_key_env)
        return val.strip() if val else None

    @field_validator("temperature")
    @classmethod
    def _temp_zero(cls, v: float) -> float:
        if v != 0.0:
            raise ConfigurationError("VLM temperature must be 0.0 (deterministic analysis)")
        return v


class AudioConfig(BaseModel):
    whisper_model: str = "large-v3"
    whisperx_align_model: str = ""
    whisperx_align_lang: str = "en"
    target_speech_lufs: float = -14.0
    speech_lufs_tolerance: float = 1.0
    true_peak_limit_dbtp: float = -1.0
    dynamic_range_target_db: float = 12.0
    onset_delta: float = 0.07
    onset_frame_length: int = 2048
    onset_hop: int = 512
    breath_min_duration_ms: float = 350.0
    breath_target_low_ms: float = 120.0
    breath_target_high_ms: float = 180.0
    harsh_breath_reduction_db: tuple[float, float] = (6.0, 12.0)


class EditorialConfig(BaseModel):
    hook_target_score: float = 0.72
    interrupt_min_seconds: float = 3.0
    interrupt_max_seconds: float = 7.0
    max_strong_interrupts_per_minute: int = 12
    dead_space_threshold: float = 0.72
    dead_space_soft_threshold: float = 0.55
    preserve_emotional_pauses: bool = True
    emotional_hold_extra_seconds: float = 1.5
    comedic_adjustment_max_ratio: float = 0.15
    max_black_at_start_seconds: float = 0.35
    speech_within_seconds: float = 0.75
    first_caption_within_seconds: float = 0.8
    cold_open_min_seconds: float = 1.0
    cold_open_max_seconds: float = 2.5
    j_cut_lead_ms: tuple[int, int] = (150, 400)
    l_cut_tail_ms: tuple[int, int] = (150, 500)
    transient_sync_window_seconds: float = 0.120
    cut_point_hard_no_mid_word: bool = True
    edit_score_weights: dict[str, float] = {
        "retention": 0.28,
        "pacing_coherence": 0.22,
        "visual_quality": 0.18,
        "audio_visual_sync": 0.12,
        "subtitle_readability": 0.10,
        "brand_safety": 0.06,
        "niche_style_fit": 0.04,
    }
    max_edit_score_patch_regression: float = 0.03

    @model_validator(mode="after")
    def _check_weights(self) -> "EditorialConfig":
        total = sum(self.edit_score_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ConfigurationError(f"edit_score_weights must sum to 1.0, got {total}")
        return self


class SubtitleConfig(BaseModel):
    max_cps: float = 18.0
    max_chars_per_line: int = 42
    max_lines: int = 2
    min_cue_duration: float = 0.35
    max_cue_duration: float = 5.0
    safe_area_inset: float = 0.05
    min_height_ratio: float = 0.035  # caption height vs frame height at 1080p
    contrast_min_ratio: float = 4.5
    font_family: str = "Inter"
    default_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width_ratio: float = 0.08
    background_color: str = "#000000"
    placement: Literal["bottom", "top", "dynamic"] = "dynamic"
    collision_shift_max_ms: float = 150.0
    collision_font_shrink_max: float = 0.12


class SoundConfig(BaseModel):
    music_under_speech_lufs: float = -26.0
    music_no_speech_lufs: float = -18.0
    sfx_peak_limit_dbtp: float = -12.0
    duck_attack_ms: int = 25
    duck_release_ms: int = 350
    duck_ratio: float = 4.0
    duck_threshold_db: float = -30.0
    duck_target_reduction_db: float = 12.0
    crossfade_speech_ms: tuple[int, int] = (2, 10)
    crossfade_music_sfx_ms: tuple[int, int] = (10, 40)


class BenchmarkConfig(BaseModel):
    enabled: bool = False
    niche_id: str = ""
    niche_name: str = ""
    reference_paths: list[Path] = Field(default_factory=list)
    retention_csv_paths: list[Path] = Field(default_factory=list)
    allow_public_metadata: bool = True
    allow_media_download: bool = False
    user_certifies_rights: bool = False
    respect_robots_txt: bool = True
    official_api_key_env: str = "AV_EDITOR_YT_API_KEY"


class ResolveNLEConfig(BaseModel):
    enabled: bool = True
    dry_run: bool = False
    script_api_path: str = ""  # override; otherwise auto-detected
    pythonpath_probe: bool = True


class NLEConfig(BaseModel):
    resolve: ResolveNLEConfig = Field(default_factory=ResolveNLEConfig)
    premiere_enabled: bool = False
    fcpxml_version: str = "1.11"
    otio_enabled: bool = True


class QAConfig(BaseModel):
    max_patch_attempts: int = 3
    require_vlm_qc: bool = True
    critical_blocks_export: bool = True
    inspection_render_height: int = 480
    subtitle_face_iou_critical: float = 0.05
    focal_overlap_high: float = 0.10
    edge_margin_medium: float = 0.02
    flash_max_per_second: float = 3.0
    patch_confidence_medium_min: float = 0.75


class PipelineConfig(BaseModel):
    """Top-level pipeline configuration (§6.3)."""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    media: MediaConfig = Field(default_factory=MediaConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    vlm: VLMConfig = Field(default_factory=VLMConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    editorial: EditorialConfig = Field(default_factory=EditorialConfig)
    subtitles: SubtitleConfig = Field(default_factory=SubtitleConfig)
    sound: SoundConfig = Field(default_factory=SoundConfig)
    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    nle: NLEConfig = Field(default_factory=NLEConfig)
    qa: QAConfig = Field(default_factory=QAConfig)
    autonomous_mode: bool = False
    human_approval_gates: list[str] = Field(default_factory=lambda: ["final_export"])
    inputs: list[Path] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "PipelineConfig":
        if not path.exists():
            raise ConfigurationError(f"Config file not found: {path}", path=str(path))
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Malformed YAML config: {exc}", path=str(path)) from exc
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ConfigurationError("Config root must be a mapping", path=str(path))
        raw = _apply_env_overrides(raw)
        try:
            return cls.model_validate(raw)
        except Exception as exc:  # pydantic ValidationError surface
            raise ConfigurationError(f"Config validation failed: {exc}", path=str(path)) from exc

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False)


def _apply_env_overrides(raw: dict) -> dict:
    """Apply ``AV_EDITOR_<SECTION>_<KEY>`` environment overrides (§6.3)."""
    prefix = "AV_EDITOR_"
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        parts = env_key[len(prefix):].lower().split("__")  # double underscore separates section/key
        if len(parts) == 2 and parts[0] in type_fields(raw):
            section, field = parts
            raw.setdefault(section, {})[field] = _coerce_scalar(env_val)
    return raw


def type_fields(raw: dict) -> set[str]:
    return set(PipelineConfig.model_fields.keys()) & (set(raw.keys()) | set(PipelineConfig.model_fields.keys()))


def _coerce_scalar(value: str) -> object:
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
