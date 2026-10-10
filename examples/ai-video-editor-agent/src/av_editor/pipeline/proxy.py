"""MODULE 1 (part A) — The Proxy Vision Engine.

NEVER run OpenCV/VLM analysis on raw 4K footage. This module:

1. Probes the source with ``ffprobe`` (JSON output, no shell interpolation).
2. Generates a deterministic 720p / 10 fps proxy via ffmpeg (libx264 fast preset).
3. Keeps an exact time map: proxy timestamps == source timestamps (we drop by
   frame *time*, not frame index), so every timestamp produced while analyzing
   the proxy maps 1:1 onto the high-res timeline.
4. Verifies proxy integrity after generation; raises ``FFmpegError`` (never
   silently proceeds) if the proxy is missing or its duration drifted.

All ffmpeg/ffprobe invocations go through :class:`SubprocessRunner` (§6.2):
``shell=False``, argv lists only, hard timeouts, structured errors.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from av_editor.core.subprocess_runner import SubprocessRunner
from av_editor.errors import FFmpegError, FFprobeError, MediaIngestError
from av_editor.logging import get_logger

log = get_logger("av_editor.pipeline.proxy")

PROXY_FPS = 10.0            # vision sampling rate on the proxy
PROXY_HEIGHT = 720          # analysis resolution ceiling


@dataclass(frozen=True)
class SourceProbe:
    path: str
    duration_s: float
    width: int
    height: int
    frame_rate: float
    has_video: bool
    has_audio: bool
    vcodec: str
    acodec: str


@dataclass(frozen=True)
class ProxyResult:
    source_path: Path
    proxy_path: Path
    probe: SourceProbe
    proxy_fps: float
    proxy_height: int
    reused: bool

    @property
    def scale_factor(self) -> float:
        """Uniform scale applied to normalized boxes is 1.0 — boxes stay normalized."""
        return self.probe.height / self.proxy_height if self.probe.height else 1.0


def ffprobe_json(path: Path, runner: SubprocessRunner | None = None) -> dict:
    runner = runner or SubprocessRunner(default_timeout=60.0)
    ffprobe = runner.require("ffprobe", "Install FFmpeg >= 6 and ensure ffprobe is on PATH.")
    res = runner.run(
        [ffprobe, "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        timeout=60.0, retries=2, retry_on_failure=True, check=True)
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        raise FFprobeError("ffprobe returned unparseable JSON", path=str(path)) from exc


def probe_source(path: Path, runner: SubprocessRunner | None = None) -> SourceProbe:
    if not path.exists():
        raise MediaIngestError("Source media file not found", path=str(path))
    info = ffprobe_json(path, runner)
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if v is None and a is None:
        raise MediaIngestError("File contains neither video nor audio streams", path=str(path))

    duration = _to_float(info.get("format", {}).get("duration"))
    if duration is None and v is not None:
        duration = _to_float(v.get("duration"))
    if duration is None:
        raise FFprobeError("Could not determine media duration", path=str(path))

    fps = 0.0
    if v is not None:
        fps = _parse_rate(v.get("avg_frame_rate") or v.get("r_frame_rate"))

    return SourceProbe(
        path=str(path),
        duration_s=float(duration),
        width=int(v.get("width", 0)) if v else 0,
        height=int(v.get("height", 0)) if v else 0,
        frame_rate=fps,
        has_video=v is not None,
        has_audio=a is not None,
        vcodec=str((v or {}).get("codec_name", "")),
        acodec=str((a or {}).get("codec_name", "")),
    )


def build_proxy_command(src: Path, dst: Path, *, fps: float = PROXY_FPS,
                        height: int = PROXY_HEIGHT) -> list[str]:
    """Deterministic argv for proxy generation (pure function — unit-testable).

    - Video: downscale to ``height`` (keep aspect, even dims), fixed CFR ``fps``,
      libx264 ultrafast/crf30 — quality is irrelevant, temporal fidelity matters.
    - Audio: copy-free AAC 96k at 48 kHz so waveform/onset analysis can also run
      cheaply on the proxy when librosa/whisper use it as scratch audio.
    - ``-vsync cfr`` guarantees proxy frame times are exactly n/fps seconds,
      which makes proxy→source timestamp mapping trivially linear.
    """
    scale_vf = (f"scale=-2:{height}:flags=bilinear,fps={fps:g},format=yuv420p")
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-vf", scale_vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
        "-vsync", "cfr", "-r", f"{fps:g}",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "96k",
        "-movflags", "+faststart",
        str(dst),
    ]


def generate_proxy(
    src: Path,
    *,
    work_dir: Path | None = None,
    runner: SubprocessRunner | None = None,
    fps: float = PROXY_FPS,
    height: int = PROXY_HEIGHT,
    max_duration_drift_s: float = 0.5,
    overwrite: bool = False,
) -> ProxyResult:
    """Create (or reuse) a 720p/10fps analysis proxy for ``src``.

    Raises:
        MediaIngestError: source missing / unreadable.
        FFmpegError: binary missing, non-zero exit, timeout, or proxy drift.
    """
    runner = runner or SubprocessRunner(default_timeout=3600.0)
    work_dir = work_dir or (src.parent / ".av_proxy")
    work_dir.mkdir(parents=True, exist_ok=True)
    dst = work_dir / f"{src.stem}_proxy_{int(height)}p_{int(fps)}fps.mp4"

    probe = probe_source(src, runner)
    if not probe.has_video:
        raise MediaIngestError("Cannot build video proxy for audio-only file", path=str(src))

    if dst.exists() and not overwrite:
        existing = probe_source(dst, runner)
        if abs(existing.duration_s - probe.duration_s) <= max_duration_drift_s:
            log.info("proxy_reused", proxy=str(dst))
            return ProxyResult(src, dst, probe, fps, height, reused=True)
        log.warning("proxy_stale_rebuilding", proxy=str(dst))
        dst.unlink(missing_ok=True)

    ffmpeg = runner.require("ffmpeg", "Install FFmpeg >= 6 and ensure ffmpeg is on PATH.")
    argv = build_proxy_command(src, dst, fps=fps, height=height)
    argv[0] = ffmpeg
    # Estimate generous timeout: encode of ultrafast x264 is usually > realtime.
    timeout = max(120.0, probe.duration_s * 10.0)
    log.info("proxy_encode_start", src=str(src), dst=str(dst), fps=fps, height=height)
    res = runner.run(argv, timeout=timeout, check=True)
    if not res.ok or not dst.exists():
        raise FFmpegError("Proxy generation failed", stderr_tail=res.stderr[-800:], src=str(src))

    # --- Integrity gate: never analyze a broken proxy (mission requirement). ---
    try:
        proxy_probe = probe_source(dst, runner)
    except (FFprobeError, MediaIngestError) as exc:
        dst.unlink(missing_ok=True)
        raise FFmpegError("Generated proxy is unreadable — refusing blind analysis",
                          proxy=str(dst)) from exc
    drift = abs(proxy_probe.duration_s - probe.duration_s)
    if drift > max_duration_drift_s:
        dst.unlink(missing_ok=True)
        raise FFmpegError(
            f"Proxy duration drifted {drift:.2f}s vs source — refusing to map timestamps",
            proxy=str(dst), source=str(src))
    log.info("proxy_encode_done", dst=str(dst), drift_s=round(drift, 3))
    return ProxyResult(src, dst, probe, fps, height, reused=False)


def extract_frames_at(proxy: Path, times_s: list[float], out_dir: Path,
                      *, runner: SubprocessRunner | None = None,
                      jpeg_quality: int = 4) -> list[Path]:
    """Extract one JPEG per requested timestamp from the proxy (1 fps default grid).

    Uses accurate seek (-ss before -i plus -frames:v 1) per frame; callers pass
    proxy-domain times. Filenames embed the timestamp: ``frame_<ms>.jpg`` so the
    mapping back to seconds is lossless.
    """
    runner = runner or SubprocessRunner(default_timeout=120.0)
    ffmpeg = runner.require("ffmpeg", "Install FFmpeg >= 6.")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for t in times_s:
        ms = max(0, int(round(t * 1000)))
        dst = out_dir / f"frame_{ms:08d}.jpg"
        if dst.exists():
            paths.append(dst)
            continue
        res = runner.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
             "-ss", f"{ms / 1000:.3f}", "-i", str(proxy),
             "-frames:v", "1", "-q:v", str(jpeg_quality), str(dst)],
            timeout=60.0, check=False)
        if not res.ok or not dst.exists():
            log.warning("frame_extract_failed", t=t, stderr_tail=res.stderr[-300:])
            dst.unlink(missing_ok=True)
            continue
        paths.append(dst)
    if not paths:
        raise FFmpegError("No frames could be extracted from proxy", proxy=str(proxy))
    return paths


def copy_proxy_if_needed(result: ProxyResult, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / result.proxy_path.name
    if target != result.proxy_path:
        shutil.copy2(result.proxy_path, target)
    return target


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_rate(rate: str | None) -> float:
    if not rate or rate in ("0/0", "N/A"):
        return 0.0
    try:
        num, _, den = rate.partition("/")
        d = float(den) if den else 1.0
        return float(num) / d if d else 0.0
    except ValueError:
        return 0.0
