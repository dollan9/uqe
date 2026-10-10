---
name: Feature request
about: Propose a capability, module, or protocol change. You must define its evidence.
title: "[FEATURE] "
labels: enhancement
assignees: ''
---

<!--
THE CENTRAL QUESTION OF UQE IS: HOW WOULD WE KNOW IT WORKS?
Every feature proposal must answer it before any implementation is discussed. A proposal
without an evidence definition is a wish, not a specification — wishes get closed with
"reopened when you can name the artifact." Fill in ALL sections; the Evidence Definition
section gates review.
-->

## Problem Description

What cannot be done today, or is done badly? Describe the failure mode concretely:

- Which task types hit this gap? (Give at least one realistic scenario, as lived or observed.)
- What do agents currently produce instead of quality output in that scenario?
- Which existing SKILL.md section / module comes closest, and why does it fall short?

Link related issues if any exist. If your motivation is "an agent did X to me once," include
the transcript excerpt — anecdotes about real failures are the strongest design input we accept.

## Proposed Solution

Describe the mechanism, not the syntax. What rule changes, what new text/module/tooling, where
it lives (new file vs amendment to Sections 0–15 vs new domain module vs installer/template).

Include:

1. **Behavioral contract** — after this lands, what exactly must an agent DO differently?
   Write it as a testable instruction ("must produce artifact Y when condition Z"), not an
   aspiration ("should be more careful"). Aspiration-shaped proposals fail Section 4 critique
   and will be sent back.
2. **Generality check** — does this bind to one vendor/model/host? Normative files ban product
   names (CONTRIBUTING.md, The Generality Rule). If the benefit only exists on one host, say
   so and propose it as downstream integration instead.
3. **Interaction with existing rules** — which current rules touch this territory? Does the
   proposal contradict, duplicate, or supersede any? Name them by section number.

## Evidence Definition (required — this question gates review)

> **What counts as EVIDENCE in this domain/feature?**

Complete the sentence honestly: *This feature is working when I can point to ______.*

Specify:

| Field | Your answer |
|---|---|
| Named artifact(s) proving success | (file paths, log contents, screenshots, diffs, scores — inspectable things) |
| Measurable threshold | (counts, dimensions, pass/fail states — not vibes) |
| How the artifact is captured | (which command/pipeline produces it) |
| How a reviewer independently verifies it | (steps + expected observations, per SEEN standard) |
| What makes a claim UNVERIFIED without it | (the exact class of false success this prevents) |

If you cannot fill this table, stop here and open a discussion issue instead — designing the
evidence model IS the hard part of this proposal, and that work happens before drafting rules.

## Alternatives Considered

List at least two rejected options with reasons:

1. **Do nothing** — what is the cost of the status quo? Why is it unacceptable now?
2. **Smallest possible version** — could a wording tweak to an existing section achieve 80%?
   Why not chosen?
3. **Structural alternative** — different placement (module vs template vs CI check)? Tradeoffs?

Proposals that skip alternatives read like solutions searching for problems. They get asked for
this section even when the idea is good.

## Additional Context

Prior art worth citing (with links you actually read), example transcripts demonstrating the
gap, sketches of proposed text, migration notes for existing installs, anything else relevant.

<!--
Pre-submission check (delete this comment after confirming):
[x] Evidence Definition table fully filled with named artifacts and thresholds
[x] Behavioral contract written as testable instructions
[x] Generality checked against CONTRIBUTING.md rule
[x] At least two alternatives considered with honest tradeoffs
[x] Every source I cite was read by me (no citation laundering)
-->
