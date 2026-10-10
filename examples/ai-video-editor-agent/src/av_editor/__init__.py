"""AV Editor Agent: vision-powered autonomous video editing system.

Every package under ``av_editor`` is import-safe without the optional heavy
dependencies (torch, whisperx, mediapipe, scenedetect, opentimelineio). Those
are imported lazily inside the modules that use them and raise
:class:`av_editor.errors.CapabilityUnavailableError` when absent, so the core
pipeline, deterministic CV engines, exports and tests run on a bare install.
"""

__version__ = "1.0.0"
MODULE_VERSION = "1.0.0"
