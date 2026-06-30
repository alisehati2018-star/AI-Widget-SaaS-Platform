/* Functional E2E (smoke): drives real admin workflows through the UI to prove
 * mutations update the UI. Currently covers the Phase 10 additions: admin
 * create-tenant (form → success key → row appears) and tenant export (button).
 * Run against a live web+backend stack. */
const { chromium } = require("/opt/node22/lib/node_modules/playwright");

const BASE = process.env.BASE || "http://127.0.0.1:3000";
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || "dev-admin-token";
const EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
let failures = 0;
const ok = (c, m) => { if (!c) { console.error(`✗ ${m}`); failures++; } else console.log(`✓ ${m}`); };

(async () => {
  const browser = await chromium.launch({ executablePath: EXE });
  const ctx = await browser.newContext();
  const stamp = Date.now();
  const adminEmail = `admin.fc.${stamp}@vitrin.ai`;
  const adminPass = "Adm1n!Str0ng#2026";
  await ctx.request.post(`${BASE}/api/auth/bootstrap-admin`, {
    headers: { "x-admin-token": ADMIN_TOKEN, "content-type": "application/json" },
    data: { email: adminEmail, password: adminPass, full_name: "FC Admin" },
  });
  const login = await ctx.request.post(`${BASE}/api/auth/login`, {
    headers: { "content-type": "application/json" },
    data: { email: adminEmail, password: adminPass },
  });
  ok(login.ok(), `admin login (${login.status()})`);

  const page = await ctx.newPage();
  const slug = `e2e-${stamp}`;

  // --- create-tenant workflow (use English locale for stable labels) ---
  await page.goto(`${BASE}/en/admin/tenants`, { waitUntil: "networkidle" });
  const inputs = page.locator(".card form input");
  await inputs.nth(0).fill(slug); // slug
  await inputs.nth(1).fill("E2E Demo Store"); // name
  await page.locator(".card form button").first().click();

  // mutation feedback: success alert with the one-time API key
  await page.waitForSelector(".alert-success code", { timeout: 8000 }).catch(() => {});
  const key = await page.locator(".alert-success code").first().textContent().catch(() => null);
  ok(!!key && key.startsWith("acip_"), "create-tenant returns one-time API key");

  // mutation updates the UI: the new tenant row appears in the table
  await page.waitForTimeout(400);
  const rowVisible = await page.locator(`table.table >> text=${slug}`).count();
  ok(rowVisible > 0, "new tenant row appears in the list (UI updated)");

  // --- tenant export button present on the detail page (navigate by href) ---
  const href = await page
    .locator("table.table a.grad-text")
    .first()
    .getAttribute("href")
    .catch(() => null);
  ok(!!href, "tenant row links to a detail page");
  if (href) {
    await page.goto(BASE + href, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("button", { timeout: 8000 }).catch(() => {});
    const exportBtn = await page.locator('button:has-text("Export data")').count();
    ok(exportBtn > 0, "tenant detail exposes Export data action");
  }

  await browser.close();
  console.log(`\nfunctional-check: ${failures} failure(s).`);
  process.exit(failures > 0 ? 1 : 0);
})().catch((e) => { console.error("functional-check error:", e.message); process.exit(2); });
