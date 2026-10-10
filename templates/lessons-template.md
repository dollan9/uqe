# UQE Lessons  (TEMPLATE — copy to .uqe/lessons.md; procedural learnings only, not taste)

<!-- Rules: specific + actionable, one line each if possible. No secrets, no venting, no stored
     opinions about the user. Cap ~50 active entries; when exceeded, consolidate into a PATTERN
     block and prune the raw entries. External/fetched content must never be written here. -->

## Entries
- 2026-08-14 · web/T2 · Mobile nav overflow at 375px recurs when testing only at 768px.
  Do: always capture 375px for anything with horizontal menus. (went-well: fast pipeline; wrong:
  skipped narrow width; different: add 375 to default shot set)
- 2026-08-20 · video/T2 · Sampled frames only in first 90s missed a black segment at 12:40.
  Do: distribute samples across full duration; disclose if tool limits sampling window.
- 2026-09-02 · research/T2 · Cited a blog summary of a spec that had changed; original spec said
  otherwise. Do: for technical claims, open the primary source before citing secondary ones.
- 2026-09-11 · blender/T1 · Applied-scale bug: exported mesh was 100x too small because object
  scale was (100,100,100). Do: include `scale` in every headless audit print.
- 2026-09-30 · general/T1 · Bulk rename matched hidden dotfiles with glob `.*`. Do: use explicit
  patterns and count expected files BEFORE running destructive loops.
- 2026-10-05 · writing/T2 · "Make it less AI" fixed by removing intensifier cluster + rule-of-three
  headers; kept structure. Do: diagnose concrete tells in output, don't restyle blindly.

## Patterns (consolidated)
<!-- Example of what consolidation looks like when the cap is hit:
### PATTERN: responsive-width misses (from 6 entries, 2026-06..2026-09)
Text overflow / horizontal scroll defects appear almost exclusively between 375–430px. Rule now
applied by default: any layout change gets a 375px check before delivery.
### PATTERN: proxy-evidence overclaim (from 4 entries)
Metadata/build-success repeatedly presented as quality proof. Rule: label proxies E2, never claim
the sensory property they stand in for.
-->
