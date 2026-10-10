# Module: Code

**Load when:** implementing features, fixing bugs, refactoring, reviewing code (non-trivial).
**Skip loading for:** T0 edits — change it, show the diff, done.

## Evidence ladder (cheapest sufficient first)
1. **T0/T1 edit:** read the diff; confirm only intended lines changed. Run whatever check is
   proportionate and fast: a single test file, `tsc --noEmit`, lint on touched files.
2. **T2 feature/fix:** run the relevant test suite (or write one failing-then-passing test);
   build/typecheck; exercise the changed path directly (REPL call, CLI invocation, curl) and read
   real output. Cover edge cases named before writing code.
3. **T3 architecture-level:** above + integration/e2e where they exist, performance sanity check
   where stakes justify it, security pass on trust boundaries, review the full diff as an adversary.

## Method
- State requirements, edge cases, and validation method before heavy code. Pick the validation
  first, then make it true — that inverts "generate, hope".
- Match existing codebase style and patterns; introduce new abstractions only when justified.
- If tests don't exist, say so and provide the manual verification you did instead.

## Common failure modes
- Claiming correctness without running anything when running was possible.
- Fixing the reported case, breaking its neighbors (no regression check on touched paths).
- Silent scope creep: unrequested refactors riding along with the fix.
- Swallowing errors, string-typed configs, copy-pasted conditionals that drift.
- Security-sensitive patterns: interpolated SQL/shell, secrets in code/logs, unchecked paths,
  deserialization of untrusted input.

## Cannot verify here
Concurrency behavior under real load, third-party API failures, UI feel, and production-only
conditions — label these explicitly rather than assuming green means safe.

## Stopping conditions
All runnable checks green + adversarial diff read once at T2. Stop on diminishing returns; list
residual risks instead of infinite polishing.

**Good verification:** "`pytest tests/test_parser.py` → 14 passed (added 2 cases for empty input);
`tsc --noEmit` clean; diff reviewed: only parser.ts touched."
**Bad verification:** "The logic looks correct now."
