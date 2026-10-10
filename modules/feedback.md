# Module: Feedback (reference)

Core rules are SKILL.md Sections 4, 9, 10. This file is the correction-handling playbook.

## Interpret first, fix second
User corrections arrive in human language, not specs. Translate to perceptual goals:
- "less AI" → inspect the actual output and name concrete causes (stock gradient hero, fade-up on
  everything, filler headings, em-dash prose, three-card row). Fix causes, not adjectives. Never
  respond with an apology paragraph plus the same work lightly shuffled.
- "too clean / boring" → likely missing texture: density, contrast jumps, asymmetry, personality
  in microcopy — diagnose which against the brief before adding noise.
- "more premium" → restraint + craft signals (typography rhythm, spacing consistency, real
  imagery, fewer loud accents) — NOT automatically dark+gold+serif+blur. Ask what the brand means
  by premium if it's load-bearing.
- "make the logo bigger" → check whether the real issue is prominence/hierarchy; size may be the
  cheapest fix but placement/contrast may be the right one. State your reading in a line.

## Protocol
1. Acknowledge the specific defect observed (quote/re-show it), don't just say "good catch".
2. Verify it exists as described; if you disagree after investigation, say so once with evidence
   and defer to the user's call on taste.
3. Fix → re-inspect the changed artifact (SEEN standard) → deliver delta concisely.
4. Classify for memory: one-off tweak (no write) | durable preference (confirm scope, then write
   per memory.md) | process complaint (adjust behavior this session; log lesson if procedural).

## Anti-overgeneralization
Three feedbacks about the same surface ≠ a global rule. Pattern promotion requires user
confirmation ("want me to always do X?"). Repeated *same* feedback (>3 in session) means your
current approach is wrong at the root — stop iterating locally, step back, re-decode intent.

## Never
Never blame the brief, never silently swap unrequested changes in alongside the fix (scope creep
on correction turns one complaint into two), never mark a feedback-fix verified without looking
at the new output.

**Good:** "Confirmed: headline sits 6px from the image edge at 375px (`shots/before.png`). Added
section spacing; `shots/after.png` shows 32px gap. Noted 'tight mobile spacing' as project-scoped
until you say otherwise."
**Bad:** "Sorry! I've made it more premium now."
