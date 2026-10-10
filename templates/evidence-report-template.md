# Evidence Report (example — Tier 2 web task)

Evidence reports are **not mandatory files** for T0/T1 (inline evidence is enough), and not even
automatic at T2 (concise inline delivery usually suffices). Use this shape when the user asks for
a report, or at T3 where a compact package genuinely helps. Keep it under one screen if possible.

---

**Task:** Add pricing section to marketing site from copy doc + brand palette.
**Tier:** T2 · **Domain:** web.md · **Date:** 2026-10-08

## Evidence collected & inspected
| Artifact | What I actually saw | Level |
|---|---|---|
| `shots/pricing-desktop.png` | 3 tiers render; Pro highlighted per brief; no overflow at 1440 | E3 |
| `shots/pricing-375.png` | Cards stack vertically; **found**: "Enterprise" button clipped (D1) | E3 |
| `logs/console.txt` | 0 errors after load + tab interaction | E3 |
| diff `src/sections/Pricing.tsx` | Only intended file changed; matches copy doc strings verbatim (checked line by line) | E3 |

## Defects found → fixed → re-verified
- D1 MAJOR: Enterprise CTA clipped at 375px (`shots/pricing-375.png`) → reduced padding + font
  step-down → re-shot `shots/pricing-375_v2.png`, button fully visible with 8px margin. Fixed.
- D2 MINOR: tier borders 1px vs spec's hairline token → switched to `--border-hairline`. No re-shot
  needed (value change verified in computed styles dump). Fixed.

## Known gaps (UNVERIFIED, disclosed)
- Hover/focus states: no browser-interaction tooling in this environment → gave manual checklist;
  marked UNVERIFIED.
- Real-device rendering: desktop-emulated screenshots only.

## Verdict
Delivered with one named gap. Claims above cite artifacts that were opened and read, not captured
and trusted.

---

*For T3, extend with: research cross-check table, direction rationale, all widths, accessibility
pass results, and ≤3 critique-cycle summaries — still bounded, still one document.*
