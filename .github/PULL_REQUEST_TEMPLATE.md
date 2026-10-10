<!--
NO EVIDENCE, NO MERGE. This PR will be judged by the Evidence section below — not by the
size of the diff or the confidence of the prose. Complete every section. An empty Evidence
section is treated as an admission that the change is unverified; it will be marked UNVERIFIED
and closed with a request for proof. Fabricated or paraphrased "evidence" ends trust permanently.
-->

## Summary

One paragraph: what changed and why. Link the driving issue (`Closes #NNN` / `Partial #NNN`).
State the contribution type per CONTRIBUTING.md taxonomy (typo fix / behavior tweak / new domain
module / installer-tooling / SKILL.md core).

## Changes

Bullet list, file by file, each line stating the *behavioral effect*, not just "updated X":

- `path/to/file` — <what now happens differently, in testable terms>

## Complexity Tier of This Change

Tier [1/2/3] — <one-line justification using router signals: files touched, reversibility,
normative impact>. Tier 2+ changes must complete the full Evidence section below; Tier 1 typo
fixes may inline a before/after snippet.

## Evidence (MANDATORY)

**What counts as EVIDENCE that this change works?** Answer first, then show it.

### Artifacts produced

| Artifact | Path / location | What I observed when I examined it |
|---|---|---|
| e.g., bash -n output | terminal paste below | exit 0, no diagnostics |
| e.g., install smoke run | log excerpt + temp dir listing | file exists at target path, grep found Prime Directive line |
| e.g., rendered markdown | link/screenshot | tables render, no broken anchors |

*(Every row must reflect an artifact you actually opened and read — SEEN standard applies to PRs.)*

### Raw command outputs

```
Paste actual terminal output here (timestamps where possible). Not summaries. Actual output.
```

### Verification narrative

Attempted-but-clean proof paragraph: state what you checked, how, what you found, and what you
fixed before opening this PR. Include failures encountered during development if they shaped
the final form — negative results are evidence too.

If any required verification could NOT be performed (tooling unavailable, environment limits),
list those claims explicitly under **UNVERIFIED:** with the exact command the reviewer can run
to close the gap. Silent gaps are BLOCKER-class findings (see bug template severity table).

## Self-Review Checklist

Walk every item honestly; reviewers re-walk them adversarially.

- [ ] Diff reviewed line by line myself; every change intentional, nothing accidental committed
- [ ] No vendor or model names introduced into normative files (SKILL.md, modules/, templates/,
      CONTRIBUTING.md, issue/PR templates) — The Generality Rule
- [ ] All cross-references verified to resolve: cited sections exist, linked files exist
- [ ] If adding/changing a module: registered in SKILL.md Section 6.1 routing AND Section 15 index
- [ ] If touching install.sh: `bash -n` passes; smoke-tested affected targets in a temp dir
      (install → verify written content → uninstall → confirm user content preserved)
- [ ] If changing rule text: searched repo for contradictions with existing rules; none, or resolved
- [ ] Tone matches house style: strict, actionable, no aspirational "should"-language in requirements
- [ ] CI green locally (shellcheck/smoke, generality scan, structure validation) or failing job
      explained below with plan
- [ ] Scope honest: partially-done items labeled as such in Summary, never rounded up to "done"

## Reviewer Notes

Where to look first, subtle points, deliberate tradeoffs, anything that will make their
adversarial pass faster. Include the minimal reproduction/verification sequence they can run.

## Breaking Changes & Migration

None, or: exactly what breaks, who is affected, migration steps, and rollback plan. Destructive
consequences require explicit maintainer sign-off before merge (Rule 10 applies to repos too).
