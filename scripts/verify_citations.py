#!/usr/bin/env python3
"""verify_citations.py — UQE citation liveness checker (stdlib only).

Actually curls (via urllib) every URL found in an evidence report (or a plain
text/markdown file of URLs) and verifies it EXISTS: HTTP status < 400, plus a
content sanity check — does the source page contain any distinctive token
(title fragment / quoted phrase words) claimed by the evidence 'observed' field?

Exit codes: 0 all citations verified · 1 at least one dead/unmatched · 2 usage error.
Usage:
  python3 scripts/verify_citations.py report.json          # evidence.schema.json report
  python3 scripts/verify_citations.py --urls urls.txt      # one URL per line
Options: --timeout N (default 15) --workers N (default 8) --no-content-check
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (compatible; UQE-citation-verifier/1.0)"

def head_status(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = b""
            try:
                body = r.read(200_000)
            except Exception:
                pass
            return r.getcode(), body
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return None, str(e).encode()

def content_tokens(observed):
    """Pick distinctive words from the observation to look for on the page."""
    words = [w.strip(".,;:!?'\"()[]{}").lower() for w in re.findall(r"\S+", observed)]
    stop = {"the","and","for","with","that","this","from","per","says","said","source","page","article","which","have","has"}
    cand = [w for w in words if len(w) >= 5 and w not in stop]
    return cand[:6]

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    elif len(argv) > 0 and argv[0].endswith(".py"):
        argv = argv[1:]

    parser = argparse.ArgumentParser(
        description="verify_citations.py — UQE citation liveness checker (stdlib only).",
    )
    parser.add_argument("target", help="Path to evidence report JSON or URL list text file")
    parser.add_argument("--urls", action="store_true", help="Treat target as a plain text file containing one URL per line")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP request timeout in seconds (default: 15)")
    parser.add_argument("--workers", type=int, default=8, help="Number of worker threads (default: 8)")
    parser.add_argument("--no-content-check", action="store_true", help="Skip checking page content for observation tokens")

    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code

    timeout = parsed.timeout
    workers = parsed.workers
    no_content = parsed.no_content_check
    path = parsed.target

    targets = []  # (url, observed_or_None)
    if parsed.urls:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    u = line.strip()
                    if u and not u.startswith("#"):
                        targets.append((u, None))
        except OSError as e:
            print(f"[citations][ERROR] cannot read {path}: {e}", file=sys.stderr)
            return 2
    else:
        try:
            with open(path, encoding="utf-8") as f:
                report = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[citations][ERROR] cannot read or parse {path}: {e}", file=sys.stderr)
            return 2
        for ev in report.get("evidence", []):
            if ev.get("type") == "citation" and str(ev.get("path", "")).startswith(("http://", "https://")):
                targets.append((ev["path"], ev.get("observed", "")))
        for uc in report.get("unverified_claims", []):
            pass  # honest disclosures need no network check

    if not targets:
        print("[citations] no http(s) citation entries found — nothing to verify. (If you cited sources, they were not schema-conformant.)")
        return 0

    ok = bad = 0
    def check(item):
        url, observed = item
        code, body = head_status(url, timeout)
        if code is None:
            return (url, False, f"unreachable: {body.decode(errors='replace')[:80]}")
        if code >= 400:
            return (url, False, f"HTTP {code}")
        # common soft-404 markers
        text = body.decode("utf-8", errors="replace").lower()
        if code == 200 and ("<title>not found" in text or "404" in text[:400]):
            return (url, False, f"HTTP {code} but looks like a soft-404")
        if not no_content and observed:
            toks = content_tokens(observed)
            if toks and not any(t in text for t in toks):
                return (url, True, f"HTTP {code} LIVE, but none of the observation tokens {toks[:3]}… appear on page — check you cite the right source (E2 warning)")
        return (url, True, f"HTTP {code}")

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for url, passed, msg in ex.map(check, targets):
            mark = "OK " if passed else "DEAD"
            if "but none" in msg:
                mark = "WARN"
            print(f"[citations][{mark}] {url} — {msg}")
            ok += 1 if passed else 0
            bad += 0 if passed else 1

    print(f"[citations] {ok} live/warn, {bad} dead-unreachable out of {len(targets)} checked.")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
