"""MODULE 1 (part B) — PySceneDetect cut detection on the PROXY only.

Hard cuts (content-aware HSV delta) and gradual transitions (adaptive
magnitudes over a rolling window) are detected at proxy resolution, then
snapped to real source frame boundaries via :mod:`av_editor.core.timecode`.

If ``scenedetect`` is not installed we degrade to an OpenCV-only content
difference detector so the pipeline never dies for a missing optional dep —
but the degradation is *logged loudly* and marked in the output so downstream
agents know evidence quality dropped.
"""

from __future__ import annotations

from av_editor.domain.evidence import Evidence, EvidenceType, new_id
from av_editor.domain.vision import ShotBoundary
from av_editor.logging import get_logger

log = get_logger("av_editor.pipeline.scenes")


def detect_scenes(
    proxy_path: str,
    *,
    asset_id: str,
    proxy_fps: float = 10.0,
    source_fps: float = 30.0,
    duration_s: float,
    content_threshold: float = 27.0,
    adaptive_threshold: float = 3.0,
    min_scene_len_frames: int = 8,          # in *proxy* frames (0.8 s @10 fps)
    hybrid: bool = True,
) -> tuple[list[ShotBoundary], list[Evidence]]:
    """Return shot boundaries + evidence records. Times are SOURCE-domain seconds
    (identical to proxy-domain seconds; only frame indices differ)."""
    try:
        boundaries = _detect_with_scenedetect(
            proxy_path, asset_id=asset_id, proxy_fps=proxy_fps, source_fps=source_fps,
            content_threshold=content_threshold, adaptive_threshold=adaptive_threshold,
            min_scene_len_frames=min_scene_len_frames, hybrid=hybrid)
        method = "hybrid" if hybrid else "content"
    except ImportError:
        log.warning("scenedetect_missing_falling_back_to_opencv",
                    remediation="pip install 'ai-video-editor-agent[full]'")
        boundaries = _detect_with_opencv(
            proxy_path, asset_id=asset_id, proxy_fps=proxy_fps, source_fps=source_fps,
            content_threshold=content_threshold, min_scene_len_frames=min_scene_len_frames)
        method = "content"

    if not boundaries:  # single continuous take
        boundaries = [ShotBoundary(
            shot_id=new_id("shot"), asset_id=asset_id,
            start_frame=0, end_frame=int(round(duration_s * source_fps)),
            start_time=0.0, end_time=duration_s, duration=duration_s,
            detector="content", confidence=1.0, boundary_strength=0.0)]

    evidence: list[Evidence] = []
    for b in boundaries:
        if b.start_time <= 0.0:
            continue  # opening of the program is not a "cut"
        evidence.append(Evidence(
            type=EvidenceType.VISUAL_SHOT_BOUNDARY, source_agent="scene_detector",
            asset_id=asset_id, time_range=None,
            payload={"shot_id": b.shot_id, "start_time": b.start_time,
                     "boundary_strength": b.boundary_strength, "detector": method},
            confidence=b.confidence))
    log.info("scenes_detected", count=len(boundaries), method=method)
    return boundaries, evidence


def _frames_from_video(proxy_path: str):
    """Generator of (frame_index, gray_downscaled) — memory-safe streaming."""
    import cv2

    cap = cv2.VideoCapture(proxy_path)
    if not cap.isOpened():
        raise OSError(f"Cannot open proxy for scene detection: {proxy_path}")
    try:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
            yield idx, small
            idx += 1
    finally:
        cap.release()


def _snap_to_source(t_proxy: float, source_fps: float) -> float:
    """Snap a boundary time onto the nearest true source frame."""
    return round(round(t_proxy * source_fps) / source_fps, 6)


def _detect_with_scenedetect(proxy_path: str, *, asset_id: str, proxy_fps: float,
                             source_fps: float, content_threshold: float,
                             adaptive_threshold: float, min_scene_len_frames: int,
                             hybrid: bool) -> list[ShotBoundary]:
    from scenedetect import AdaptiveDetector, ContentDetector, detect  # noqa: F401

    detectors = [ContentDetector(threshold=content_threshold,
                                 min_scene_len=min_scene_len_frames)]
    if hybrid:
        detectors.append(AdaptiveDetector(adaptive_threshold=adaptive_threshold,
                                          min_scene_len=min_scene_len_frames))
    # detect() accepts a list of detectors; union of their cuts = hybrid mode.
    scene_list = detect(proxy_path, detectors=detectors)
    if not scene_list:
        return []

    boundaries: list[ShotBoundary] = []
    for start, end in scene_list:
        st = _snap_to_source(start.get_seconds(), source_fps)
        et = _snap_to_source(end.get_seconds(), source_fps)
        boundaries.append(ShotBoundary(
            shot_id=new_id("shot"), asset_id=asset_id,
            start_frame=int(round(st * source_fps)), end_frame=int(round(et * source_fps)),
            start_time=st, end_time=et, duration=max(et - st, 0.0),
            detector="hybrid" if hybrid else "content",
            confidence=0.95,
            boundary_strength=0.0))
    return boundaries


def _detect_with_opencv(proxy_path: str, *, asset_id: str, proxy_fps: float,
                        source_fps: float, content_threshold: float,
                        min_scene_len_frames: int) -> list[ShotBoundary]:
    """Fallback HSV-histogram-difference detector (no scenedetect dependency)."""
    import cv2

    cuts: list[int] = []
    last_cut = 0
    prev_hist = None
    frame_count = 0
    for idx, small in _frames_from_video(proxy_path):
        frame_count = idx + 1
        hist = cv2.calcHist([small], [0, 1, 2], None, [16, 16, 16], [0, 256] * 3)
        cv2.normalize(hist, hist)
        if prev_hist is not None:
            delta = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA) * 100.0
            if delta > content_threshold and idx - last_cut >= min_scene_len_frames:
                cuts.append(idx)
                last_cut = idx
        prev_hist = hist

    bounds_idx = [0, *cuts, frame_count]
    boundaries: list[ShotBoundary] = []
    for a, b in zip(bounds_idx[:-1], bounds_idx[1:], strict=False):
        st = _snap_to_source(a / proxy_fps, source_fps)
        et = _snap_to_source(b / proxy_fps, source_fps)
        boundaries.append(ShotBoundary(
            shot_id=new_id("shot"), asset_id=asset_id,
            start_frame=int(round(st * source_fps)), end_frame=int(round(et * source_fps)),
            start_time=st, end_time=et, duration=max(et - st, 0.0),
            detector="content", confidence=0.80,  # degraded-path honesty (§ LAW 1)
            boundary_strength=0.0))
    return boundaries
