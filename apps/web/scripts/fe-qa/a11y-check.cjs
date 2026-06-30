/* Accessibility audit (axe-core via Playwright). Loads key public pages and
 * fails on serious/critical violations. Run against a live web stack:
 * BASE=… node scripts/fe-qa/a11y-check.cjs */
const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const axePath = require.resolve("axe-core");

const BASE = process.env.BASE || "http://127.0.0.1:3000";
const EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PAGES = ["/", "/en", "/login", "/signup", "/pricing", "/features", "/docs", "/contact"];
const FAIL = new Set(["serious", "critical"]);

(async () => {
  const browser = await chromium.launch({ executablePath: EXE });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  let failures = 0;
  for (const path of PAGES) {
    const page = await ctx.newPage();
    await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 20000 });
    await page.addScriptTag({ path: axePath });
    const { violations } = await page.evaluate(async () =>
      await window.axe.run(document, { resultTypes: ["violations"] }),
    );
    const serious = violations.filter((v) => FAIL.has(v.impact));
    if (serious.length) {
      for (const v of serious) {
        console.error(`✗ ${path} [${v.impact}] ${v.id} — ${v.help} (${v.nodes.length} node(s))`);
        failures++;
      }
    } else {
      console.log(`✓ ${path} — no serious/critical a11y violations`);
    }
    await page.close();
  }
  await browser.close();
  console.log(`\na11y-check: ${failures} serious/critical violation(s).`);
  process.exit(failures > 0 ? 1 : 0);
})().catch((e) => { console.error("a11y-check error:", e.message); process.exit(2); });
