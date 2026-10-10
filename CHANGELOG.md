# Changelog — Universal Quality Engine

## [3.2.0] - 2026-10-09
### Changed
- Architecture: SKILL.md reduced to a 106-line router core (Sections 0–6); full behavioral law
  moved on-demand to `references/core-behavior.md`; new short always-loadable `AGENTS.md` router.
- Cursor target default is now `alwaysApply: false` (opt in via `UQE_ALWAYS_APPLY=true`).
- README clone URL and CI badge corrected to `github.com/dollan9/uqe`.
- CI: generality-scan job removed (banning tool names made docs useless); replaced with the
  Capability-First guidance in CONTRIBUTING.md. Installer smoke tests now assert
  `alwaysApply: false`, Prime Directive presence in written files, and auto-detection.
- `ai-video-editor-agent/` relocated from repo root to `examples/` as a reference implementation.
- Toxic phrasing removed from README ("law, not vibes").
### Added
- `evidence.schema.json` + `scripts/validate_evidence.py` (schema check + artifact-exists check).
- Real verification scripts: `verify_web.sh` (playwright 1440/768/375 + axe), `verify_video.sh`
  (ffprobe + EBU R128 loudnorm + keyframes), `verify_blender.py` (non-manifold audit),
  `verify_citations.py` (HTTP-fetches every cited URL), `check_tools.sh` (tooling inventory),
  `prune_memory.py` (preferences ≤500 tokens, lessons ≤20 entries with TTL).
- `install.ps1` PowerShell installer; `--with-sha` SHA256SUMS integrity record in install.sh.
- MIGRATION.md fix ledger, VERSION file.
### Fixed
- install.sh SIGPIPE failures under piped CI invocations (`printf: write error: Broken pipe`).
- Dead code in cache invalidation and stale section references across modules/CONTRIBUTING.

## [3.0.0] - earlier
- v3 monolithic SKILL.md with Sections 0–15, three-gate CI (installer, generality, structure).
- Attribution note: v1/v2 lineage drew ideas from prior art; MIT license retained.
