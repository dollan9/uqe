"""MODULE 2 (part C) — Timeline builder: applies EditDecisions to the canonical
timeline and enforces CRITICAL SAFETY NET #2 — Micro-fades.

Every audio-adjacent cut (standard, J-cut, L-cut) automatically receives a
2–4 frame constant-power crossfade on BOTH sides of the edit so transients
never hit a hard discontinuity (clicks/pops). The fade length is expressed in
*frames* (not seconds) because that is what NLEs quantize to; at 30 fps,
2–4 frames = 66–133 ms.

Confidence coloring (SAFETY NET #4): GREEN ≥ 0.95, YELLOW 0.80–0.95,
RED < 0.80 + human-review marker with the decision rationale as note text.
"""

from __future__ import annotations

from av_editor.core.timecode import frames_to_timecode
from av_editor.domain.evidence import ActionType, EditDecision, TimeRange
from av_editor.domain.timeline import (CanonicalTimeline, ItemEffect, TimelineItem,
                                       TimelineMarker, Track, Transition)
from av_editor.logging import get_logger
from av_editor.settings import SoundConfig

log = get_logger("av_editor.editing.builder")

GREEN = "GREEN"
YELLOW = "YELLOW"
RED = "RED"


def confidence_color(conf: float) -> str:
    if conf >= 0.95:
        return GREEN
    if conf >= 0.80:
        return YELLOW
    return RED


def micro_fade_frames(*, frame_rate: float, sound_cfg: SoundConfig) -> int:
    """Clamp the configured speech crossfade ms window into 2–4 frames."""
    lo_ms, hi_ms = sound_cfg.crossfade_speech_ms
    ideal_ms = (lo_ms + hi_ms) / 2.0
    frames = round(ideal_ms / 1000.0 * frame_rate)
    return max(2, min(4, frames))


def build_timeline_from_decisions(
    *, timeline_name: str, source_asset_id: str, frame_rate: float,
    width: int, height: int, duration_s: float,
    decisions: list[EditDecision], injects, sound_cfg: SoundConfig,
) -> CanonicalTimeline:
    """Apply REMOVE/SHORTEN decisions as ripple cuts over one continuous take.

    Decisions are expected pre-snapped to frame boundaries. Overlapping spans
    are merged. Every produced cut gets: transition_out+in micro crossfades,
    evidence ids, rationale, and a color-coded marker.
    """
    tl = CanonicalTimeline(name=timeline_name, frame_rate=frame_rate,
                           width=width, height=height)
    vtrack = Track(kind="video", index=0, role="primary")
    atrack = Track(kind="audio", index=1, role="vo")
    tl.tracks = [vtrack, atrack]

    removals: list[TimeRange] = []
    for d in decisions:
        if d.action_type in (ActionType.REMOVE_PAUSE, ActionType.SHORTEN_PAUSE):
            removals.append(TimeRange(start=d.start_time, end=d.end_time))
        elif d.action_type in (ActionType.CUT, ActionType.TRIM_START, ActionType.TRIM_END):
            removals.append(TimeRange(start=d.start_time, end=max(d.end_time, d.start_time)))
    merged = _merge_spans(removals)

    fade_frames = micro_fade_frames(frame_rate=frame_rate, sound_cfg=sound_cfg)
    fade_seconds = fade_frames / frame_rate

    cursor = 0.0
    keep_spans: list[tuple[float, float]] = []
    for r in merged:
        if r.start > cursor + 1e-6:
            keep_spans.append((cursor, r.start))
        cursor = max(cursor, r.end)
    if cursor < duration_s - 1e-6:
        keep_spans.append((cursor, duration_s))

    for idx, (k0, k1) in enumerate(keep_spans):
        tr_in = tr_out = None
        # Crossfades only where there is material to overlap into.
        if idx > 0 and k0 - keep_spans[idx - 1][1] >= 0:
            tr_in = Transition(kind="crossfade", duration_seconds=fade_seconds,
                               easing="constant_power")
        if idx < len(keep_spans) - 1:
            tr_out = Transition(kind="crossfade", duration_seconds=fade_seconds,
                                easing="constant_power")
        v_item = TimelineItem(
            track_id=vtrack.track_id, asset_id=source_asset_id,
            start_time=k0, end_time=k1, source_in=k0, source_out=k1,
            transition_in=tr_in, transition_out=tr_out)
        a_item = TimelineItem(
            track_id=atrack.track_id, asset_id=source_asset_id,
            start_time=k0, end_time=k1, source_in=k0, source_out=k1,
            transition_in=tr_in, transition_out=tr_out,
            effects=[ItemEffect(kind="eq", parameters={"note": "micro-fade guard"})])
        vtrack.items.append(v_item)
        atrack.items.append(a_item)

    # Injected zoom moves / b-roll become effects & overlay items.
    for p in injects or []:
        if p.kind == "zoom_move":
            host = _item_containing(vtrack, p.t)
            if host is not None:
                host.effects.append(ItemEffect(
                    kind="zoom_move",
                    parameters={"scale_from": p.scale_from, "scale_to": p.scale_to,
                                "duration": p.duration, "easing": "ease_in_out"},
                    evidence_ids=list(p.evidence_ids)))
        elif p.kind == "broll_insert":
            btrack = next((t for t in tl.tracks if t.role == "broll"), None)
            if btrack is None:
                btrack = Track(kind="video", index=len(tl.tracks), role="broll")
                tl.tracks.append(btrack)
            btrack.items.append(TimelineItem(
                track_id=btrack.track_id, asset_id=p.broll_asset_id,
                start_time=p.t, end_time=min(p.t + p.duration, duration_s),
                opacity=1.0,
                transition_in=Transition(kind="crossfade", duration_seconds=fade_seconds),
                transition_out=Transition(kind="crossfade", duration_seconds=fade_seconds),
                evidence_ids=list(p.evidence_ids), rationale=p.rationale))

    _attach_markers(tl, decisions, frame_rate)
    tl.structural_validate()
    log.info("timeline_built", keeps=len(keep_spans), fades_frames=fade_frames,
             markers=len(tl.markers))
    return tl


def _merge_spans(spans: list[TimeRange]) -> list[TimeRange]:
    if not spans:
        return []
    ordered = sorted(spans, key=lambda s: s.start)
    out = [ordered[0]]
    for s in ordered[1:]:
        prev = out[-1]
        if s.start <= prev.end + 0.05:      # near-touching gaps merge too
            out[-1] = TimeRange(start=prev.start, end=max(prev.end, s.end))
        else:
            out.append(s)
    return out


def _item_containing(track: Track, t: float) -> TimelineItem | None:
    for i in track.items:
        if i.start_time <= t < i.end_time:
            return i
    return None


def _attach_markers(tl: CanonicalTimeline, decisions: list[EditDecision],
                    frame_rate: float) -> None:
    """SAFETY NET #4: color-coded confidence markers on the master timeline."""
    for d in decisions:
        color = confidence_color(d.confidence)
        tc = frames_to_timecode(int(round(d.start_time * frame_rate)), frame_rate)
        if color == RED:
            tl.markers.append(TimelineMarker(
                time=d.start_time, duration=max(d.end_time - d.start_time, 1 / frame_rate),
                color=RED, name=f"REVIEW {tc}",
                note=(f"[{d.decision_id}] low confidence {d.confidence:.2f}: {d.rationale} "
                      f"— check eye line / context before accepting"),
                kind="risk"))
        elif color == YELLOW:
            tl.markers.append(TimelineMarker(
                time=d.start_time, color=YELLOW, name=f"CHECK {tc}",
                note=f"confidence {d.confidence:.2f}: {d.rationale}", kind="qa"))
        else:
            tl.markers.append(TimelineMarker(
                time=d.start_time, color=GREEN, name=f"AI cut {tc}",
                note=d.rationale, kind="interrupt"))
    # High-risk decisions also force MEDIUM risk floor honesty in ledger.
    tl.decision_ledger.extend({
        "decision_id": d.decision_id, "action": d.action_type.value,
        "start": d.start_time, "end": d.end_time, "confidence": d.confidence,
        "color": confidence_color(d.confidence), "risk": d.risk_level.value,
        "rationale": d.rationale, "evidence_ids": d.evidence_ids}
        for d in decisions)


def apply_jl_offsets(tl: CanonicalTimeline, plans, frame_rate: float) -> None:
    """Give J/L cuts their audio lead/trail by offsetting the AUDIO item edges.

    Video stays put; audio slides ∓offset across the cut — the classic split
    edit. Micro-fades still wrap both sides (already applied at build time).
    """
    atrack = next((t for t in tl.tracks if t.kind == "audio"), None)
    if atrack is None:
        return
    items = atrack.sorted_items()
    for plan in plans or []:
        if plan.kind == "hard" or not (0 < plan.cut_index < len(items)):
            continue
        left, right = items[plan.cut_index - 1], items[plan.cut_index]
        off = abs(plan.offset_ms) / 1000.0
        if plan.kind == "j_cut":       # right audio starts earlier (leads video)
            right.start_time = max(left.start_time, right.start_time - off)
        else:                           # l_cut: left audio trails past video cut
            left.end_time = min(right.end_time, left.end_time + off)
    atrack.validate_no_overlap()
