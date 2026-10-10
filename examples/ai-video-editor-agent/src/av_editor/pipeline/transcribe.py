"""MODULE 1 (part C) — WhisperX word-level transcription bridge.

Design: whisperx is a heavy optional dependency (torch, models). This module
keeps the *conversion* logic pure and unit-testable, and isolates the actual
ASR call behind :func:`run_whisperx` so it can be mocked in tests and swapped
for another provider without touching downstream code.

Word timestamps come out in SOURCE-domain seconds; the model never needs to
know about proxies because audio analysis runs on full-quality audio extracted
from the original file (audio is cheap; pixels are not).
"""

from __future__ import annotations

from pathlib import Path

from av_editor.core.subprocess_runner import SubprocessRunner
from av_editor.domain.audio import VocalActivity
from av_editor.domain.evidence import Evidence, EvidenceType, TimeRange, new_id
from av_editor.domain.transcript import (EmphasisEvent, PitchPoint, Sentence,
                                         TranscriptDocument, TranscriptSegment,
                                         TranscriptWord)
from av_editor.errors import TranscriptionError
from av_editor.logging import get_logger

log = get_logger("av_editor.pipeline.transcribe")


def extract_audio_wav(src: Path, dst: Path, *, sample_rate: int = 16000,
                      runner: SubprocessRunner | None = None) -> Path:
    """Mono 16 kHz WAV for ASR/VAD from the ORIGINAL source (never the proxy)."""
    runner = runner or SubprocessRunner(default_timeout=600.0)
    ffmpeg = runner.require("ffmpeg", "Install FFmpeg >= 6.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    res = runner.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(src), "-vn", "-ac", "1", "-ar", str(sample_rate),
         "-c:a", "pcm_s16le", str(dst)],
        timeout=600.0, check=True)
    if not res.ok or not dst.exists():
        raise TranscriptionError("Audio extraction for ASR failed",
                                 src=str(src), stderr_tail=res.stderr[-500:])
    return dst


def run_whisperx(audio_path: Path, *, model_name: str = "large-v3",
                 align_model: str = "", align_lang: str = "en",
                 device: str = "auto", batch_size: int = 8,
                 diarize: bool = False) -> list[dict]:
    """Thin wrapper around whisperx — the ONLY place whisperx is imported.

    Returns the raw list of segment dicts (word-level when alignment enabled).
    Raises ImportError with a remediation hint if the extra isn't installed.
    """
    try:
        import whisperx
    except ImportError as exc:
        raise TranscriptionError(
            "whisperx is not installed",
            remediation="pip install 'ai-video-editor-agent[full]'") from exc

    compute_type = "float16"
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
        except ImportError:
            device = "cpu"
            compute_type = "int8"

    model = whisperx.load_model(model_name, device, compute_type=compute_type)
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=batch_size)

    if align_model:
        aligned = whisperx.align(result["segments"],
                                 whisperx.load_align_model(language_code=result["language"],
                                                            device=device),
                                 result["language"], audio, device,
                                 return_alignments=False)
        result = aligned

    if diarize:
        try:
            diar = whisperx.DiarizationPipeline(use_auth_token=None, device=device)
            turns = diar(str(audio_path))
            result = whisperx.assign_word_speakers(diar, result)
        except Exception as exc:  # diarization is best-effort, never fatal
            log.warning("diarization_failed", error=str(exc))
    return result.get("segments", [])


def segments_to_document(raw_segments: list[dict], *, asset_id: str,
                         language: str = "en", model_version: str = ""
                         ) -> tuple[TranscriptDocument, list[Evidence]]:
    """Convert raw WhisperX/Whisper segment dicts into the canonical document.

    Tolerant of missing keys (plain whisper output has no per-word timings —
    we then synthesize word times spread linearly across the segment, flagged
    with lower confidence so the editing brain knows precision dropped).
    """
    segments: list[TranscriptSegment] = []
    sentences: list[Sentence] = []
    speakers: set[str] = set()
    evidence: list[Evidence] = []
    sid = 0

    for seg in raw_segments:
        s0 = float(seg.get("start", 0.0))
        s1 = float(seg.get("end", s0))
        text = str(seg.get("text", "")).strip()
        if not text or s1 <= s0:
            continue
        seg_words: list[TranscriptWord] = []
        raw_words = seg.get("words") or []
        if raw_words:  # aligned (WhisperX) path: true word timestamps
            for w in raw_words:
                wt = str(w.get("word", "")).strip()
                if not wt:
                    continue
                word = TranscriptWord(
                    word_id=new_id("w"), text=wt,
                    start=max(s0, float(w.get("start", s0))),
                    end=min(s1, float(w.get("end", s1))),
                    speaker_id=w.get("speaker"),
                    confidence=float(seg.get("confidence", 0.9)),
                    sentence_id=sid)
                if word.end <= word.start:
                    word.end = min(word.start + 0.08, s1)
                seg_words.append(word)
        else:          # unaligned fallback: linear time allocation, low confidence
            toks = text.split()
            if toks:
                step = (s1 - s0) / len(toks)
                for i, tok in enumerate(toks):
                    seg_words.append(TranscriptWord(
                        word_id=new_id("w"), text=tok,
                        start=s0 + i * step, end=s0 + (i + 1) * step,
                        confidence=0.45, sentence_id=sid))
        if not seg_words:
            continue
        speakers.update(w.speaker_id for w in seg_words if w.speaker_id)
        segments.append(TranscriptSegment(
            segment_id=new_id("seg"), start=s0, end=s1, text=text,
            words=seg_words, speaker_id=seg_words[0].speaker_id,
            confidence=float(seg.get("confidence", 0.9)), language=language))
        sentences.append(_make_sentence(sid, seg_words, text))
        evidence.append(Evidence(
            type=EvidenceType.TRANSCRIPT, source_agent="transcriber", asset_id=asset_id,
            time_range=TimeRange(start=s0, end=s1),
            payload={"text": text, "word_count": len(seg_words)},
            confidence=float(seg.get("confidence", 0.9))))
        sid += 1

    doc = TranscriptDocument(
        asset_id=asset_id, language=language, segments=segments, sentences=sentences,
        words=words_all_flat(segments), pitch_contour=[], emphasis_events=[],
        speakers=sorted(s for s in speakers if s), model_version=model_version,
        diarization_enabled=bool(speakers))
    ev_extra = [Evidence(type=EvidenceType.TRANSCRIPT, source_agent="transcriber",
                         asset_id=asset_id, confidence=0.9,
                         payload={"kind": "speech_ranges",
                                  "ranges": [[a, b] for a, b in doc.speech_ranges()]})]
    return doc, evidence + ev_extra


def words_all_flat(segments: list[TranscriptSegment]) -> list[TranscriptWord]:
    return [w for s in segments for w in s.words]


def _make_sentence(sentence_id: int, words: list[TranscriptWord], text: str) -> Sentence:
    lowered = text.rstrip().lower()
    ends_with = "none"
    if lowered.endswith("."):
        ends_with = "period"
    elif lowered.endswith("?"):
        ends_with = "question"
    elif lowered.endswith("!"):
        ends_with = "exclamation"
    elif lowered.endswith(","):
        ends_with = "comma"
    return Sentence(sentence_id=sentence_id, start=words[0].start, end=words[-1].end,
                    text=text, word_ids=[w.word_id for w in words], ends_with=ends_with)


def vocal_activities_from_doc(doc: TranscriptDocument, *, min_gap_s: float = 0.3
                              ) -> list[VocalActivity]:
    """Derive VAD-style activities from word timings (no silero dependency)."""
    return [VocalActivity(start=a, end=b, probability=1.0)
            for a, b in doc.speech_ranges() if b - a > 0.05]


def build_emphasis_from_pitch(pitch: list[PitchPoint], *, threshold_semitones: float = 3.0,
                              snap_to_words: list[TranscriptWord] | None = None
                              ) -> list[EmphasisEvent]:
    """Prosody emphasis: f0 peaks above the voiced median by N semitones."""
    import math
    import statistics

    events: list[EmphasisEvent] = []
    voiced = [p for p in pitch if p.voiced and p.f0_hz and p.f0_hz > 50]
    if len(voiced) < 5:
        return events
    med = statistics.median([p.f0_hz for p in voiced])
    words = snap_to_words or []
    for p in voiced:
        cents = 1200.0 * math.log2((p.f0_hz or med) / med)
        if cents >= threshold_semitones * 100.0:
            nearest = _nearest_word(p.time, words)
            events.append(EmphasisEvent(
                word_id=nearest.word_id if nearest else "", time=p.time,
                score=min(cents / 600.0, 1.0), kind="pitch_peak"))
    return events


def _nearest_word(t: float, words: list[TranscriptWord]) -> TranscriptWord | None:
    best: TranscriptWord | None = None
    best_d = float("inf")
    for w in words:
        mid = (w.start + w.end) / 2.0
        d = abs(mid - t)
        if d < best_d:
            best, best_d = w, d
    return best if best_d <= 0.4 else None
