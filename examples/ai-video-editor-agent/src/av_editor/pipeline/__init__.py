"""Production pipeline stages: proxy vision engine, scene detection, VLM analysis,
transcription bridge, and the NLE export bridges.

Heavy third-party dependencies (ffmpeg via subprocess, scenedetect, whisperx,
cv2) are imported lazily inside functions so this package stays importable
with a minimal install — see ``[project.optional-dependencies].full``.
"""
