# Module: Writing

**Load when:** copy, marketing text, docs prose, microcopy (buttons, errors, empty states),
tone-sensitive rewrites. **Skip loading for:** T0 typo/word swaps — edit and show the diff.

## Evidence ladder
1. **T1 short text:** check against the brief yourself: audience, purpose, tone, length, banned
   words/constraints. Quote the requirement met, not just "done".
2. **T2 substantial piece:** draft → read it aloud-mode (scan for rhythm/clarity) → cut 10–20% →
   verify every factual claim made in the copy (writing inherits research rules).
3. **T3 voice-critical work:** reference samples analyzed first (sentence length, vocabulary,
   stance); draft; side-by-side comparison against a sample; anti-pattern pass.

## Method
- Establish audience, purpose, tone before writing. A vague word ("punchy", "professional",
  "less AI") is a direction to interpret, not a checkbox.
- Clarity beats buzzwords. Concrete verbs, specific nouns, one idea per sentence where possible.
- Microcopy is UX: button labels state the outcome ("Save draft"), errors state cause + fix,
  empty states point to the first action.
- Preserve the user's/brand's voice; do not flatten everything into neutral assistant prose.

## AI-tell detection (contextual, not a ban list)
Flag and fix only when they undercut the brief: hollow intensifiers ("truly", "effortlessly"),
not-opinion opener ("In today's fast-paced world"), rule-of-three compulsion, em-dash confetti,
"delve/leverage/seamless/unparalleled" clusters, hedge-stacked conclusions, bullet-list-anything
reflex. Normal rhetoric (metaphor, tricolon, emphasis) is fine when chosen on purpose. Ask "would
a human with this voice write it this way?" — not "is this word forbidden?".

## Common failure modes
- Buzzword substitution instead of meaning change.
- Over-long output for a small ask; padding paragraphs that restate the prompt.
- Unverified claims dressed as copy ("award-winning", "used by 10,000 teams").
- Killing personality while "improving clarity".

## Cannot verify here
Reader response. You can verify constraints, claims, and anti-patterns; persuasiveness needs real
audience testing — say so.

**Good verification:** "Checked against brief: ≤120 chars (117), no banned terms (grep clean),
two claims softened because sources (`pricing.md`, live page) didn't support them."
**Bad verification:** "Rewrote it to sound more premium."
