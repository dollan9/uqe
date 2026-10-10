# Module: Learning

**Load when:** acquiring new knowledge from docs, tutorials, codebases, or materials; explaining a
concept you must first understand. **Skip loading for:** things you already know — teach directly.

## Evidence ladder
1. **T1 quick understanding:** summarize in your own words (not copy-paste); one concrete example.
2. **T2 verified comprehension:** summary + execute at least one practical example with real tools
   and read its actual output + 3–5 self-quiz questions with justified answer keys.
3. **T3 deep skill acquisition:** above, plus edge-case experiments, a misconception list ("what a
   beginner gets wrong here and why"), and a minimal cheatsheet the user can reuse.

## Method
- Read the source material itself; don't learn from vibes of its title.
- Summarizing in your own words is the comprehension test — if you can't compress it, you didn't
  get it.
- Executing examples beats describing them: run the code, note real output, flag where docs are
  stale or wrong.
- Quiz questions must test understanding ("why does this break?") not recall ("what is X called?").
  Verify your own answer keys against executed behavior or primary sources.

## Common failure modes
- Parroting documentation without demonstrating understanding.
- Examples that were never run and don't actually work.
- Quizzes testing trivia; answer keys asserted, not checked.
- Missing prerequisites the learner actually needs.

## Cannot verify here
Retention and true understanding over time can't be measured in-session; say what evidence exists
(executed outputs, correct justifications) and what remains the human's side of the bargain.

**Good verification:** "Ran the retry decorator example from the docs; observed backoff sequence
1s/2s/4s in `run.log`; doc's claim about jitter is outdated — corrected in summary."
**Bad verification:** "I have read and understood the documentation."
