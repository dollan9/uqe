# Contributing to UQE — Universal Quality Engine

**No evidence, no merge.** This is not a slogan; it is the review gate. Every pull request is
judged by the artifacts you produce to prove your change works, not by how confidently you
describe it. Read this entire file before opening your first PR.

UQE is a behavioral operating system for AI agents. That means contributions are mostly
*specification text and shell tooling*, and specification defects propagate into every agent
session that loads them. The bar is accordingly high. We appreciate all contributors and we
reject sloppy changes without apology. Both statements are true simultaneously.

## Contribution Taxonomy and Acceptance Bars

| Type | Definition | Acceptance bar |
|---|---|---|
| **Typo/clarity fix** | Non-semantic wording corrections in any doc | Diff shown inline in PR description; CI green. Fast-tracked. |
| **Behavior tweak** | Wording change that alters what an agent must do (rules, severities, thresholds) | Before/after comparison + reasoning + demonstration of the rule being followed or a cited failure mode it prevents. Reviewer must agree the change generalizes beyond one user's pain. |
| **New domain module** | A `modules/<domain>.md` following `templates/domain-template.md` | Full 7-point Module Acceptance Checklist below, plus registration edits, plus CI green. Requires 1 maintainer approval minimum. |
| **Installer/tooling change** | `install.sh`, CI workflows, templates | Smoke-test evidence: command outputs proving install/uninstall/dry-run behavior across affected targets (CI runs it too — your local proof still required). No silent behavior changes. |
| **SKILL.md core change** | Any edit to Sections 0–6 (router core) | Highest bar: proposal issue reviewed BEFORE implementation work, plus full structure-validation pass, plus argument for why this belongs in the brain rather than a module. Section 0 verbatim text is untouchable. |

## Adding a New Domain Module — Full Walkthrough

Keyed to [`templates/domain-template.md`](templates/domain-template.md). Do all steps; partial
modules are closed, not commented on.

1. **Copy the template:** `cp templates/domain-template.md modules/<yourdomain>.md`.
2. **Section 1 — Domain Name and Description.** Define exactly which task characteristics route
   here. This sentence becomes your row in the SKILL.md SECTION 3 domain router; write it
   so routing is unambiguous against existing domains. Overlap with an existing domain's routing needs
   justification.
3. **Section 2 — Evidence Definition. ⚠️ NON-NEGOTIABLE.** This section decides whether your
   module exists. State what artifact proves success in this domain, with thresholds
   (counts, dimensions, measurements, states) and naming conventions. Test your draft: could a
   reviewer verify your claim *only* from the named artifacts? If the answer involves "well,
   you can also just look at the code," the evidence definition is too weak. Domains whose
   evidence cannot be named are not automatable and will be rejected.
4. **Section 3 — Verification Pipeline.** Numbered steps, each producing its artifact, ending
   in an analysis step — never in a capture step. Include concrete commands.
5. **Section 4 — Defect Taxonomy.** Minimum five real defect classes with default severities.
   Hypothetical padding gets asked for field examples.
6. **Section 5 — Quality Metrics.** Domain metrics with measurement methods tied to artifacts.
   Must compose with the universal quality vocabulary in `modules/evidence.md`.
7. **Section 6 — Tool Requirements.** Probe commands + honest fallbacks (disclose gap → manual
   command for user → UNVERIFIED marking). "Skip verification" is not a permitted fallback.
8. **Section 7 — The SEEN Standard.** What it means to truly see output in this domain. If an
   agent could write compliant evidence lines without opening any artifact, rewrite this section.
9. **Section 8 — Registration.** Add a row to the SKILL.md SECTION 3 domain router table. An unregistered module
   does not exist — structure validation fails any module file missing from the router.
10. **Local checks:** run the two CI jobs locally (see `.github/workflows/ci.yml`: shellcheck +
    installer smoke tests, structure validation) before pushing.

## Module Acceptance Checklist (6 points — all mandatory)

A reviewer walks this list literally. One unchecked box = changes requested.

1. [ ] **Evidence defined and nameable.** Section 2 lists concrete artifacts with measurable
     requirements; every success claim maps to one.
2. [ ] **Pipeline terminates in analysis.** Section 3's final step requires reading/viewing/
     listening to captured artifacts (SEEN standard), not capturing them.
3. [ ] **Defect taxonomy ≥5 classes with severities**, drawn from real occurrences.
4. [ ] **Metrics measurable** — each domain metric names its measurement method and source artifact.
5. [ ] **Registered completely** — SKILL.md SECTION 3 routing row present; structure
     validation passes.
7. [ ] **Self-demonstration** — PR includes evidence of the module applied once: a worked
     example (even small) producing the artifacts the module demands, attached or path-referenced.

## The Capability-First Rule

Normative files (`SKILL.md`, `modules/`, `templates/`) state rules as **capabilities**
("an agent with browser automation access", "a code-execution environment"), not as
product marketing. Naming an integration target or tool convention where the wiring
actually requires it (installer targets, README setup docs, concrete verification
commands like `ffmpeg`/`playwright`) is fine and expected — docs that cannot name
their tools are useless. What remains banned is brand-gated *behavioral law*: rules
that only make sense for one vendor's product do not belong in the core; maintain
them as downstream integrations.

## Pull Request Process

1. **Open an issue first** for anything beyond typo fixes. Behavior changes and new modules
   need agreement before labor. Tier-3-style proposals get routed for maintainer comment.
2. Branch from `main`: `<type>/<short-slug>` (e.g., `module/audio-editing`).
3. Make the change. Run all three CI jobs locally if possible.
4. Fill the PR template **completely**. The Evidence section is mandatory and specific: state
   what artifacts you produced to verify your own change, and attach or reference them.
   "CI passed" alone is not sufficient evidence for normative-text changes — CI checks
   structure, not quality; say what you read and what you concluded.
5. Expect adversarial review. Reviewers apply the self-critique standard in `references/core-behavior.md` to your diff. Critique of
   the work is the culture; take it as such.
6. Merge criteria: all checklist items satisfied, CI green, at least one approving maintainer,
   no unresolved BLOCKER/MAJOR findings. Squash-merge with a message that states the outcome,
   not the file count.

## Style Guide

- **Tone:** strict, professional, intolerant of mediocrity. Imperative voice for rules
  ("You must…", "Never…"). Explanatory prose may be warm; requirements may not be soft.
- **Every requirement is actionable:** a reader must be able to perform it and check it. Ban
  "should" from rule text; use MUST/warn-by-default constructions deliberately.
- **Named artifacts everywhere:** refer to outputs by filename patterns, not gestures.
- **Format:** ATX headings (`#`–`###`), tables for matrices, fenced code blocks with language
  tags, line wrap ~100 chars, American spelling, serial commas.
- **Structure:** one concept per paragraph; numbered lists for sequences; no nested bullets
  deeper than two levels in normative files.
- **Cross-references:** cite SKILL.md sections by number ("Section 6.2") and modules by path
  (`modules/web.md`). Verify references exist — CI does.
- **Length honesty:** prefer deleting a redundant paragraph over hedging a weak one. Rules
  that repeat themselves dilute each other.

## Questions?

Open a `question`-labeled issue. You will get the same treatment as everything else here:
an answer backed by links to the governing text, or an admission that the spec has a hole —
which is itself a welcome bug report.
