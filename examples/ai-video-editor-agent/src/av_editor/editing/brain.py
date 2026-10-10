"""MODULE 2 (part B) — The Editing Brain: pacing waves, dead-space removal,
cut-point selection and the B-Roll/Zoom injector.

Core principle (Tension & Release): retention density is a WAVE, not a
constant. Hooks run hot (cuts/interrupts every ~3 s), narrative build-up
deliberately slows down (release — let shots breathe up to ~9 s), payoffs
accelerate again (tension). A phase modulator scales all cadence thresholds,
so the same code produces veteran-editor rhythm instead of machine-gun cuts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from av_editor.domain.evidence import EditDecision, Evidence, EvidenceType, TimeRange
from av_editor.domain.pacing import CutPointCandidate, DeadSpaceScore, JLCutPlan
from av_editor.editing.fusion import MultimodalIndex, score_dead_space
from av_editor.logging import get_logger
from av_editor.settings import EditorialConfig

log = get_logger("av_editor.editing.brain")


# --------------------------------------------------------------------------
# Pacing wave model
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PacingPhase:
    name: str            # "hook" | "build" | "tension" | "release" | "payoff"
    density: float       # multiplier on interrupt frequency (>1 = faster)


def classify_phase(t: float, *, hook_window_s: float = 8.0,
                   segment_boundaries: list[float] | None = None,
                   energy_curve: list[tuple[float, float]] | None = None) -> PacingPhase:
    """Decide which part of the story wave time ``t`` sits in.

    - First ``hook_window_s`` seconds → HOOK (max density).
    - After a sentence/topic boundary with rising audio-visual energy → TENSION/PAYOFF.
    - Long steady stretch without payoff markers → RELEASE (narrative build-up).
    ``energy_curve`` is [(t, 0..1)] visual+audio energy samples; its local slope
    drives the tension/release decision.
    """
    if t <= hook_window_s:
        return PacingPhase("hook", 1.6)
    slope = _local_slope(energy_curve or [], t)
    if slope > 0.15:
        return PacingPhase("payoff", 1.35)
    if slope > 0.05:
        return PacingPhase("tension", 1.1)
    if slope < -0.05:
        return PacingPhase("release", 0.65)
    return PacingPhase("build", 0.85)


def _local_slope(curve: list[tuple[float, float]], t: float, win: float = 4.0) -> float:
    pts = [(x, y) for x, y in curve if abs(x - t) <= win]
    if len(pts) < 2:
        return 0.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom <= 1e-9:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in pts) / denom


def cadence_bounds(phase: PacingPhase, cfg: EditorialConfig) -> tuple[float, float]:
    """Min/max seconds between pattern interrupts, modulated by the wave."""
    lo = cfg.interrupt_min_seconds / phase.density
    hi = cfg.interrupt_max_seconds / phase.density
    return max(1.2, lo), min(12.0, hi)


# --------------------------------------------------------------------------
# Dead-space removal (adjustable thresholds)
# --------------------------------------------------------------------------

@dataclass
class DeadSpaceReport:
    removals: list[TimeRange] = field(default_factory=list)      # confident cuts
    shortenings: list[TimeRange] = field(default_factory=list)   # soft cuts (partial)
    preserved: list[TimeRange] = field(default_factory=list)     # emotional/comedic holds
    scores: list[DeadSpaceScore] = field(default_factory=list)


def find_dead_spaces(index: MultimodalIndex, *, duration_s: float, step_s: float = 0.5,
                     hard_threshold: float = 0.72, soft_threshold: float = 0.55,
                     min_span_s: float = 0.35, max_span_s: float = 8.0,
                     energy_curve: list[tuple[float, float]] | None = None,
                     protected_spans: list[TimeRange] | None = None
                     ) -> DeadSpaceReport:
    """Scan the fused timeline and merge contiguous high-score regions.

    Adjustable thresholds: ``hard_threshold`` ⇒ remove, ``soft_threshold`` ⇒
    shorten to ~60% (keep a breath), anything below soft is untouched. Spans
    overlapping protected regions (emotional holds, comedic beats, direct gaze)
    are preserved verbatim — the veteran-editor instinct encoded as policy.
    """
    protected = protected_spans or []
    grid = [round(i * step_s, 3) for i in range(int(duration_s / step_s) + 1)]
    scores = [score_dead_space(index, t, window=2.0,
                               motion_energy=_curve_at(energy_curve, t))
              for t in grid]
    report = DeadSpaceReport(scores=scores)

    def is_protected(t: float) -> bool:
        return any(p.start - 0.25 <= t <= p.end + 0.25 for p in protected)

    run_start: float | None = None
    run_hard = False
    for t, s in zip(grid, scores, strict=True):
        dead = s.value >= soft_threshold
        if dead and run_start is None:
            run_start, run_hard = t, s.value >= hard_threshold
        elif dead:
            run_hard = run_hard or s.value >= hard_threshold
        else:
            if run_start is not None:
                _flush(report, run_start, t, run_hard, is_protected(run_start),
                      min_span_s, max_span_s)
                run_start = None
    if run_start is not None:
        _flush(report, run_start, grid[-1], run_hard, is_protected(run_start),
               min_span_s, max_span_s)
    return report


def _flush(report: DeadSpaceReport, t0: float, t1: float, hard: bool, protected: bool,
           min_span: float, max_span: float) -> None:
    span = TimeRange(start=t0, end=min(t1, t0 + max_span))
    if span.duration < min_span:
        return
    if protected:
        report.preserved.append(span)
    elif hard:
        report.removals.append(span)
    else:
        report.shortenings.append(span)


def _curve_at(curve: list[tuple[float, float]] | None, t: float) -> float | None:
    if not curve:
        return None
    best = min(curve, key=lambda p: abs(p[0] - t))
    return best[1] if abs(best[0] - t) <= 1.5 else None


# --------------------------------------------------------------------------
# Cut-point snapping: never cut mid-word; prefer boundaries/onsets
# --------------------------------------------------------------------------

def snap_cut_point(t: float, index: MultimodalIndex, *, source_fps: float,
                   cfg: EditorialConfig,
                   transients: list[float] | None = None) -> CutPointCandidate:
    """Move a naive cut time to the nearest safe frame-aligned position.

    Anchors ranked by score contribution: shot boundary > silence midpoint >
    sentence boundary > audio transient sync. Hard constraint: the cut must NOT
    land inside a word (unless the word itself is being removed entirely).
    """
    frames = [t]
    for s in index.shots:
        frames += [s.start_time, s.end_time]
    ranges = index.doc.speech_ranges() if index.doc else []
    for a, b in ranges:
        frames += [a - 0.05, b + 0.05, (a + b) / 2 if b - a > 0.4 else a]
    for sent in (index.doc.sentences if index.doc else []):
        frames.append(sent.end + 0.08)
    for tr in transients or []:
        frames.append(tr)

    best: CutPointCandidate | None = None
    for f in frames:
        if f <= 0:
            continue
        snapped = round(round(f * source_fps) / source_fps, 6)
        violations: list[str] = []
        mid_word = _inside_word(snapped, index)
        if mid_word and cfg.cut_point_hard_no_mid_word:
            violations.append("mid_word")
        anchors: list[str] = []
        score = 0.4
        if any(abs(snapped - s.start_time) < 0.15 or abs(snapped - s.end_time) < 0.15
               for s in index.shots):
            anchors.append("shot_boundary")
            score += 0.35
        if any(abs(snapped - e.end) < 0.2 for e in (index.doc.sentences if index.doc else [])):
            anchors.append("sentence_boundary")
            score += 0.20
        sync = 0.0
        for tr in transients or []:
            if abs(tr - snapped) <= cfg.transient_sync_window_seconds:
                sync = 1.0 - abs(tr - snapped) / cfg.transient_sync_window_seconds
                break
        if sync > 0:
            anchors.append("audio_onset")
            score += 0.15 * sync
        if not mid_word:
            score += 0.10
        cand = CutPointCandidate(t=snapped, score=min(score, 1.0), anchors=anchors,
                                 components={"base": 0.4, "boundary": 0.35, "sync": sync},
                                 hard_constraint_violations=violations,
                                 transient_sync_score=sync)
        if violations:
            continue  # never choose an unsafe anchor when a safe one exists
        better = (best is None
                  or cand.score > best.score + 1e-9
                  or (abs(cand.score - best.score) <= 1e-9
                      and abs(cand.t - t) < abs(best.t - t)))
        if better:
            best = cand
    if best is None:
        snapped = round(round(t * source_fps) / source_fps, 6)
        best = CutPointCandidate(t=snapped, score=0.2, anchors=["fallback"],
                                 hard_constraint_violations=["no_safe_anchor"])
    return best


def _inside_word(t: float, index: MultimodalIndex) -> bool:
    return any(w.start < t < w.end for w in index.words_at(t))


# --------------------------------------------------------------------------
# J-cut / L-cut planning
# --------------------------------------------------------------------------

def plan_jl_cut(*, prev_sentence_end: float, next_sentence_start: float,
                rng_seed: int, cfg: EditorialConfig) -> JLCutPlan:
    """Alternate J/L deterministically (seeded RNG — LAW 5 reproducibility).

    J-cut: audio of the NEXT scene leads video by 150–400 ms.
    L-cut: audio of the PREVIOUS scene trails video by 150–500 ms.
    Chosen on sentence boundaries so dialogue flows like a real edit bay cut.
    """
    j_lo, j_hi = cfg.j_cut_lead_ms
    l_lo, l_hi = cfg.l_cut_tail_ms
    u = ((rng_seed * 1103515245 + 12345) >> 16) % 1000 / 1000.0  # deterministic LCG
    gap = next_sentence_start - prev_sentence_end
    if gap < 0.15:
        return JLCutPlan(cut_index=0, kind="hard", offset_ms=0,
                        rationale="speech too dense for overlap; hard cut keeps clarity")
    if u < 0.5:
        off = int(j_lo + u * 2 * (j_hi - j_lo))
        return JLCutPlan(cut_index=0, kind="j_cut", offset_ms=off,
                         rationale=f"audio leads video {off} ms (J-cut)")
    off = int(l_lo + (u - 0.5) * 2 * (l_hi - l_lo))
    return JLCutPlan(cut_index=0, kind="l_cut", offset_ms=-off,
                     rationale=f"video leads audio {-off} ms (L-cut)")


# --------------------------------------------------------------------------
# B-Roll & Zoom injector
# --------------------------------------------------------------------------

@dataclass
class InjectPlan:
    t: float
    duration: float
    kind: str                       # "zoom_move" | "broll_insert"
    scale_from: float = 1.0
    scale_to: float = 1.15
    keyword: str | None = None
    broll_asset_id: str | None = None
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    rationale: str = ""


def plan_static_shot_attacks(index: MultimodalIndex, *, cfg: EditorialConfig,
                             keywords: list[str], static_min_s: float = 4.0,
                             zoom_scale_to: float = 1.15,
                             broll_pool: dict[str, list[str]] | None = None
                             ) -> tuple[list[InjectPlan], list[Evidence]]:
    """If a talking head is static ≥ ``static_min_s``: inject slow digital zoom
    (1.0→scale_to) OR contextual b-roll when a keyword matches the b-roll pool.

    Never stacks two attacks closer than the phase-scaled cadence floor — that
    would destroy the release half of the tension/release wave.
    """
    plans: list[InjectPlan] = []
    evidence: list[Evidence] = []
    last_t = -1e9
    broll_pool = broll_pool or {}
    hits = index.keyword_hits(keywords)
    hit_times = {round(w.start, 2): kw for kw, w in hits}

    ordered = sorted(index.analyses, key=lambda a: a.frame_time)
    for a in ordered:
        shot = index.shot_at(a.frame_time)
        if shot is None or shot.duration < static_min_s:
            continue
        if a.visual_interest >= 0.35 or a.shot_type not in (
                "close_up", "medium_close_up", "medium", "extreme_close_up"):
            continue
        phase = classify_phase(a.frame_time, hook_window_s=cfg.cold_open_max_seconds * 3)
        lo, _hi = cadence_bounds(phase, cfg)
        if a.frame_time - last_t < lo:
            continue
        kw = _nearest_hit(hit_times, a.frame_time, within=2.5)
        broll_asset = _match_broll(kw, broll_pool)
        if kw and broll_asset:
            plan = InjectPlan(t=a.frame_time, duration=min(3.0, shot.end_time - a.frame_time),
                              kind="broll_insert", keyword=kw, broll_asset_id=broll_asset,
                              confidence=0.8,
                              rationale=f"keyword '{kw}' over static shot {shot.duration:.1f}s "
                                        f"→ contextual b-roll")
        else:
            plan = InjectPlan(t=a.frame_time,
                              duration=min(4.0, shot.end_time - a.frame_time),
                              kind="zoom_move", scale_from=1.0, scale_to=zoom_scale_to,
                              keyword=kw, confidence=0.75,
                              rationale=f"static shot {shot.duration:.1f}s, visual_interest "
                                        f"{a.visual_interest:.2f} → slow push-in "
                                        f"1.00→{zoom_scale_to:.2f}")
        ev = Evidence(type=EvidenceType.VLM_SEMANTIC, source_agent="editing_brain",
                      time_range=TimeRange(start=plan.t, end=plan.t + plan.duration),
                      payload={"kind": plan.kind, "shot_id": shot.shot_id,
                               "keyword": plan.keyword},
                      confidence=plan.confidence)
        evidence.append(ev)
        plan.evidence_ids.append(ev.evidence_id)
        plans.append(plan)
        last_t = a.frame_time
    log.info("inject_plans", count=len(plans))
    return plans, evidence


def plan_scale_text(p: InjectPlan) -> str:
    """Public helper for reports/UI: 'slow push-in 1.00→1.15'."""
    return f"{p.scale_from:.2f}→{p.scale_to:.2f}"


def _nearest_hit(hit_times: dict[float, str], t: float, within: float) -> str | None:
    best_kw, best_d = None, within
    for ht, kw in hit_times.items():
        d = abs(ht - t)
        if d <= best_d:
            best_kw, best_d = kw, d
    return best_kw


def _match_broll(kw: str | None, pool: dict[str, list[str]]) -> str | None:
    if not kw:
        return None
    assets = pool.get(kw.lower())
    return assets[0] if assets else None


# --------------------------------------------------------------------------
# Decision builder (confidence-scored, evidence-linked — LAW 1)
# --------------------------------------------------------------------------

def decisions_from_report(report: DeadSpaceReport, index: MultimodalIndex, *,
                          timeline_id: str, asset_id: str, source_fps: float,
                          cfg: EditorialConfig) -> list[EditDecision]:
    """Turn dead-space spans into EditDecisions snapped to safe cut points.

    Confidence formula blends detection strength with ASR precision — low
    confidence decisions become RED review markers downstream, never silent cuts.
    """
    out: list[EditDecision] = []
    for span in report.removals:
        snap = snap_cut_point(span.start, index, source_fps=source_fps, cfg=cfg)
        snap_end = snap_cut_point(span.end, index, source_fps=source_fps, cfg=cfg)
        if snap.hard_constraint_violations or snap_end.hard_constraint_violations:
            conf = 0.6          # flagged red — human decides
        else:
            base = _span_strength(report, span)
            asr = index.asr_precision_confidence(span.start, span.end)
            conf = min(0.99, base * (0.6 + 0.4 * max(asr, 0.5)))
        evs = [e for e in report.scores if span.start <= e.t <= span.end]
        ev_ids = [f"deadspace_{i}" for i in range(max(1, len(evs)))]
        out.append(EditDecision(
            timeline_id=timeline_id, source_asset_id=asset_id,
            start_time=snap.t, end_time=snap_end.t, action_type=_action_for(span, conf),
            confidence=conf, evidence_ids=ev_ids or ["deadspace_scan"],
            rationale=(f"dead space {span.duration:.2f}s removed "
                       f"(snap: {snap.anchors or snap_end.anchors or ['grid']})"),
            risk_level=_risk(conf)))
    return out


def _action_for(span: TimeRange, conf: float):
    from av_editor.domain.evidence import ActionType
    if span.duration < 0.25 and conf < 0.8:
        return ActionType.SHORTEN_PAUSE
    return ActionType.REMOVE_PAUSE


def _risk(conf: float):
    from av_editor.domain.evidence import RiskLevel
    if conf >= 0.9:
        return RiskLevel.LOW
    if conf >= 0.75:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def _span_strength(report: DeadSpaceReport, span: TimeRange) -> float:
    vals = [s.value for s in report.scores if span.start <= s.t <= span.end]
    if not vals:
        return 0.7
    return min(1.0, (sum(vals) / len(vals)) + 0.15 * math.log1p(span.duration))
