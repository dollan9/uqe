---
name: Bug report
about: Report a defect with evidence. Reports without evidence are closed, not triaged.
title: "[BUG] "
labels: bug
assignees: ''
---

<!--
NO EVIDENCE, NO TRIAGE.
UQE treats unverified claims as fraud (SKILL.md Rule 4). That standard applies to bug
reports too: describe what you OBSERVED, attach what you CAPTURED, and classify the harm
using the severity classes below. A report that says "it doesn't work" with no artifact
will be closed as unreproducible without further comment.
-->

## Severity Class (required — pick exactly one)

| Class | Definition |
|---|---|
| **BLOCKER** | The defect silently allows fabricated completion — the system produces or permits claims of success without evidence (e.g., installer reports VERIFIED without checking; a module lets an agent mark Phase 4 done with no named artifact; rule text contradicts so agents skip verification legitimately). This is the highest class. BLOCKERs get response within 24h. |
| **MAJOR** | Verified functionality is broken or misleadingly documented (install writes wrong path for a target; template example contradicts SKILL.md thresholds; cross-references point at nonexistent files). Workaround exists but costs real time. |
| **MINOR** | Cosmetic, wording, or clarity issues with no behavioral consequence (typos, table formatting, inconsistent heading depth). |

Severity: [BLOCKER / MAJOR / MINOR]

## Describe the Bug

One paragraph. What happened, where (file/section/target), and how severe it is *for an agent
following the protocol*, not just for you personally.

## Steps to Reproduce

Numbered, complete, minimal. Include exact commands typed and inputs given. If you cannot
reproduce it twice, say so explicitly in this section rather than hiding it — "single occurrence,
attempted reproduction 3 times, failed" is honest data; silence about irreproducibility is not.

1.
2.
3.

## Expected Behavior

What the governing text (cite file + section number) says should happen, quoted or linked.

## Actual Behavior

What happened instead. Paste raw output — do not paraphrase logs, error text, or diffs.

## Evidence (required)

Attach or paste every artifact you captured. Then state, per the SEEN standard, what you saw
when you examined each one — a log you did not read is not your evidence.

```
Artifact type | Path or inline paste | What I observed when I looked at it
```

Examples of acceptable evidence: terminal session transcript (with timestamps), `bash -n`
output, installer run logs with `--verbose`, diff of expected vs actual file content,
agent-session transcript excerpt showing the protocol violation, checksum before/after.

## Environment

- OS + version:
- Shell + version (`bash --version`):
- UQE version/tag or commit SHA (`git rev-parse HEAD` in the checkout):
- Install target used (`--target ...`) and whether auto-detection was involved:
- Agent host capability notes (tool access relevant to the defect; describe capabilities rather
  than naming products unless the product itself is the defect surface):

## Additional Context

Anything else: suspected root cause with reasoning shown, related issues, proposed fix direction
(optional — welcome, not required).

<!--
Pre-submission check (delete this comment after confirming):
[x] Severity class chosen and defensible against its definition above
[x] Reproduction attempted at least twice; results stated honestly
[x] Raw outputs pasted, not paraphrased
[x] Every attached artifact actually examined by me before filing
-->
