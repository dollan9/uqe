# Module: Evidence (reference)

The universal rules are SKILL.md SECTION 4 (Evidence Contract). This file is the cross-domain ladder and vocabulary.

## Evidence quality levels
| Level | Meaning | Example labels |
|---|---|---|
| **E3 Direct** | You observed the real artifact and can name it | viewed screenshot, read test output, inspected diff |
| **E2 Derived** | Measured proxy that supports but doesn't prove the claim | ffprobe metadata, HTTP status, lint pass |
| **E1 Asserted** | Reasoning only — never present as verification | "the code should render correctly" ⇒ mark UNVERIFIED |

Rule of thumb: a claim's level is the *lowest* evidence level supporting it. Downgrade honestly.

## Cross-domain ladder (cheapest sufficient first)
- **code:** failing→passing test › suite run › typecheck/lint › executed invocation › diff review
- **files:** before/after listing or diff › checksums › command exit output
- **text/copy:** quoted passage vs stated constraints › char/word counts › claim citations
- **research:** cross-check table with sources read › single citation › none (= opinion, label it)
- **web:** viewed screenshots at relevant widths + console log › DOM/source checks (E2 for visuals)
- **video/audio:** frames sampled across whole timeline + loudness measurement (viewed/read) ›
  ffprobe metadata (E2) › filename hopes (E1)
- **image:** visual inspection incl. detail crops (host vision) › tool-measured dimensions/format
- **3d:** renders viewed from ≥2 angles + audit script output read › script output alone (E2 for looks)
- **learning:** executed example output + checked quiz answers › written summary (E1 comprehension)

## Never-as
DOM ≠ sight · metadata ≠ quality · frames ≠ pacing · CSS ≠ motion feel · build green ≠ design good ·
audit clean ≠ beautiful · reading ≠ running.

## Artifact naming
Store evidence where the user can open it: `shots/home-375.png`, `logs/console.txt`,
`frames/f04-t92s.png`. Reference by path in delivery. Ad-hoc inline excerpts (diff, output lines)
count as named artifacts for T0/T1.

## Cache & invalidation
Evidence stays valid while the underlying artifact is unchanged (same content hash / same file).
After any change that could affect the verified property, re-capture only the affected evidence.
Re-running the entire pipeline on every tweak is over-processing; trusting stale evidence after a
material change is shipping blind. Both are violations.
