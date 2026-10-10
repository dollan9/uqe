# MIGRATION & FIX LEDGER — dollan9/uqe (v3.1 → v3.2)

Brutal, honest list of what was broken and what the v3.2 restructure fixes.
Status legend: ✅ done & verified · ⚠️ done, partially verified · ⬜ open

## 0. Repo hygiene
- ✅ README clone URL + CI badge pointed at a foreign repo (`uhobnil/...`) → now `dollan9/uqe`.
- ✅ Toxic UX line removed ("quote the section number back at it. The rules are law, not vibes.").
- ✅ `ai-video-editor-agent/` moved out of root into `examples/ai-video-editor-agent/` (reference
  implementation for `modules/video.md`, no longer a second project in the repo root).
- ✅ `VERSION` + `CHANGELOG.md` added.
- ⚠️ LICENSE/attribution: MIT present; upstream attribution note kept in CHANGELOG.

## 1. Architecture — monolith → router (the core problem)
- Before: one ~500-line SKILL.md with `alwaysApply:true` → truncated and ignored by small models.
- After:
  - ✅ `AGENTS.md` — short always-loaded router (~48 lines, Prime Directive verbatim, routing table).
  - ✅ `SKILL.md` — 106-line router core, Sections 0–6 only.
  - ✅ `references/core-behavior.md` — full Sections 0–13 behavioral law, loaded on demand.
  - ✅ `modules/*.md` — per-domain depth, each routed, none preloaded.
  - ✅ `scripts/check_tools.sh` — honest tooling inventory before any evidence claim.
  - ✅ Memory pruning: `scripts/prune_memory.py` (preferences ≤500 tokens, lessons ≤20 + TTL).

## 2. Evidence — stop theatre, start measuring
- ✅ `evidence.schema.json` forces `{"evidence":[{type,path,observed,tool}],"defects":[…],"scores":{…}}`
  with enums + minItems — invention-resistant by construction.
- ✅ `scripts/validate_evidence.py` checks schema AND that every `path` exists on disk.
- ✅ Real verifiers (produce actual artifacts, fail loudly when tools missing):
  - `scripts/verify_web.sh` — playwright screenshots 1440/768/375 + axe audit + console log.
  - `scripts/verify_video.sh` — ffprobe JSON + EBU R128 loudnorm + 5 keyframes.
  - `scripts/verify_blender.py` — bpy non-manifold/degenerate geometry audit.
- ⚠️ End-to-end runs of verify_web.sh depend on host tooling (npx/playwright); readiness is
  probed via check_tools.sh instead of pretending.

## 3. Installer security
- ✅ `install.sh`: auto-detect tested (.cursor→cursor, AGENTS.md→codex, CLAUDE.md→claude,
  .windsurf→windsurf, empty→generic), `--dry-run`, `--with-sha` writes `.uqe/SHA256SUMS`,
  post-write verification greps the Prime Directive in the installed file, uninstall preserves
  user data outside managed blocks, cursor default is `alwaysApply:false`
  (opt-in override: `UQE_ALWAYS_APPLY=true`).
- ✅ SIGPIPE-safe logging (`log/vlog/die` with `|| :`) so piped CI invocations don't die.
- ✅ `install.ps1` PowerShell installer (parity with bash targets). ⚠️ Not executed here —
  no pwsh in this environment; syntax-reviewed only.

## 4. Research anti-hallucination
- ✅ `scripts/verify_citations.py` fetches every URL (urllib, no deps) and requires ≥3 sources
  across ≥2 classes; writes `http_status` back into the report; exits non-zero on 404/failure.
- ✅ `modules/research.md` mandates `verify/citations.json` with per-claim sources.

## 5. Tier system
- ✅ Tiers defined explicitly (T0–T3) in SKILL.md SECTION 2 with protocol + evidence column;
  examples extended in `modules/routing.md`.

## 6. CI truthfulness
- Before: workflow asserted `alwaysApply: true` (contradicting the fixed installer) and ran a
  "generality scan" banning vendor names from normative files — which made docs useless.
- After:
  - ✅ Generality-scan job deleted; replaced by Capability-First guidance in CONTRIBUTING.md.
  - ✅ Smoke tests assert `alwaysApply: false` + Prime Directive grep in the written file.
  - ✅ New smoke test for auto-detection; structure job validates AGENTS.md length/router refs,
    references/, scripts executability, VERSION/CHANGELOG presence.
  - ⬜ Green run pending push (remote not configured in this workspace).

## 7. Definition of Done tracker
- [x] README clone URL correct
- [x] AGENTS.md short router containing the Prime Directive
- [x] cursor rule default `alwaysApply:false`
- [x] `./install.sh --target cursor --dry-run` works
- [x] `./install.sh --target cursor` writes file; grep "Assume nothing" succeeds
- [x] scripts executable; shellcheck gate in CI
- [x] ai-video-editor-agent moved to examples/
- [ ] verify/ example evidence generated on a real target (needs host tooling; see check_tools.sh)
