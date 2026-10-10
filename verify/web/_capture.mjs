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
