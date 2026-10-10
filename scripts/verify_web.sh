#!/usr/bin/env bash
# verify_web.sh — UQE web verification: screenshots at 1440/768/375 + axe audit.
# Produces real artifacts under $OUT_DIR and prints an evidence JSON skeleton to
# stdout that you fill in with what you OBSERVED (SEEN standard), then validate:
#   python3 scripts/validate_evidence.py report.json
#
# Usage: ./scripts/verify_web.sh <url> [out_dir]
# Requires: npx (Node 18+) for @playwright/test + @axe-core/playwright, OR
#           playwright CLI already installed. Degrades honestly if absent.
set -euo pipefail

URL="${1:?usage: verify_web.sh <url> [out_dir]}"
OUT_DIR="${2:-verify/web}"
WIDTHS=(1440 768 375)
mkdir -p "$OUT_DIR"

if ! command -v npx >/dev/null 2>&1; then
  echo "[verify_web][UNVERIFIED] npx/node not available — no screenshots or axe audit produced." >&2
  echo "[verify_web] Manual equivalent: open $URL, capture at ${WIDTHS[*]}px, run axe DevTools. Mark claims UNVERIFIED until artifacts exist." >&2
  exit 2
fi

# Inline Playwright script (chromium only; --no-save keeps CI fast & deterministic).
cat > "$OUT_DIR/_capture.mjs" <<'JS'
import { chromium } from '@playwright/test';
const [url, outDir, ...widths] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage();
for (const w of widths) {
  await page.setViewportSize({ width: Number(w), height: 900 });
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.screenshot({ path: `${outDir}/shot-${w}.png`, fullPage: true });
  console.log(`captured shot-${w}.png`);
}
// axe accessibility audit via injected core
await page.setViewportSize({ width: 1440, height: 900 });
await page.addScriptTag({ url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js' });
const results = await page.evaluate(async () => await window.axe.run());
const fs = await import('node:fs');
fs.writeFileSync(`${outDir}/axe-report.json`, JSON.stringify(results, null, 2));
console.log(`axe: ${results.violations.length} violation(s)`);
for (const v of results.violations.slice(0, 20)) {
  console.log(`  [${v.impact}] ${v.id}: ${v.nodes.length} node(s) — ${v.help}`);
}
await browser.close();
JS

echo "[verify_web] installing playwright deps (one-time)..." >&2
cd "$OUT_DIR"
[ -f package.json ] || npm init -y >/dev/null 2>&1
npx --yes playwright@latest install chromium --with-deps >/dev/null 2>&1 || \
  npx --yes playwright@latest install chromium >/dev/null 2>&1 || true
npm install --no-save --silent @playwright/test@latest >/dev/null 2>&1 || true
cd - >/dev/null

if node "$OUT_DIR/_capture.mjs" "$URL" "$OUT_DIR" "${WIDTHS[@]}" 2>&1 | tee "$OUT_DIR/capture.log"; then
  echo "[verify_web] ARTIFACTS:"
  for w in "${WIDTHS[@]}"; do [ -f "$OUT_DIR/shot-$w.png" ] && echo "  $OUT_DIR/shot-$w.png"; done
  [ -f "$OUT_DIR/axe-report.json" ] && echo "  $OUT_DIR/axe-report.json"
  echo "[verify_web] NEXT: VIEW every screenshot (do not skip), read axe-report violations, write the evidence JSON entries with your observations, validate with scripts/validate_evidence.py."
else
  echo "[verify_web][UNVERIFIED] capture failed (browser/network). Inspect $OUT_DIR/capture.log; mark affected claims UNVERIFIED." >&2
  exit 1
fi
