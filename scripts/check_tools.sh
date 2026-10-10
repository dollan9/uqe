#!/usr/bin/env bash
# =============================================================================
# UQE check_tools.sh — honest tooling inventory for the verification scripts.
# Run this BEFORE claiming any evidence. Missing tool = TOOLING GAP, never a
# fabricated artifact.
#
# Usage: ./scripts/check_tools.sh [--json]
# Exit codes: 0 = at least one verifier fully runnable; 2 = no verifier runnable
#             (everything is a gap — report UNVERIFIED honestly).
# =============================================================================
set -euo pipefail

JSON=0
[ "${1:-}" = "--json" ] && JSON=1

have() { command -v "$1" >/dev/null 2>&1; }

probe() { # name required_for
  local n="$1" role="$2"
  if have "$n"; then
    [ "$JSON" -eq 0 ] && printf 'OK      %-14s %s\n' "$n" "$role"
    eval "HAS_${n//[^a-zA-Z0-9_]/_}=1"
  else
    [ "$JSON" -eq 0 ] && printf 'GAP     %-14s %s\n' "$n" "$role"
    eval "HAS_${n//[^a-zA-Z0-9_]/_}=0"
  fi
}

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[ "$JSON" -eq 0 ] && printf '[uqe] Tooling inventory (checked %s)\n' "$NOW"
probe ffmpeg   "verify_video.sh: keyframes + loudnorm (EBU R128)"
probe ffprobe  "verify_video.sh: container/codec metadata"
probe node     "verify_web.sh: npx runner"
probe npx      "verify_web.sh: playwright + axe via npx"
probe python3  "verify_citations.py, validate_evidence.py, prune_memory.py, verify_blender.py"
probe shellcheck "CI: installer lint gate"
probe git      "general.md: git mv / diff evidence"

[ "$JSON" -eq 0 ] && echo ""
[ "$JSON" -eq 0 ] && printf '[uqe] Verifier readiness:\n'
runnable=0
video_ready=0
web_ready=0
python_ready=0

if [ "${HAS_ffmpeg:-0}" -eq 1 ] && [ "${HAS_ffprobe:-0}" -eq 1 ]; then
  [ "$JSON" -eq 0 ] && echo "  READY   scripts/verify_video.sh"
  video_ready=1
  runnable=1
else
  [ "$JSON" -eq 0 ] && echo "  GAP     scripts/verify_video.sh -> needs ffmpeg+ffprobe (apt install ffmpeg / brew install ffmpeg)"
fi
if [ "${HAS_npx:-0}" -eq 1 ]; then
  [ "$JSON" -eq 0 ] && echo "  READY   scripts/verify_web.sh (first run installs chromium via playwright)"
  web_ready=1
  runnable=1
else
  [ "$JSON" -eq 0 ] && echo "  GAP     scripts/verify_web.sh -> needs node/npx (or use: npx playwright screenshot manually once installed)"
fi
if [ "${HAS_python3:-0}" -eq 1 ]; then
  [ "$JSON" -eq 0 ] && echo "  READY   scripts/validate_evidence.py, prune_memory.py, verify_blender.py"
  [ "$JSON" -eq 0 ] && echo "  NOTE    scripts/verify_citations.py URL checks need 'pip install requests' (falls back to urllib)"
  python_ready=1
  runnable=1
else
  [ "$JSON" -eq 0 ] && echo "  GAP     python-based scripts unavailable"
fi

if [ "$JSON" -eq 1 ]; then
  cat <<EOF
{
  "checked_at": "$NOW",
  "runnable": $([ "$runnable" -eq 1 ] && echo "true" || echo "false"),
  "tools": {
    "ffmpeg": { "available": $([ "${HAS_ffmpeg:-0}" -eq 1 ] && echo "true" || echo "false") },
    "ffprobe": { "available": $([ "${HAS_ffprobe:-0}" -eq 1 ] && echo "true" || echo "false") },
    "node": { "available": $([ "${HAS_node:-0}" -eq 1 ] && echo "true" || echo "false") },
    "npx": { "available": $([ "${HAS_npx:-0}" -eq 1 ] && echo "true" || echo "false") },
    "python3": { "available": $([ "${HAS_python3:-0}" -eq 1 ] && echo "true" || echo "false") },
    "shellcheck": { "available": $([ "${HAS_shellcheck:-0}" -eq 1 ] && echo "true" || echo "false") },
    "git": { "available": $([ "${HAS_git:-0}" -eq 1 ] && echo "true" || echo "false") }
  },
  "verifiers": {
    "verify_video.sh": { "ready": $([ "$video_ready" -eq 1 ] && echo "true" || echo "false") },
    "verify_web.sh": { "ready": $([ "$web_ready" -eq 1 ] && echo "true" || echo "false") },
    "python_scripts": { "ready": $([ "$python_ready" -eq 1 ] && echo "true" || echo "false") }
  }
}
EOF
else
  echo ""
  if [ "$runnable" -eq 1 ]; then
    echo "[uqe] At least one verifier is runnable. For every GAP above you MUST emit:"
    echo "      STATUS: UNVERIFIED / GAP: <tool missing> / MANUAL COMMAND: <exact command>"
  else
    echo "[uqe] NO verifier runnable in this environment. All output must be marked UNVERIFIED."
  fi
fi

if [ "$runnable" -eq 1 ]; then
  exit 0
else
  exit 2
fi
