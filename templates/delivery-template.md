# Delivery Contract (example shapes — keep replies this short)

The default user-facing format is SKILL.md Section 9: Result · Verification · Assumptions ·
Known gaps · Next step. Omit empty sections. Never dump internal process unless asked.

## T0 example ("rename Save to Done in settings.ts")
> Done — `settings.ts:14,37`: both labels now "Done" (diff above). No other matches for the
> string in the file; build untouched so no re-verify needed beyond reading the diff.

## T2 example ("add a pricing section")
> **Result:** Pricing section added (`src/sections/Pricing.tsx`, wired into index page).
> **Verified:** Viewed desktop + 375px screenshots — layout clean, found and fixed a clipped CTA
> at mobile (`shots/pricing-375_v2.png`); console log clean.
> **Assumed:** Monthly/annual toggle not requested → omitted; say if wanted.
> **Gaps:** Hover states UNVERIFIED (no interaction tooling here); manual check: tab through cards.
> **Next:** Review copy against brand doc — I matched the provided text verbatim.

## Honest-failure example (missing tool)
> Couldn't verify audio loudness: FFmpeg isn't installed in this environment, so I can't measure
> LUFS honestly. Tried: host tools (none), python libs (no decoder). Run locally:
> `ffmpeg -i out.mp4 -af ebur128 -f null -` (target −16 LUFS integrated). Marking audio quality
> UNVERIFIED; everything else in the edit was checked as listed above.

## Anti-patterns (do not ship these)
- "I have completed Phase 3 of Intent Validation…" — internal narration on the user.
- A 40-line report for a one-line change — over-processing is a defect.
- "It looks great and fully responsive!" with no named artifact — fake confidence.
- Apology paragraph + same work reshuffled after feedback — diagnose the actual complaint instead.
