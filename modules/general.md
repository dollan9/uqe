# Module: General

**Load when:** file operations, data manipulation, scripting, system administration, lists,
text processing — anything not covered by a specialized module.

## Core pattern: observe → act → observe → diff
1. Record current state (`ls`, `cat -n`, checksums, row counts — whatever fits).
2. Perform the action.
3. Record new state.
4. Compare; verify **only intended changes** occurred. Never assume a command succeeded because
   it returned quietly — read its output and re-check the state.

## Destructive ops: blast-radius rule
Before deleting, overwriting, mass-renaming, or bulk-modifying existing work, state:
- exactly what will change (paths, counts),
- what will NOT change,
- what cannot be undone,
then get explicit confirmation. Prefer reversible forms first (move to trash dir, write `.bak`
only when asked, copy-then-verify-then-delete).

## Evidence ladder
- T0: command output + one confirming observation (`mv x y && ls y`).
- T1: before/after snippet or listing for the touched items.
- T2+: diff of full affected scope (e.g., `diff <(sort before) <(sort after)`), spot-check N≥3
  transformed records against the rule.

## Common failure modes
- Off-by-one/glob damage: acting on more files than intended (`*` recursion, hidden files).
- Encoding/newline corruption in bulk text ops (silently converting CRLF, mangling UTF-8).
- Partial completion reported as complete (loop aborted at item 47/50).
- Sorting/grouping assumptions that break downstream consumers.

## Cannot verify here
Side effects outside your observable scope (other processes, remote systems you can't query) —
name them as gaps.

**Good verification:** "Renamed 23 files; `ls | grep -c 'IMG_'` = 0, count unchanged at 23; spot-
checked items 1, 12, 23 — extensions preserved."
**Bad verification:** "Ran the rename script, looks done."
