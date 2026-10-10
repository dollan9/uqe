# UQE Preferences  (TEMPLATE — copy to .uqe/preferences.md, edit freely, delete anytime)

<!-- OPT-IN: this file only matters if you create it. The agent will not auto-seed memory.
     Keep it small (<= ~150 lines). NEVER store credentials, API keys, tokens, or sensitive
     personal data here — it is plaintext. Scope rules: entries marked [project] belong in
     .uqe/projects/<id>.md instead; unmarked entries are global taste. Current explicit
     requests always override anything in this file. "forget this" / "clear my preferences"
     works instantly. -->

## Visual
- Prefers restrained palettes; one accent color max unless a project says otherwise.
- Likes generous whitespace and consistent type scale; dislikes centered-everything layouts.

## Communication
- Terse answers by default; detail on request. No emoji in code comments or commit messages.
- Show diffs for edits; skip preamble like "Great question!".

## Quality thresholds
- Typo-free always (T0 applies too). Accessibility contrast ≥ WCAG AA on real text.
- Perf budget for marketing pages: LCP < 2.5s on mid-tier mobile when measurable.

## Domain-specific
- Web: semantic HTML first, ARIA only when semantics can't express it.
- Video: target −16 LUFS integrated for web content.

## Explicit dislikes
- Fade-up-on-scroll as a default animation (fine when justified by the brief).
- Lorem ipsum shipped in final deliverables.

## Project context
- <!-- e.g. [project: acme-site] Brand voice: dry wit, no exclamation marks. -->
