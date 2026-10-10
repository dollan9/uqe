# Module: Video

**Load when:** editing, cutting, trimming, grading, muxing, or checking video files.
**Skip loading for:** T0 ops (a rename, reading duration with ffprobe) — just run and report output.

## Evidence ladder
1. **T0/T1 probe:** `ffprobe -v error -show_format -show_streams file.mp4` → report resolution,
   fps, codec, duration from actual output.
2. **T1 single trim/cut:** re-probe the output; extract 1–3 frames around each cut boundary and
   look at them (`ffmpeg -ss <t> -i out.mp4 -frames:v 1 f.png`).
3. **T2 meaningful edit:** ≥5 keyframes sampled across the **whole timeline**, not just the first
   90 seconds (if a tool limit forces early sampling, disclose it); audio loudness check
   (`ffmpeg -i out.mp4 -af ebur128 -f null -` or `volumedetect`); inspect every frame captured.
4. **T3 full project:** scene-change detection if available (`-vf select='gt(scene,0.4)'`),
   waveform/loudness against target spec, per-segment frame sampling, then a real review pass of
   all captured evidence.

## Tools
Host video tools/vision first; otherwise FFmpeg/ffprobe. If FFmpeg is missing: say so, give the
install hint and the exact commands you would have run, mark visual/audio claims UNVERIFIED, and
still deliver the edit instructions or script the user can run.

## Common failure modes
- Jump cuts and continuity breaks between adjacent sampled frames.
- Audio clipping/dead air; loudness far off target; A/V drift on re-encode.
- Wrong aspect ratio or unintended letterboxing after crop/scale.
- Compression artifacts introduced by aggressive re-encode settings.
- Claiming pacing or emotional effect from stills.

## Cannot verify here
Frames do not prove pacing, motion quality, or narrative impact; metadata does not prove picture
or sound quality. Without playback + listening (host capability), state exactly which judgments
remain human work.

## Stopping conditions
One critique pass at T2. Re-extract frames only where content actually changed. Deliver with named
gaps ("color consistency between 04:10–07:00 not inspected frame-by-frame").

**Good verification:** "Extracted and viewed 6 frames at 0%, 20%, 40%, 60%, 80%, 99% of
`out.mp4`: no black frames, lower-third legible throughout; ebur128 integrated −16.1 LUFS."
**Bad verification:** "Rendered successfully, so the edit looks good."
