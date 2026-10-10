"""Typed exception hierarchy for the AV Editor Agent.

All errors carry structured context so logs and audit reports remain
diagnosable without stack-forensics. No error is ever swallowed silently.
"""

from __future__ import annotations

from typing import Any


class AVEditorError(Exception):
    """Base class for every error raised by av_editor."""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context

    def to_dict(self) -> dict[str, Any]:
        return {"error": type(self).__name__, "message": self.message, "context": self.context}


class MediaIngestError(AVEditorError):
    """Media file is missing, unreadable, corrupt or unsupported."""


class FFmpegError(AVEditorError):
    """An ffmpeg invocation failed (non-zero exit, timeout, or missing binary)."""


class FFprobeError(AVEditorError):
    """An ffprobe invocation failed or returned unparseable metadata."""


class TranscriptionError(AVEditorError):
    """WhisperX / ASR stage failed or produced an unusable transcript."""


class VisionAnalysisError(AVEditorError):
    """A computer-vision stage failed to produce usable evidence."""


class VLMProviderError(AVEditorError):
    """The configured Vision-Language Model provider is unreachable or errored."""


class VLMResponseSchemaError(VLMProviderError):
    """The VLM returned a payload that violates the strict JSON schema.

    Per LAW 1 the system never fabricates analysis; an invalid response is a
    hard failure, not a silent fallback.
    """


class TimelineConstructionError(AVEditorError):
    """Canonical timeline invariants were violated during construction."""


class NLEBridgeError(AVEditorError):
    """An NLE export bridge failed."""


class ResolveConnectionError(NLEBridgeError):
    """DaVinci Resolve scripting environment could not be located or connected."""


class CapabilityUnavailableError(AVEditorError):
    """An optional external capability (library, binary, API) is unavailable."""


class ComplianceError(AVEditorError):
    """A benchmark/export operation would violate licensing or platform policy."""


class QACriticalError(AVEditorError):
    """The Visual QA Critic blocked export due to critical violations."""


class ConfigurationError(AVEditorError):
    """Configuration file is missing, malformed, or fails schema validation."""
