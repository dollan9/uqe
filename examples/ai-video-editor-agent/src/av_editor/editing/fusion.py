"""MODULE 2 (part A) — Multimodal fusion: map WhisperX word timestamps onto vision.

The editing brain must never reason about audio and video as separate worlds.
This module builds a fused, queryable timeline of "moments": for any time t we
can instantly ask *what words are being spoken*, *what shot are we in*, *what
does the VLM see*, *is the frame visually dead* — with confidence-weighted
answers that respect degraded evidence paths (unaligned ASR, missing VLM).
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from av_editor.domain.pacing import DeadSpaceScore
from av_editor.domain.transcript import TranscriptDocument, TranscriptWord
from av_editor.domain.vision import (CompositionMetrics, FaceTrack, ShotBoundary,
                                     VLMFrameAnalysis)
from av_editor.pipeline.vlm import detect_visual_dead_space


@dataclass
class FusedMoment:
    """Everything known about an instant on the source timeline."""
    t: float
    shot: ShotBoundary | None = None
    words: list[TranscriptWord] = field(default_factory=list)
    vlm: VLMFrameAnalysis | None = None
    faces: list[FaceTrack] = field(default_factory=list)
    composition: CompositionMetrics | None = None
    visual_dead: bool = False

    @property
    def speaking(self) -> bool:
        return bool(self.words)

    @property
    def static_talking_head(self) -> bool:
        if self.vlm is None or self.shot is None:
            return False
        return (self.shot.duration >= 4.0
                and self.vlm.visual_interest < 0.35
                and self.vlm.shot_type in ("close_up", "medium_close_up", "medium",
                                           "extreme_close_up"))


class MultimodalIndex:
    """Time-indexed fusion of transcript + shots + per-frame VLM analyses."""

    def __init__(self, *, doc: TranscriptDocument | None = None,
                 shots: list[ShotBoundary] | None = None,
                 analyses: list[VLMFrameAnalysis] | None = None,
                 dead_space_floor: float = 0.35,
                 dead_space_min_streak_s: float = 4.0) -> None:
        self.doc = doc
        self.shots = sorted(shots or [], key=lambda s: s.start_time)
        self._shot_starts = [s.start_time for s in self.shots]
        self.analyses = sorted(analyses or [], key=lambda a: a.frame_time)
        self._analysis_times = [a.frame_time for a in self.analyses]
        self.dead_spans = detect_visual_dead_space(
            self.analyses, interest_floor=dead_space_floor,
            min_streak_s=dead_space_min_streak_s) if self.analyses else []
        # Word index for O(log n) range queries.
        if doc is not None:
            self._words_sorted = sorted(doc.words, key=lambda w: w.start)
            self._word_starts = [w.start for w in self._words_sorted]
        else:
            self._words_sorted, self._word_starts = [], []

    # ---- queries -------------------------------------------------------
    def shot_at(self, t: float) -> ShotBoundary | None:
        if not self.shots:
            return None
        i = bisect.bisect_right(self._shot_starts, t) - 1
        if i < 0:
            return self.shots[0] if t <= self.shots[0].end_time else None
        s = self.shots[i]
        return s if t < s.end_time else None

    def words_at(self, t: float, *, window: float = 0.0) -> list[TranscriptWord]:
        lo = bisect.bisect_left(self._word_starts, t - window)
        out: list[TranscriptWord] = []
        for w in self._words_sorted[lo:]:
            if w.start > t + window:
                break
            if w.end >= t - window and w.start <= t + window:
                out.append(w)
        return out

    def analysis_at(self, t: float, *, tolerance: float = 0.6) -> VLMFrameAnalysis | None:
        if not self.analyses:
            return None
        i = bisect.bisect_left(self._analysis_times, t)
        best: VLMFrameAnalysis | None = None
        best_d = float("inf")
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(self.analyses):
                d = abs(self.analyses[j].frame_time - t)
                if d < best_d:
                    best, best_d = self.analyses[j], d
        return best if best_d <= tolerance else None

    def is_visual_dead(self, t: float) -> bool:
        return any(s.start <= t <= s.end for s in self.dead_spans)

    def moment(self, t: float) -> FusedMoment:
        a = self.analysis_at(t)
        return FusedMoment(t=t, shot=self.shot_at(t), words=self.words_at(t), vlm=a,
                           visual_dead=self.is_visual_dead(t))

    # ---- cross-modal helpers -------------------------------------------
    def keyword_hits(self, keywords: list[str]) -> list[tuple[str, TranscriptWord]]:
        """Case-insensitive keyword → word-timestamp mapping (Module 2 b-roll trigger)."""
        kws = [k.lower() for k in keywords]
        hits: list[tuple[str, TranscriptWord]] = []
        for w in self._words_sorted:
            cleaned = "".join(ch for ch in w.text.lower() if ch.isalnum())
            for kw in kws:
                norm_kw = "".join(ch for ch in kw if ch.isalnum())
                if norm_kw and norm_kw in cleaned:
                    hits.append((kw, w))
        return hits

    def speech_density(self, t0: float, t1: float) -> float:
        """Fraction of [t0,t1] covered by speech (word-level)."""
        if t1 <= t0:
            return 0.0
        covered = 0.0
        for w in self.words_at(t0, window=(t1 - t0)):
            lo, hi = max(w.start, t0), min(w.end, t1)
            if hi > lo:
                covered += hi - lo
        return min(covered / (t1 - t0), 1.0)

    def asr_precision_confidence(self, t0: float, t1: float) -> float:
        """Mean word confidence over a span; low when unaligned fallback was used."""
        ws = self.words_at((t0 + t1) / 2, window=(t1 - t0) / 2)
        if not ws:
            return 0.0
        return sum(w.confidence for w in ws) / len(ws)


def score_dead_space(index: MultimodalIndex, t: float, *, window: float = 2.0,
                     motion_energy: float | None = None,
                     emotional_hold: bool = False,
                     comedic_window: bool = False) -> DeadSpaceScore:
    """Blend five signals into one 0..1 dead-space score at time t.

    Components (all normalized 0..1, higher = deader):
      silence_excess          – no speech in the window
      low_visual_motion       – 1 - optical-flow energy (None ⇒ neutral 0.5)
      low_speech_density      – partial coverage counts partially
      low_focal_change        – proxy: same shot AND VLM says interest is low
      low_semantic_progress   – few new words vs typical rate
    """
    t0, t1 = max(0.0, t - window / 2), t + window / 2
    density = index.speech_density(t0, t1)
    silence = 1.0 if not index.words_at(t, window=window / 2) else 1.0 - density
    motion = 0.5 if motion_energy is None else max(0.0, 1.0 - min(motion_energy, 1.0))
    a = index.analysis_at(t)
    focal = 1.0 - (a.visual_interest if a else 0.5)
    span_words = index.words_at(t, window=window / 2)
    expected = max(1.0, (t1 - t0) * 2.2)  # ~2.2 words/sec conversational baseline
    semantic = max(0.0, 1.0 - len(span_words) / expected)
    value = (0.30 * silence + 0.20 * motion + 0.20 * (1.0 - density)
             + 0.15 * focal + 0.15 * semantic)
    if emotional_hold or comedic_window:
        value *= 0.5  # human editors protect these beats (Tension & Release)
    return DeadSpaceScore(
        t=t, value=min(value, 1.0), silence_excess=silence, low_visual_motion=motion,
        low_speech_density=1.0 - density, low_focal_change=focal,
        low_semantic_progress=semantic, emotional_hold=emotional_hold,
        comedic_window=comedic_window)
