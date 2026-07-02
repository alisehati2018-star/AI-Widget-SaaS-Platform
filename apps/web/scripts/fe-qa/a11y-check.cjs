/* Accessibility audit (axe-core via Playwright). Loads key public pages AND
 * the admin surface (signed in) and fails on serious/critical violations.
 * Run against a live web+backend stack:
 * BASE=… ADMIN_TOKEN=… node scripts/fe-qa/a11y-check.cjs */
const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const axePath = require.resolve("axe-core");

const BASE = process.env.BASE || "http://127.0.0.1:3000";
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || "dev-admin-token";
const EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PAGES = ["/", "/en", "/login", "/signup", "/pricing", "/features", "/docs", "/contact"];
const ADMIN_PAGES = ["/admin", "/admin/tenants", "/admin/contact", "/admin/operators",
  "/admin/elasticsearch", "/admin/queue", "/admin/flags", "/admin/health"];
const FAIL = new Set(["serious", "critical"]);

async function audit(ctx, paths, label) {
  let failures = 0;
  for (const path of paths) {
    const page = await ctx.newPage();
    await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 20000 });
    await page.addScriptTag({ path: axePath });
    const { violations } = await page.evaluate(async () =>
      await window.axe.run(document, { resultTypes: ["violations"] }),
    );
    const serious = violations.filter((v) => FAIL.has(v.impact));
    if (serious.length) {
      for (const v of serious) {
        console.error(`✗ ${label} ${path} [${v.impact}] ${v.id} — ${v.help} (${v.nodes.length} node(s))`);
        failures++;
      }
    } else {
      console.log(`✓ ${label} ${path} — no serious/critical a11y violations`);
    }
    await page.close();
  }
  return failures;
}

(async () => {
  const browser = await chromium.launch({ executablePath: EXE });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  let failures = 0;

  failures += await audit(ctx, PAGES, "public");

  // Admin surface: bootstrap + login (cookie lands on the context), then audit.
  const stamp = Date.now();
  const adminEmail = `admin.a11y.${stamp}@vitrin.ai`;
  const adminPass = "Adm1n!Str0ng#2026";
  await ctx.request.post(`${BASE}/api/admin/auth/bootstrap`, {
    headers: { "x-admin-token": ADMIN_TOKEN, "content-type": "application/json" },
    data: { email: adminEmail, password: adminPass, full_name: "A11y Admin" },
  });
  const login = await ctx.request.post(`${BASE}/api/admin/auth/login`, {
    headers: { "content-type": "application/json" },
    data: { email: adminEmail, password: adminPass },
  });
  if (!login.ok()) {
    console.error(`✗ admin login failed (${login.status()}) — admin a11y skipped`);
    failures++;
  } else {
    failures += await audit(ctx, ADMIN_PAGES, "admin");
  }

  await browser.close();
  console.log(`\na11y-check: ${failures} serious/critical violation(s).`);
  process.exit(failures > 0 ? 1 : 0);
})().catch((e) => { console.error("a11y-check error:", e.message); process.exit(2); });
