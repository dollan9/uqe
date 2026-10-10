"""MODULE 1 (part D) — VLM integration: "the eyes of the editor".

Sends PROXY frames (never raw 4K) to a vision-language model at ~1 frame per
second and extracts, per frame: subject framing/shot type, emotion, action,
b-roll relevance ("recommended_use"), distractions and visual dead space
("visual_interest"). Output is validated against the strict
:class:`VLMFrameAnalysis` schema — an invalid response is a hard failure
(LAW 1: never fabricate analysis), with one explicit exception: if the user
opted into ``allow_cv_only_fallback`` we degrade to CV-only evidence and mark
it as such.

Provider: any OpenAI-compatible chat-completions endpoint (GPT-4o, Claude via
LiteLLM/OpenRouter, local vLLM). HTTP via httpx with retries + backoff.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from av_editor.domain.evidence import Evidence, EvidenceType, TimeRange
from av_editor.domain.vision import ShotType, VLMFrameAnalysis
from av_editor.errors import VLMProviderError, VLMResponseSchemaError
from av_editor.logging import get_logger
from av_editor.settings import VLMConfig

log = get_logger("av_editor.pipeline.vlm")

SYSTEM_PROMPT = """You are a veteran film editor analyzing ONE frame from a video proxy.
Return STRICT JSON only, matching exactly this schema (no markdown, no prose):
{
 "shot_type": one of extreme_close_up|close_up|medium_close_up|medium|medium_wide|wide|extreme_wide|over_the_shoulder|two_shot|group|product|screen_recording|broll_object|empty_scene|unknown,
 "subjects": [short descriptions],
 "action": "what is happening",
 "emotion": "neutral|happy|excited|serious|tense|sad|surprised|confident",
 "emotion_confidence": 0..1,
 "composition": {"rule_of_thirds":0..1,"headroom":0..1,"lead_room":0..1},
 "distractions": [items pulling attention from subject],
 "visual_interest": 0..1 (LOW = visual dead space: static, empty, repetitive),
 "motion_description": "camera/subject motion",
 "on_screen_text": [visible text],
 "brand_safety_flags": [],
 "recommended_use": subset of ["a_roll","b_roll","hook","cutaway"],
 "notes": ""
}
Judge "visual_interest" honestly: a locked-off talking head mid-monologue is often <0.35."""


def encode_frame_jpeg(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _extract_json_object(text: str) -> dict:
    """Robustly pull the first JSON object out of a model reply (some providers
    wrap it in ```json fences despite instructions)."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise VLMResponseSchemaError("No JSON object found in VLM reply",
                                         reply_head=text[:200])
        candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise VLMResponseSchemaError("VLM reply is not valid JSON",
                                     error=str(exc), reply_head=candidate[:200]) from exc


class VLMClient:
    """OpenAI-compatible vision client with deterministic settings (temp=0)."""

    def __init__(self, config: VLMConfig) -> None:
        if config.provider == "disabled":
            raise VLMProviderError("VLM provider disabled in config",
                                   remediation="set vlm.provider + AV_EDITOR_VLM_API_KEY")
        self.cfg = config
        self._client = None  # lazy httpx.Client

    def _http(self):
        if self._client is None:
            import httpx
            key = self.cfg.resolve_api_key()
            if self.cfg.provider == "openai_compatible" and not key:
                raise VLMProviderError(
                    f"API key env var '{self.cfg.api_key_env}' is not set",
                    remediation="export the key or set vlm.provider=hf_local")
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            self._client = httpx.Client(base_url=self.cfg.base_url, headers=headers,
                                        timeout=self.cfg.timeout_seconds)
        return self._client

    def analyze_frame(self, image_path: Path, *, shot_id: str, frame_time: float,
                      context: dict | None = None) -> VLMFrameAnalysis:
        payload = {
            "model": self.cfg.model,
            "temperature": 0.0,                       # determinism enforced by config too
            "max_tokens": 700,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": self._user_prompt(frame_time, context)},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{encode_frame_jpeg(image_path)}"}},
                ],
            }],
        }
        system = {"role": "system", "content": SYSTEM_PROMPT}
        payload["messages"].insert(0, system)

        last_err: Exception | None = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                resp = self._http().post("/chat/completions", json=payload)
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
                data = _extract_json_object(text)
                data.setdefault("shot_id", shot_id)
                data["frame_time"] = frame_time
                data["model"] = self.cfg.model
                data["prompt_version"] = self.cfg.prompt_version
                analysis = VLMFrameAnalysis.model_validate(data)
                analysis.shot_type = _coerce_shot_type(analysis.shot_type)
                return analysis
            except VLMResponseSchemaError:
                raise  # schema violations are not transient — fail fast, LAW 1
            except Exception as exc:  # network / provider hiccups → retry w/ backoff
                last_err = exc
                import time
                time.sleep(min(2 ** attempt, 8))
        raise VLMProviderError("VLM request failed after retries",
                               error=str(last_err), attempts=self.cfg.max_retries + 1)

    def _user_prompt(self, frame_time: float, context: dict | None) -> str:
        parts = [f"Frame at t={frame_time:.2f}s of the source timeline."]
        if context:
            if context.get("spoken_words"):
                parts.append("Words spoken near this frame: "
                             + ", ".join(context["spoken_words"]) + ".")
            if context.get("shot_duration"):
                parts.append(f"Current shot duration so far: {context['shot_duration']:.1f}s.")
        parts.append("Analyze now. JSON only.")
        return " ".join(parts)


def _coerce_shot_type(value: str) -> ShotType:
    allowed = {"extreme_close_up", "close_up", "medium_close_up", "medium", "medium_wide",
               "wide", "extreme_wide", "over_the_shoulder", "two_shot", "group", "product",
               "screen_recording", "broll_object", "empty_scene", "unknown"}
    v = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    return v if v in allowed else "unknown"  # type: ignore[return-value]


def analyze_frames(
    client: VLMClient,
    frame_paths: list[Path],
    *, asset_id: str, shot_id_for_time,  # callable(float) -> str
    contexts: dict[float, dict] | None = None,
) -> tuple[list[VLMFrameAnalysis], list[Evidence]]:
    """Batch driver: 1 call/frame; failures skip the frame but never abort the run.

    ``frame_times_from_path`` recovers the timestamp embedded by the proxy
    extractor (``frame_<ms>.jpg``), keeping proxy→source mapping lossless.
    """
    analyses: list[VLMFrameAnalysis] = []
    evidence: list[Evidence] = []
    contexts = contexts or {}
    skipped = 0
    for p in frame_paths:
        t = frame_time_from_path(p)
        sid = shot_id_for_time(t)
        try:
            a = client.analyze_frame(p, shot_id=sid, frame_time=t,
                                     context=contexts.get(t))
        except VLMProviderError as exc:
            skipped += 1
            log.warning("vlm_frame_skipped", path=str(p), error=exc.message)
            continue
        analyses.append(a)
        evidence.append(Evidence(
            type=EvidenceType.VLM_SEMANTIC, source_agent="vlm_analyzer",
            asset_id=asset_id, time_range=TimeRange(start=t, end=t + 0.001),
            payload={"shot_id": sid, "shot_type": a.shot_type, "emotion": a.emotion,
                     "visual_interest": a.visual_interest,
                     "recommended_use": a.recommended_use,
                     "model": a.model, "prompt_version": a.prompt_version},
            confidence=0.85))
    if skipped:
        log.warning("vlm_partial_coverage", analyzed=len(analyses), skipped=skipped)
    return analyses, evidence


def frame_time_from_path(path: Path) -> float:
    m = re.match(r"frame_(\d+)\.jpe?g$", path.name)
    if not m:
        raise VLMProviderError("Frame filename does not encode a timestamp",
                               path=path.name)
    return int(m.group(1)) / 1000.0


def detect_visual_dead_space(analyses: list[VLMFrameAnalysis], *, interest_floor: float = 0.35,
                             min_streak_s: float = 4.0) -> list[TimeRange]:
    """Contiguous spans where VLM visual_interest stays below the floor for at
    least ``min_streak_s`` — the exact regions Module 2 must attack with zooms
    or b-roll instead of hoping viewers stay."""
    ordered = sorted(analyses, key=lambda a: a.frame_time)
    spans: list[TimeRange] = []
    cur_start: float | None = None
    prev_t: float | None = None
    for a in ordered:
        if a.visual_interest < interest_floor:
            if cur_start is None:
                cur_start = a.frame_time
            prev_t = a.frame_time
        else:
            if cur_start is not None and prev_t is not None and prev_t - cur_start >= min_streak_s:
                spans.append(TimeRange(start=cur_start, end=prev_t))
            cur_start, prev_t = None, None
    if cur_start is not None and prev_t is not None and prev_t - cur_start >= min_streak_s:
        spans.append(TimeRange(start=cur_start, end=prev_t))
    return spans


def new_client(config: VLMConfig) -> VLMClient | None:
    if config.provider == "disabled":
        log.warning("vlm_disabled", note="CV-only evidence will be used; semantic depth reduced")
        return None
    return VLMClient(config)
