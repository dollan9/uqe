#!/usr/bin/env bash
# =============================================================================
# UQE v3.2 Installer — Universal Quality Engine
# =============================================================================
# Installs the UQE behavioral layer (SKILL.md router core + modules/ + templates/
# + references/ + evidence.schema.json + scripts/) into an agent environment.
# Supports the common instruction-file conventions plus a fully manual target for
# any other agent. Windows users: use install.ps1 (PowerShell) or --target generic.
#
# Targets:
#   cursor    -> .cursor/rules/uqe.mdc  (front-matter; default alwaysApply: false,
#                                         override with UQE_ALWAYS_APPLY=true)
#   claude    -> CLAUDE.md              (marker-delimited block appended in place;
#                                         user content outside markers is preserved)
#   codex     -> AGENTS.md              (same marker-block protocol as claude)
#   gemini    -> GEMINI.md              (same marker-block protocol as claude)
#   windsurf  -> .windsurf/rules/uqe.md (full SKILL.md content)
#   generic   -> creates .uqe/UQE-INSTRUCTIONS.md (core skill copy) and prints
#                 wiring steps for any agent that accepts instruction files
#   manual    -> prints wiring instructions only (writes nothing)
#
# Flags:
#   --target <name>   Force a target (skips auto-detection)
#   --dest <dir>      Destination directory (or use UQE_DEST env var)
#   --dry-run         Preview all actions without writing anything
#   --uninstall       Remove UQE (marker block for append-targets; managed files
#                     otherwise). User content outside markers is never touched.
#   --help            Show usage
#   --verbose         Debug logging of every decision
#
# Environment:
#   UQE_DEST          Overrides the destination directory (default: current dir)
#
# Design decisions (documented per project policy):
# - Idempotent install: re-running replaces only UQE-managed content, never duplicates.
# - Verification after write: every install checks file existence AND presence of the
#   Prime Directive line before declaring success. No blind "installed!" messages.
# - Fail loudly: any missing source file or failed verification exits non-zero with a
#   specific error. Silent partial success is not allowed.
# =============================================================================

set -euo pipefail

# --- Defaults ----------------------------------------------------------------
TARGET=""                    # resolved by detection if empty ('auto' forces detection)
DRY_RUN=0
UNINSTALL=0
VERBOSE=0
HELP=0
WITH_SHA=0                   # --with-sha: print SHA-256 of every written artifact
CHECKSUM_FILE=".uqe/SHA256SUMS"  # relative to DEST; machine-readable integrity record

# Activation policy for the cursor target. alwaysApply:true burns context in EVERY
# session regardless of task; the router core is short but still not free. Default
# is false (rule loads when relevant/described); set UQE_ALWAYS_APPLY=true to opt in.
ALWAYS_APPLY="${UQE_ALWAYS_APPLY:-false}"

# The exact Prime Directive sentence used as the post-install verification probe.
PRIME_DIRECTIVE="Assume nothing. Verify everything. Use the cheapest sufficient evidence. Do not ship blind. Do not fabricate. Do not over-process trivial work."

# Marker lines for the append-into-existing-file target (claude). Kept as variables
# so install and uninstall cannot drift apart.
MARKER_BEGIN="<!-- BEGIN UQE -->"
MARKER_END="<!-- END UQE -->"

usage() {
  cat <<'EOF'
UQE v3.2 Installer — Universal Quality Engine

USAGE:
  ./install.sh [--target <auto|cursor|claude|codex|gemini|windsurf|generic|manual>]
               [--dest <dir>] [--dry-run] [--uninstall] [--with-sha] [--verbose] [--help]

TARGETS:
  auto       Force fingerprint detection even when defaults exist (same as omitting --target)
  cursor     Writes .cursor/rules/uqe.mdc (front-matter + router core). Default
             alwaysApply: false to avoid burning context every session; set
             UQE_ALWAYS_APPLY=true to opt into unconditional loading.
  claude     Appends a marker-delimited UQE block to CLAUDE.md (creates it if absent);
             user content outside the markers is preserved on update and uninstall
  codex      Same marker-block protocol, applied to AGENTS.md
  gemini     Same marker-block protocol, applied to GEMINI.md
  windsurf   Writes .windsurf/rules/uqe.md with the router core
  generic    Writes .uqe/UQE-INSTRUCTIONS.md (core skill copy) + modules/templates,
             and prints wiring steps for any agent that accepts instruction files
  manual     Prints manual wiring instructions; writes nothing

FLAGS:
  --target <name>   Specify target explicitly ('auto' forces detection)
  --dest <dir>      Destination directory (same as UQE_DEST env var)
  --dry-run         Show what would happen; make no changes
  --uninstall       Remove UQE artifacts from the destination
  --with-sha        Print SHA-256 of each written artifact and write .uqe/SHA256SUMS
  --verbose         Enable debug logging
  --help            Show this help

ENVIRONMENT:
  UQE_DEST=<dir>          Override destination directory (default: current directory)
  UQE_ALWAYS_APPLY=true   Opt in to cursor alwaysApply:true activation

EXAMPLES:
  ./install.sh                          # auto-detect target, install
  ./install.sh --target auto --dry-run  # force detection, preview
  ./install.sh --uninstall
  ./install.sh --target cursor --with-sha
  UQE_DEST=~/myproject ./install.sh --target cursor --verbose
EOF
}

# NOTE: the "2>/dev/null || :" guards are intentional. Under `set -euo pipefail`,
# a broken pipe (e.g. output piped into `head` in CI, which exits early) makes
# printf fail with SIGPIPE and would abort the whole script over a cosmetic
# logging write. Logging must never be fatal, so we suppress stderr for these
# helpers and neutralise their exit status. die() still exits 1 explicitly —
# that is control flow, not an I/O failure.
log()   { printf '[uqe] %s\n' "$*" 2>/dev/null || :; }
vlog()  { if [ "$VERBOSE" -eq 1 ]; then printf '[uqe:debug] %s\n' "$*" >&2 2>/dev/null || :; fi; }
die()   { printf '[uqe][ERROR] %s\n' "$*" >&2 2>/dev/null || :; exit 1; }

# --- Argument parsing --------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      [ $# -ge 2 ] || die "--target requires a value (cursor|claude|codex|gemini|windsurf|generic|manual)"
      TARGET="$2"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --dest)
      [ $# -ge 2 ] || die "--dest requires a directory"
      DEST_ARG="$2"; shift 2 ;;
    --dest=*) DEST_ARG="${1#*=}"; shift ;;
    --dry-run)   DRY_RUN=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --with-sha)  WITH_SHA=1; shift ;;
    --verbose)   VERBOSE=1; shift ;;
    --help|-h)   HELP=1; shift ;;
    *) die "Unknown argument: $1 (see --help)" ;;
  esac
done

if [ "$HELP" -eq 1 ]; then usage; exit 0; fi

# Resolve destination. --dest wins over UQE_DEST, which wins over cwd.
DEST="${DEST_ARG:-${UQE_DEST:-$PWD}}"
vlog "destination: $DEST"
vlog "requested target: ${TARGET:-<auto-detect>}"

# --- Locate source files -----------------------------------------------------
# Sources live next to this script, not in the cwd: resolve the script's own dir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd || pwd)"
SRC_SKILL="$SCRIPT_DIR/SKILL.md"
SRC_MODULES_DIR="$SCRIPT_DIR/modules"
SRC_TEMPLATES_DIR="$SCRIPT_DIR/templates"
SRC_REFERENCES_DIR="$SCRIPT_DIR/references"
SRC_SCHEMA="$SCRIPT_DIR/evidence.schema.json"
SRC_SCRIPTS_DIR="$SCRIPT_DIR/scripts"

CLEANUP_SRC_DIR=""
cleanup_temp_sources() {
  if [ -n "$CLEANUP_SRC_DIR" ] && [ -d "$CLEANUP_SRC_DIR" ]; then
    rm -rf "$CLEANUP_SRC_DIR"
  fi
}
trap cleanup_temp_sources EXIT INT TERM

# Accumulates 'sha  relpath' lines for .uqe/SHA256SUMS when --with-sha is used.
SHA_RECORD=""

record_sha() {
  # $1 = absolute path of a written artifact. Best-effort: if no sha tool exists,
  # say so honestly instead of pretending integrity was recorded.
  local f="$1" sum=""
  [ "$WITH_SHA" -eq 1 ] || return 0
  [ "$DRY_RUN" -eq 1 ] && return 0
  if command -v sha256sum >/dev/null 2>&1; then
    sum=$(sha256sum "$f" 2>/dev/null | awk '{sub(/^\\/, "", $1); print $1}') || :
  elif command -v shasum >/dev/null 2>&1; then
    sum=$(shasum -a 256 "$f" 2>/dev/null | awk '{sub(/^\\/, "", $1); print $1}') || :
  else
    vlog "no sha256 tool available; skipping checksum for $f"
    return 0
  fi
  [ -n "$sum" ] || { vlog "failed to compute sha256 for $f"; return 0; }
  local rel="${f#"$DEST"/}"
  SHA_RECORD+="$sum  $rel"$'\n'
  log "sha256: $sum  $rel"
}

write_sum_file() {
  # Persist accumulated checksums under DEST/.uqe/SHA256SUMS (verification data).
  [ "$WITH_SHA" -eq 1 ] || return 0
  [ "$DRY_RUN" -eq 1 ] && { printf '[uqe:dry-run] write %s\n' "$DEST/$CHECKSUM_FILE"; return 0; }
  [ -z "$SHA_RECORD" ] && { vlog "no checksums recorded (nothing written or no sha tool)"; return 0; }
  mkdir -p "$DEST/.uqe"
  printf '%s' "$SHA_RECORD" > "$DEST/$CHECKSUM_FILE"
  log "wrote $DEST/$CHECKSUM_FILE ($(printf '%s' "$SHA_RECORD" | grep -c . ) entries)"
}

validate_sources() {
  if [ ! -f "$SRC_SKILL" ]; then
    vlog "Source files not found at $SCRIPT_DIR; attempting remote bootstrap from GitHub..."
    CLEANUP_SRC_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'uqe-install')"
    local dl_ok=0
    local repo_tar="https://github.com/dollan9/uqe/archive/refs/heads/main.tar.gz"

    if command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
      log "Downloading UQE source archive via curl..."
      if curl -fsSL "$repo_tar" | tar -xz -C "$CLEANUP_SRC_DIR" 2>/dev/null; then
        dl_ok=1
      fi
    elif command -v wget >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
      log "Downloading UQE source archive via wget..."
      if wget -qO- "$repo_tar" | tar -xz -C "$CLEANUP_SRC_DIR" 2>/dev/null; then
        dl_ok=1
      fi
    elif command -v git >/dev/null 2>&1; then
      log "Cloning UQE repository via git..."
      if git clone --depth=1 https://github.com/dollan9/uqe.git "$CLEANUP_SRC_DIR/dollan-main" >/dev/null 2>&1; then
        dl_ok=1
      fi
    fi

    if [ "$dl_ok" -eq 1 ]; then
      local extracted
      extracted="$(find "$CLEANUP_SRC_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
      if [ -n "$extracted" ] && [ -f "$extracted/SKILL.md" ]; then
        SCRIPT_DIR="$extracted"
        SRC_SKILL="$SCRIPT_DIR/SKILL.md"
        SRC_MODULES_DIR="$SCRIPT_DIR/modules"
        SRC_TEMPLATES_DIR="$SCRIPT_DIR/templates"
        SRC_REFERENCES_DIR="$SCRIPT_DIR/references"
        SRC_SCHEMA="$SCRIPT_DIR/evidence.schema.json"
        SRC_SCRIPTS_DIR="$SCRIPT_DIR/scripts"
        vlog "Successfully resolved remote source directory: $SCRIPT_DIR"
      fi
    fi
  fi

  # Never start an install we cannot finish. Check every required input first.
  [ -f "$SRC_SKILL" ]        || die "Source file missing: $SRC_SKILL (run installer from the UQE repo root checkout or check network connection)"
  [ -d "$SRC_MODULES_DIR" ]  || die "Source directory missing: $SRC_MODULES_DIR"
  [ -d "$SRC_TEMPLATES_DIR" ]|| die "Source directory missing: $SRC_TEMPLATES_DIR"
  # Prime Directive sanity: refuse to install a corrupted skill file.
  grep -qF "$PRIME_DIRECTIVE" "$SRC_SKILL" \
    || die "SKILL.md does not contain the Prime Directive verbatim — refusing to install a corrupt source."
  vlog "source validation passed ($SRC_SKILL, $(find "$SRC_MODULES_DIR" -name '*.md' | wc -l | tr -d ' ') modules, $(find "$SRC_TEMPLATES_DIR" -name '*.md' | wc -l | tr -d ' ') templates)"
}

# --- Target auto-detection ---------------------------------------------------
detect_target() {
  # Heuristic order: explicit project fingerprints, most-specific first.
  if [ -e "$DEST/.cursor" ]; then echo "cursor"; return; fi
  if [ -e "$DEST/.windsurf" ]; then echo "windsurf"; return; fi
  if [ -f "$DEST/CLAUDE.md" ]; then echo "claude"; return; fi
  if [ -f "$DEST/GEMINI.md" ]; then echo "gemini"; return; fi
  if [ -f "$DEST/AGENTS.md" ]; then echo "codex"; return; fi
  # No fingerprint found: do not guess silently between vendor conventions.
  echo "generic"
}

case "$TARGET" in
  ""|auto) TARGET="$(detect_target)"; log "Auto-detected target: $TARGET" ;;
  generic|cursor|claude|codex|gemini|windsurf|manual) : ;;
  *) die "Invalid --target '$TARGET' (must be auto, cursor, claude, codex, gemini, windsurf, generic, or manual)" ;;
esac
vlog "effective target: $TARGET"

# --- Helpers -----------------------------------------------------------------
run() {
  # Central action gate: dry-run prints instead of executing. Executes argv directly
  # (no eval), so arguments beginning with '-' are passed positionally and safely.
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[uqe:dry-run]%s\n' " $*"
  else
    vlog "exec: $*"
    "$@"
  fi
}

copy_support_files() {
  # Every target benefits from modules/ + templates/ + references/ + scripts/ +
  # evidence.schema.json living beside the installed brain under .uqe/ inside the
  # destination (the canonical runtime layout).
  local base="$1" f rel
  run mkdir -p "$base/.uqe/modules" "$base/.uqe/templates" "$base/.uqe/references" "$base/.uqe/scripts"
  for f in "$SRC_MODULES_DIR"/*.md; do
    rel=".uqe/modules/$(basename "$f")"
    run cp -f "$f" "$base/$rel"
    record_sha "$base/$rel"
  done
  for f in "$SRC_TEMPLATES_DIR"/*.md; do
    rel=".uqe/templates/$(basename "$f")"
    run cp -f "$f" "$base/$rel"
    record_sha "$base/$rel"
  done
  if [ -d "$SRC_REFERENCES_DIR" ]; then
    for f in "$SRC_REFERENCES_DIR"/*.md; do
      rel=".uqe/references/$(basename "$f")"
      run cp -f "$f" "$base/$rel"
      record_sha "$base/$rel"
    done
  fi
  if [ -f "$SRC_SCHEMA" ]; then
    run cp -f "$SRC_SCHEMA" "$base/.uqe/evidence.schema.json"
    record_sha "$base/.uqe/evidence.schema.json"
  fi
  if [ -d "$SRC_SCRIPTS_DIR" ]; then
    for f in "$SRC_SCRIPTS_DIR"/*; do
      [ -f "$f" ] || continue
      rel=".uqe/scripts/$(basename "$f")"
      run cp -f "$f" "$base/$rel"
      run chmod +x "$base/$rel" 2>/dev/null || true
      record_sha "$base/$rel"
    done
  fi
  # Mirror the brain itself into the runtime dir so uninstall can identify
  # UQE-managed copies, and agents that read .uqe/ directly have it available.
  run cp -f "$SRC_SKILL" "$base/.uqe/SKILL.md"
  record_sha "$base/.uqe/SKILL.md"
  # Seed preferences/lessons from templates only if absent (never clobber user data).
  if [ ! -f "$base/.uqe/preferences.md" ]; then
    run cp "$SRC_TEMPLATES_DIR/preferences-template.md" "$base/.uqe/preferences.md"
  else
    vlog "keeping existing preferences.md"
  fi
  if [ ! -f "$base/.uqe/lessons.md" ]; then
    run cp "$SRC_TEMPLATES_DIR/lessons-template.md" "$base/.uqe/lessons.md"
  else
    vlog "keeping existing lessons.md"
  fi
}

verify_file_contains() {
  # Post-write proof: file exists AND carries the Prime Directive. Used for every
  # written artifact. In dry-run mode there is nothing to verify (nothing was written).
  local f="$1"
  [ "$DRY_RUN" -eq 1 ] && { vlog "dry-run: skipping verification of $f"; return 0; }
  [ -f "$f" ] || die "Verification failed: '$f' does not exist after install."
  grep -qF "$PRIME_DIRECTIVE" "$f" \
    || die "Verification failed: '$f' exists but does not contain the Prime Directive."
  log "verified: $f (exists, Prime Directive present)"
}

# --- Install paths per target ------------------------------------------------
install_cursor() {
  local out="$DEST/.cursor/rules/uqe.mdc"
  run mkdir -p "$DEST/.cursor/rules"
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[uqe:dry-run] write %s (front-matter alwaysApply: %s + router core)\n' "$out" "$ALWAYS_APPLY"
  else
    # .mdc format: YAML front-matter controls activation. Default false — an
    # always-on rule burns context in every session; opt in via UQE_ALWAYS_APPLY=true.
    {
      printf '%s\n' '---'
      printf 'description: UQE v3.2 — Universal Quality Engine router core (load when doing non-trivial work)\n'
      printf 'globs:\n'
      printf 'alwaysApply: %s\n' "$ALWAYS_APPLY"
      printf '%s\n\n' '---'
      cat "$SRC_SKILL"
    } > "$out"
  fi
  verify_file_contains "$out"
  record_sha "$out"
  copy_support_files "$DEST"
}

install_marker_block() {
  # Marker-block protocol for append-into-existing-file targets (claude/codex/gemini).
  # $1 = output file. No EXIT trap: the temp file is consumed by mv (success path)
  # or removed explicitly below.
  local out="$1"
  local tmp
  tmp="$(mktemp)"

  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[uqe:dry-run] upsert marker block (%s ... %s) in %s with full SKILL.md\n' \
      "$MARKER_BEGIN" "$MARKER_END" "$out"
    rm -f "$tmp"
    copy_support_files "$DEST"
    return 0
  fi

  # Idempotent upsert: strip any pre-existing UQE block first, then append a fresh one.
  # Everything outside the markers is byte-preserved — user content is sacred.
  if [ -f "$out" ]; then
    awk -v b="$MARKER_BEGIN" -v e="$MARKER_END" '
      index($0, b) { inside=1; next }
      index($0, e) { inside=0; next }
      !inside { print }
    ' "$out" > "$tmp"
    # Trim trailing blank lines so we don't grow whitespace each install.
    while [ -s "$tmp" ] && [ -z "$(tail -c 200 "$tmp" | tr -d '[:space:]')" ]; do
      sed -i '$ d' "$tmp" 2>/dev/null || truncate -s -1 "$tmp"
    done
    mv "$tmp" "$out"
    printf '\n\n' >> "$out"
  else
    printf '# Project Instructions\n\n' > "$out"
  fi

  {
    printf '%s\n' "$MARKER_BEGIN"
    printf '<!-- Managed by UQE install.sh. Do not edit inside these markers; edits will be overwritten on update. Content outside the markers is never modified. -->\n\n'
    cat "$SRC_SKILL"
    printf '\n%s\n' "$MARKER_END"
  } >> "$out"

  verify_file_contains "$out"
  record_sha "$out"
  copy_support_files "$DEST"
}

install_claude() { install_marker_block "$DEST/CLAUDE.md"; }
install_codex()  { install_marker_block "$DEST/AGENTS.md"; }
install_gemini() { install_marker_block "$DEST/GEMINI.md"; }

install_windsurf() {
  local out="$DEST/.windsurf/rules/uqe.md"
  run mkdir -p "$DEST/.windsurf/rules"
  run cp -f "$SRC_SKILL" "$out"
  verify_file_contains "$out"
  record_sha "$out"
  copy_support_files "$DEST"
}

install_generic() {
  # NOTE: `|| :` guards the cat against SIGPIPE (exit 141) when this script's
  # stdout is piped to a consumer that exits early (e.g. `install.sh | head -3`
  # in CI). Under `set -euo pipefail` an unguarded cat would abort the install
  # after all files were already written, turning a cosmetic truncation into a
  # spurious job failure. The instructions are informational output only.
  cat <<EOF || :
UQE v3.2 — MANUAL WIRING INSTRUCTIONS (generic target)

No supported rule-file convention was detected, so nothing was written automatically.
To wire UQE into any agent that accepts instruction files:

1. Copy the brain (router core) and ALL support dirs:
     cp '$SRC_SKILL' <your-agent-rules-file>
     mkdir -p <workspace>/.uqe
     cp -r '$SRC_MODULES_DIR' <workspace>/.uqe/modules
     cp -r '$SRC_TEMPLATES_DIR' <workspace>/.uqe/templates
     cp -r '$SRC_REFERENCES_DIR' <workspace>/.uqe/references
     cp -r '$SRC_SCRIPTS_DIR' <workspace>/.uqe/scripts
     cp '$SRC_SCHEMA' <workspace>/.uqe/evidence.schema.json
   Or paste the router core's contents into your agent's system/instruction prompt field.

2. Ensure the agent reads '.uqe/preferences.md' and '.uqe/lessons.md' at session
   start (memory policy in references/core-behavior.md Section 10). Seed them from
   the templates if they do not exist yet. Enforce caps with:
     python3 .uqe/scripts/prune_memory.py check .uqe

3. Use the verification scripts as real evidence producers (no evidence, no claim):
     bash .uqe/scripts/verify_web.sh <url>        # playwright shots 1440/768/375 + axe
     bash .uqe/scripts/verify_video.sh <file>     # keyframes + loudness
     python3 .uqe/scripts/verify_blender.py       # geometry audit (run inside Blender)
     python3 .uqe/scripts/verify_citations.py report.json
   Fill an evidence JSON per '.uqe/evidence.schema.json' and validate it:
     python3 .uqe/scripts/validate_evidence.py report.json

4. Verify activation yourself (do not trust this message — check):
     grep -F "$PRIME_DIRECTIVE" <your-agent-rules-file>
   If that prints the line, the skill is installed. Then ask the agent to recite
   Section 0. If it cannot, it is not loading the file.

Supported targets for automatic installation: cursor, claude, codex, gemini, windsurf.
EOF
  log "generic target: no files written by design (manual wiring above)."
}

install_manual() {
  # Explicit manual target: print wiring steps, write nothing (same contract as the
  # no-fingerprint generic fallback, but requested by name).
  install_generic
}

# --- Uninstall paths ----------------------------------------------------------
uninstall_cursor() {
  local out="$DEST/.cursor/rules/uqe.mdc"
  if [ -f "$out" ] && grep -qF "$PRIME_DIRECTIVE" "$out"; then
    run rm -f "$out"
    log "removed $out"
  else
    log "nothing to remove at $out (absent or not UQE-managed)"
  fi
  uninstall_support_files
}

uninstall_marker_block() {
  # Strip ONLY the UQE marker block from $1; everything else is byte-preserved.
  local out="$1"
  if [ ! -f "$out" ]; then
    log "no $out present; nothing to remove."
    uninstall_support_files
    return 0
  fi
  if ! grep -qF "$MARKER_BEGIN" "$out"; then
    log "$out has no UQE marker block; leaving user file untouched."
    uninstall_support_files
    return 0
  fi
  local tmp
  tmp="$(mktemp)"
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[uqe:dry-run] strip marker block (%s ... %s) from %s, preserve all other content\n' \
      "$MARKER_BEGIN" "$MARKER_END" "$out"
    rm -f "$tmp"
  else
    awk -v b="$MARKER_BEGIN" -v e="$MARKER_END" '
      index($0, b) { inside=1; next }
      index($0, e) { inside=0; next }
      !inside { print }
    ' "$out" > "$tmp"
    mv "$tmp" "$out"
    log "stripped UQE marker block from $out — user content outside markers preserved."
  fi
  uninstall_support_files
}

uninstall_claude() { uninstall_marker_block "$DEST/CLAUDE.md"; }
uninstall_codex()  { uninstall_marker_block "$DEST/AGENTS.md"; }
uninstall_gemini() { uninstall_marker_block "$DEST/GEMINI.md"; }

uninstall_windsurf() {
  local out="$DEST/.windsurf/rules/uqe.md"
  if [ -f "$out" ] && grep -qF "$PRIME_DIRECTIVE" "$out"; then
    run rm -f "$out"
    log "removed $out"
  else
    log "nothing to remove at $out (absent or not UQE-managed)"
  fi
  uninstall_support_files
}

uninstall_support_files() {
  # Remove the runtime copy only if it is UQE-managed (Prime Directive in the
  # mirrored brain file) — never delete a user-modified .uqe directory wholesale.
  local brain="$DEST/.uqe/SKILL.md"
  if [ -f "$brain" ] && grep -qF "$PRIME_DIRECTIVE" "$brain"; then
    run rm -rf "$DEST/.uqe/modules" "$DEST/.uqe/templates" "$DEST/.uqe/references" \
      "$DEST/.uqe/scripts" "$DEST/.uqe/evidence.schema.json" "$DEST/$CHECKSUM_FILE" "$brain"
    log "removed UQE-managed runtime files under $DEST/.uqe (preferences.md and lessons.md kept — they are user data)."
  else
    log "no UQE-managed runtime copy found under $DEST/.uqe; user files left untouched."
  fi
}

# --- Main ---------------------------------------------------------------------
validate_sources

MODE="INSTALL"
[ "$UNINSTALL" -eq 1 ] && MODE="UNINSTALL"
log "mode: $MODE | target: $TARGET | destination: $DEST | dry-run: $([ "$DRY_RUN" -eq 1 ] && echo yes || echo no)"

if [ "$UNINSTALL" -eq 1 ]; then
  case "$TARGET" in
    cursor)   uninstall_cursor ;;
    claude)   uninstall_claude ;;
    codex)    uninstall_codex ;;
    gemini)   uninstall_gemini ;;
    windsurf) uninstall_windsurf ;;
    generic|manual)
      cat <<EOF || :   # `|| :` = SIGPIPE guard, see install_generic() note
Generic/manual target uninstall: locate wherever you manually placed the UQE files
(SKILL.md copy, .uqe/modules, .uqe/templates) and remove them. Nothing was
installed automatically, so nothing can be removed automatically.
EOF
      ;;
  esac
else
  case "$TARGET" in
    cursor)   install_cursor ;;
    claude)   install_claude ;;
    codex)    install_codex ;;
    gemini)   install_gemini ;;
    windsurf) install_windsurf ;;
    generic)  install_generic ;;
    manual)   install_manual ;;
  esac
fi

# Integrity record (only when --with-sha requested; no-op otherwise).
if [ "$UNINSTALL" -eq 0 ]; then
  write_sum_file
fi

# Final honest summary. In dry-run we say exactly that nothing was verified because
# nothing was written — no fake success language.
if [ "$DRY_RUN" -eq 1 ]; then
  log "DRY RUN complete. No changes made; no verification performed (nothing was written)."
elif [ "$TARGET" = "generic" ] && [ "$UNINSTALL" -eq 0 ]; then
  log "Manual-wiring instructions printed above. Installation is NOT complete until YOU follow step 4 and see the Prime Directive echoed back."
else
  log "$MODE complete and VERIFIED by post-write checks listed above."
fi
exit 0
