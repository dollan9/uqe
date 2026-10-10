# Module: Image

**Load when:** creating, editing, inspecting, or transforming images (photos, sprites, mockups,
generated art). **Skip loading for:** T0 ops like a rename or reading dimensions.

## Evidence ladder
1. **T0/T1 probe:** actual pixel dimensions/format/size from output (`identify img.png`,
   `ffprobe`, or file bytes) — report what the tool printed.
2. **T1 crop/resize/compress:** open the result and look at it (host vision if available);
   check the specific region affected, not just the whole canvas.
3. **T2 meaningful edit:** full inspection + detail crops at 100% for edges, text, faces, seams;
   compare before/after side by side; verify format/quality constraints were met.
4. **T3 generated art direction:** inspect all candidates, judge against the stated intent
   (composition, palette, mood), keep a shortlist with reasons.

## Tools
Host image tools/vision first. Otherwise ImageMagick (`convert`/`magick`), Pillow via python3, or
FFmpeg single-frame extraction. Missing everything → give exact runnable commands, mark aesthetic
claims UNVERIFIED.

## Common failure modes
- Upscaled blur / compression artifacts visible at 100% but not in thumbnails.
- Wrong color profile (CMYK sneaking in), unexpected transparency on dark backgrounds.
- Cropping that cuts limbs/text/focal points; aspect distortion from naive resize.
- Text baked into raster that becomes untranslatable/unscalable.

## Cannot verify here
Metadata proves dimensions, never aesthetics. Without vision capability you cannot claim an image
"looks good", "is centered", or "has no artifacts" — describe only measurable facts and label the
rest UNVERIFIED for human review.

## Stopping conditions
One inspection pass per changed artifact. Stop once measurable constraints are met and visual
inspection found no high-impact defects.

**Good verification:** "Viewed `out.png` and 100%-crop of the logo region: edges crisp, no halo,
transparent background intact (alpha channel present per `identify -verbose`)."
**Bad verification:** "Converted to PNG, so quality is preserved."
