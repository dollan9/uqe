# Module: Routing (complexity tiers, reference)

Tier definitions and overrides live in SKILL.md Section 3 — this file only adds examples and
tie-breaking guidance. Do not restate the rules; apply them.

## Worked tier examples
| Request | Tier | Why |
|---|---|---|
| "Rename `Save` to `Done` in settings.ts" | T0 | one-line edit, visible diff is proof |
| "List files larger than 10M" | T0 | run command, show output |
| "Summarize this article" (provided) | T1 | no research needed, check against brief |
| "Add a dark-mode toggle to this app" | T2 | behavior change, needs interaction test |
| "Cut the dead air out of this interview" | T2 | audio evidence + sampled frames |
| "Make a premium clothing site with smooth animations" | T3 | vague creative direction |
| "Is library X safe for production auth?" | T2–T3 | stakes decide; high stakes ⇒ more cross-checks |

## Tie-breaking
- Ambiguous tier? Estimate cost of under-processing vs over-processing; pick the cheaper unless
  failure means data loss, security exposure, or public-facing output.
- Multi-domain task ("add a Blender-rendered product video to the site"): route by artifact, not
  by request — load web.md + video.md only for the parts you actually touch; general.md covers the
  glue work.
- A T0 request that reveals hidden scope mid-execution ("rename Save" → 14 files, generated code,
  locale keys): say so in one line, propose the expanded plan, get a nod if blast radius grew.
  Never silently turn a chore into a project.

## Override handling
- "Just do it" on something you'd rate T3: comply at T1, put remaining risks in Known gaps — one
  sentence, not a sermon.
- "Be thorough" never licenses infinite loops: still bounded by stop conditions (SKILL.md §3).
