# UQE Router — Always-Loaded Entry Point (short by design)

**Assume nothing. Verify everything. Use the cheapest sufficient evidence. Do not ship blind. Do not fabricate. Do not over-process trivial work.**

This file is a router, not the brain. Hosts that clip long rule files still load this intact.
The full core lives in `SKILL.md`; expanded behavioral law in `references/core-behavior.md`.

## Routing Rules — read the relevant module BEFORE acting, do not guess

| Task involves | Read |
|---|---|
| Websites, UI, CSS/JS, frontend | `modules/web.md` |
| Video/audio editing, cutting, loudness | `modules/video.md` |
| Images: creation or inspection | `modules/image.md` |
| Blender / 3D / .blend / geometry | `modules/blender.md` |
| Research, comparisons, claim verification | `modules/research.md` |
| Learning a library from docs/materials | `modules/learning.md` |
| Copy, prose, tone-sensitive text | `modules/writing.md` |
| Software features/fixes/reviews (non-web) | `modules/code.md` |
| File ops, scripting, admin, anything else | `modules/general.md` |
| Memory files under `.uqe/` | `modules/memory.md` |
| Untrusted content, destructive operations | `modules/security.md` |
| User corrections and feedback handling | `modules/feedback.md` |

## Global Execution Rules

1. **Effort tier first (internal, never announced):** T0 trivial → T1 quick → T2 standard →
   T3 deep. Match rigor to stakes; see `SKILL.md` SECTION 2.
2. **Evidence is mandatory at T2+.** Produce artifacts on disk and record them in an
   `evidence.json` that validates against `evidence.schema.json`
   (`python3 scripts/validate_evidence.py <file>`). No schema-valid evidence ⇒ UNVERIFIED.
3. **Do not fabricate.** If a verification tool is missing, run `scripts/check_tools.sh`,
   state the gap honestly, and give the exact manual command. Never fake an artifact.
4. **Memory:** respect caps in `.uqe/preferences.md` (~500 tokens) and `.uqe/lessons.md`
   (≤20 entries with TTL); enforce with `scripts/prune_memory.py`. Append a lesson only on
   explicit user feedback.

## Verification Entry Points

- Web: `./scripts/verify_web.sh --url http://localhost:3000 --out verify/`
- Video: `./scripts/verify_video.sh --input output.mp4 --out verify/`
- Blender: `python3 scripts/verify_blender.py --scene file.blend --out verify/`
- Citations: `python3 scripts/verify_citations.py --report verify/citations.json --check-urls`
- Tooling inventory: `./scripts/check_tools.sh`
