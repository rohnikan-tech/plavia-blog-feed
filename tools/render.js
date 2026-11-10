// Offline SVG/HTML -> PNG renderer: local file:// pages only, every http(s) request aborted.
// Needs Playwright and a Chromium build; both locations come from the environment, nothing is hard-coded:
//   NODE_PATH      folder that holds node_modules/playwright
//   CHROMIUM_PATH  the Chromium executable Playwright should launch
// Usage: node tools/render.js <in.svg|in.html> <out.png> <width> <height> [fullPage]
//   e.g. node tools/render.js posts/2026/11/<slug>/cover.svg posts/2026/11/<slug>/cover.png 1200 630
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [input, output, w, h, full] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, headless: true });
  const context = await browser.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  await context.route(/^https?:/, route => route.abort());
  const page = await context.newPage();
  await page.goto('file:///' + path.resolve(input).replace(/\\/g, '/'));
  await page.waitForTimeout(300);
  await page.screenshot({ path: output, fullPage: full === '1' });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
