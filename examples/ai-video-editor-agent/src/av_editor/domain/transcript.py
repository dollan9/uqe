"""Transcript domain models (§2.7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TranscriptWord(BaseModel):
    word_id: str
    text: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    speaker_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    sentence_id: int | None = None
    emphasis_score: float = 0.0
    emotion_score: float = 0.0

    @property
    def duration(self) -> float:
        return max(self.end - self.start, 0.0)


class TranscriptSegment(BaseModel):
    segment_id: str
    start: float
    end: float
    text: str
    words: list[TranscriptWord] = Field(default_factory=list)
    speaker_id: str | None = None
    confidence: float = 1.0
    language: str = "en"
    punctuation: bool = True


class Sentence(BaseModel):
    sentence_id: int
    start: float
    end: float
    text: str
    word_ids: list[str] = Field(default_factory=list)
    ends_with: Literal["period", "question", "exclamation", "comma", "none"] = "none"
    emotional_weight: float = 0.0


class PitchPoint(BaseModel):
    time: float
    f0_hz: float | None = None
    voiced: bool = False
    confidence: float = 0.0


class EmphasisEvent(BaseModel):
    word_id: str
    time: float
    score: float
    kind: Literal["pitch_peak", "duration_stretch", "loudness", "prosodic_boundary"]


class TranscriptDocument(BaseModel):
    asset_id: str
    language: str = "en"
    segments: list[TranscriptSegment] = Field(default_factory=list)
    sentences: list[Sentence] = Field(default_factory=list)
    words: list[TranscriptWord] = Field(default_factory=list)
    pitch_contour: list[PitchPoint] = Field(default_factory=list)
    emphasis_events: list[EmphasisEvent] = Field(default_factory=list)
    speakers: list[str] = Field(default_factory=list)
    model_version: str = ""
    diarization_enabled: bool = False

    def words_in_range(self, t0: float, t1: float) -> list[TranscriptWord]:
        return [w for w in self.words if w.end > t0 and w.start < t1]

    def first_speech_time(self) -> float | None:
        if not self.words:
            return None
        return min(w.start for w in self.words)

    def speech_ranges(self) -> list[tuple[float, float]]:
        """Merge word timings into contiguous speech ranges (gap > 0.3s splits)."""
        ordered = sorted(self.words, key=lambda w: w.start)
        ranges: list[tuple[float, float]] = []
        cur_start = cur_end = None
        for w in ordered:
            if cur_end is None or w.start - cur_end <= 0.3:
                cur_start = w.start if cur_start is None else cur_start
                cur_end = max(cur_end or 0.0, w.end)
            else:
                assert cur_start is not None and cur_end is not None
                ranges.append((cur_start, cur_end))
                cur_start, cur_end = w.start, w.end
        if cur_start is not None and cur_end is not None:
            ranges.append((cur_start, cur_end))
        return ranges
