#!/usr/bin/env bash
# verify_video.sh — UQE video verification: keyframes across timeline + loudness.
# Artifacts: frames/keyframe-NN-tSSSs.png, ffprobe-metadata.json, loudnorm-measure.txt
# Usage: ./scripts/verify_video.sh <input.mp4> [out_dir] [num_keyframes]
# Degrades honestly (exit 2 + manual command) when ffmpeg is missing.
set -euo pipefail

IN="${1:?usage: verify_video.sh <input> [out_dir] [n_frames]}"
OUT_DIR="${2:-verify/video}"
N="${3:-8}"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "[verify_video][UNVERIFIED] ffmpeg/ffprobe not installed — no frames or loudness data produced." >&2
  echo "[verify_video] Manual equivalent:" >&2
  echo "  ffprobe -print_format json -show_format -show_streams '$IN' > ffprobe-metadata.json" >&2
  echo "  ffmpeg -i '$IN' -vf fps=$N/DURATION frames/f%02d.png" >&2
  echo "  ffmpeg -i '$IN' -af loudnorm=print_format=json -f null -" >&2
  exit 2
fi

mkdir -p "$OUT_DIR/frames"

# --- Duration ---------------------------------------------------------------
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$IN" | tr -d '[:space:]')
[ -n "$DUR" ] && [ "$DUR" != "N/A" ] || { echo "[verify_video][ERROR] cannot read duration of $IN" >&2; exit 1; }

# --- Metadata artifact -------------------------------------------------------
ffprobe -v error -print_format json -show_format -show_streams "$IN" > "$OUT_DIR/ffprobe-metadata.json"
echo "[verify_video] wrote $OUT_DIR/ffprobe-metadata.json (duration ${DUR}s)"

# --- Keyframes evenly spread across the WHOLE timeline -----------------------
STEP=$(awk -v d="$DUR" -v n="$N" 'BEGIN{printf "%.3f", d/(n+1)}')
i=0
while [ "$i" -lt "$N" ]; do
  T=$(awk -v s="$STEP" -v i="$i" 'BEGIN{printf "%.2f", s*(i+1)}')
  TAG=$(printf "%02d-t%04.0fs" "$((i+1))" "$T")
  ffmpeg -v error -ss "$T" -i "$IN" -frames:v 1 -q:v 2 "$OUT_DIR/frames/keyframe-$TAG.png" -y
  i=$((i+1))
done
echo "[verify_video] wrote $N keyframes under $OUT_DIR/frames/ (timestamps spread over full duration)"

# --- Loudness (two-pass measure; target ~-14 LUFS for online delivery) -------
ffmpeg -hide_banner -nostats -i "$IN" -af "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json" -f null - \
  > "$OUT_DIR/loudnorm-measure.txt" 2>&1 || true
LUFS=$(grep -Eo '"input_i"[[:space:]]*:[[:space:]]*"?[-0-9.]+' "$OUT_DIR/loudnorm-measure.txt" | grep -Eo -- '[-0-9.]+$' | head -1 || true)
TP=$(grep -Eo '"input_tp"[[:space:]]*:[[:space:]]*"?[-0-9.]+' "$OUT_DIR/loudnorm-measure.txt" | grep -Eo -- '[-0-9.]+$' | head -1 || true)
echo "[verify_video] measured loudness: ${LUFS:-?} LUFS, true peak ${TP:-?} dBTP (target ≈ -14 LUFS, ≤ -1 dBTP)"

# --- Scene-change sanity (optional, uses scdet filter) ------------------------
ffmpeg -v error -nostats -i "$IN" -vf "select='gt(scene,0.4)',metadata=print" -an -f null - \
  > "$OUT_DIR/scenes.txt" 2>&1 || true
SCENES=$(grep -c "pts_time" "$OUT_DIR/scenes.txt" || true)
echo "[verify_video] hard-cut candidates detected: ${SCENES:-0} (see $OUT_DIR/scenes.txt)"

echo "[verify_video] NEXT: VIEW every keyframe and WRITE one observed line per frame (content, framing, continuity). Reading metadata alone is E2, never visual truth. Then build the evidence JSON and validate with scripts/validate_evidence.py."
