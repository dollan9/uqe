#!/usr/bin/env python3
"""prune_memory.py — UQE memory hygiene enforcer (SKILL.md references/core-behavior.md §10).

Caps that prevent context death:
  * preferences.md : <= MAX_PREF_TOKENS (default 500, ~4 chars/token heuristic)
  * lessons.md     : <= MAX_LESSONS entries (default 20); entries carry a TTL
                     date in the entry text; expired entries are dropped.

Modes:
  check   : report violations, change nothing            (exit 1 on violation)
  prune   : enforce caps — drop oldest lessons beyond cap, drop expired by TTL,
            trim preferences to cap keeping newest lines, write .bak first
  report  : sizes only (exit 0)

Usage: python3 scripts/prune_memory.py [check|prune|report] [.uqe dir = .uqe]
Env overrides: UQE_MAX_PREF_TOKENS, UQE_MAX_LESSONS, UQE_LESSON_TTL_DAYS (default 180)
"""
import os
import re
import sys
from datetime import date, timedelta

MAX_PREF_TOKENS = int(os.environ.get("UQE_MAX_PREF_TOKENS", "500"))
MAX_LESSONS = int(os.environ.get("UQE_MAX_LESSONS", "20"))
TTL_DAYS = int(os.environ.get("UQE_LESSON_TTL_DAYS", "180"))
CHARS_PER_TOKEN = 4  # rough heuristic; conservative for English prose

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

def tokens(text):
    return len(text) // CHARS_PER_TOKEN

def lesson_entries(lines):
    """A lesson entry starts with '- ' at column 0 and continues until next entry/blank-header."""
    out = []  # list of (start_idx, end_idx_exclusive, text, date_or_None)
    idxs = [i for i, l in enumerate(lines) if l.startswith("- ")]
    for k, i in enumerate(idxs):
        j = idxs[k + 1] if k + 1 < len(idxs) else len(lines)
        block = "\n".join(lines[i:j])
        m = DATE_RE.search(block)
        out.append((i, j, block, m.group(1) if m else None))
    return out

def run(mode, uqe_dir):
    pref_path = os.path.join(uqe_dir, "preferences.md")
    less_path = os.path.join(uqe_dir, "lessons.md")
    problems = []

    # --- preferences ---------------------------------------------------------
    if os.path.exists(pref_path):
        with open(pref_path, encoding="utf-8") as f:
            ptext = f.read()
        pt = tokens(ptext)
        print(f"[memory] preferences.md: {pt} est-tokens (cap {MAX_PREF_TOKENS})")
        if pt > MAX_PREF_TOKENS:
            problems.append("preferences over cap")
            if mode == "prune":
                lines = ptext.splitlines()
                header_lines = []
                body_lines = []
                in_header = True
                for line in lines:
                    if in_header and (line.startswith("## ") or (line.startswith("- ") and not header_lines)):
                        in_header = False
                    if in_header:
                        header_lines.append(line)
                    else:
                        body_lines.append(line)

                header_tokens = tokens("\n".join(header_lines) + "\n") if header_lines else 0
                remaining_budget = max(0, MAX_PREF_TOKENS - header_tokens)

                kept_body = []
                total_body = 0
                for line in reversed(body_lines):  # keep newest (bottom) first
                    t = tokens(line + "\n")
                    if total_body + t > remaining_budget and kept_body:
                        break
                    kept_body.append(line)
                    total_body += t
                kept_body = list(reversed(kept_body))

                final_lines = header_lines + kept_body
                total = header_tokens + total_body
                backup = pref_path + ".bak"
                os.replace(pref_path, backup)
                with open(pref_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(final_lines) + "\n")
                print(f"[memory] pruned preferences.md to {total} est-tokens; previous file at {backup}")

    # --- lessons --------------------------------------------------------------
    if os.path.exists(less_path):
        with open(less_path, encoding="utf-8") as f:
            ltext = f.read()
        lines = ltext.splitlines()
        entries = lesson_entries(lines)
        today = date.today()
        cutoff = today - timedelta(days=TTL_DAYS)
        expired = [e for e in entries if e[3] and date.fromisoformat(e[3]) < cutoff]
        undated = [e for e in entries if not e[3]]
        print(f"[memory] lessons.md: {len(entries)} entries (cap {MAX_LESSONS}), "
              f"{len(expired)} expired (TTL {TTL_DAYS}d), {len(undated)} undated")
        if len(entries) > MAX_LESSONS or expired:
            problems.append("lessons over cap or expired entries present")
            if mode == "prune":
                keep_blocks = []
                header = [l for l in lines[: (entries[0][0] if entries else len(lines))] if not l.startswith("- ")]
                for i, j, block, d in entries:
                    if d and date.fromisoformat(d) < cutoff:
                        continue
                    keep_blocks.append(block.rstrip())
                keep_blocks = keep_blocks[-MAX_LESSONS:]  # newest N
                backup = less_path + ".bak"
                os.replace(less_path, backup)
                with open(less_path, "w", encoding="utf-8") as f:
                    if header:
                        f.write("\n".join(header).rstrip() + "\n\n")
                    f.write("\n".join(keep_blocks) + "\n")
                print(f"[memory] pruned lessons.md to {len(keep_blocks)} entries; previous file at {backup}")
        if undated and mode != "report":
            print(f"[memory] NOTE: {len(undated)} undated lesson(s) — add '(added YYYY-MM-DD)' so TTL can work.")

    if not os.path.exists(pref_path) and not os.path.exists(less_path):
        print(f"[memory] no memory files under {uqe_dir} — nothing to do.")
        return 0

    if problems and mode == "check":
        print(f"[memory][VIOLATION] {'; '.join(problems)}. Run with 'prune' to enforce caps.")
        return 1
    if not problems:
        print("[memory] within caps.")
    return 0

def main(argv):
    mode = argv[1] if len(argv) > 1 else "check"
    if mode not in ("check", "prune", "report"):
        print(__doc__)
        return 2
    uqe_dir = argv[2] if len(argv) > 2 else ".uqe"
    if not os.path.isdir(uqe_dir):
        print(f"[memory] directory not found: {uqe_dir}")
        return 2
    return run(mode, uqe_dir)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
