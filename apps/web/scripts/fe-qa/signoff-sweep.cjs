/* Dev sign-off sweep (Phase 8): loads EVERY admin + dashboard page signed in
 * and fails if a page doesn't render (no heading, error boundary, or a crash).
 * The per-page result list IS the sign-off checklist.
 * Run against a live stack:  ADMIN_TOKEN=… node scripts/fe-qa/signoff-sweep.cjs */
const { chromium } = require("/opt/node22/lib/node_modules/playwright");

const BASE = process.env.BASE || "http://127.0.0.1:3000";
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || "dev-admin-token";
const EXE = process.env.CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";

const ADMIN_PAGES = [
  "/admin", "/admin/tenants", "/admin/users", "/admin/plans", "/admin/billing",
  "/admin/analytics", "/admin/usage", "/admin/audit", "/admin/security",
  "/admin/queue", "/admin/health", "/admin/models", "/admin/elasticsearch",
  "/admin/synonyms", "/admin/agent", "/admin/widget", "/admin/flags",
  "/admin/contact", "/admin/operators", "/admin/settings",
];
const DASH_PAGES = [
  "/dashboard", "/dashboard/catalog", "/dashboard/search", "/dashboard/assistant",
  "/dashboard/knowledge", "/dashboard/analytics", "/dashboard/sales",
  "/dashboard/chat", "/dashboard/leads", "/dashboard/billing", "/dashboard/credits",
  "/dashboard/keys", "/dashboard/widget", "/dashboard/team", "/dashboard/audit",
  "/dashboard/settings",
];
const ERROR_MARKERS = ["Application error", "Internal Server Error", "این صفحه پیدا نشد", "404"];

async function sweep(ctx, paths, label) {
  let failures = 0;
  for (const path of paths) {
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e.message).slice(0, 120)));
    try {
      const resp = await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 30000 });
      const status = resp ? resp.status() : 0;
      const heading = (await page
        .locator("main h1, main h2, #content h1, h1, h2")
        .first()
        .textContent({ timeout: 5000 }))?.trim();
      const body = (await page.locator("body").innerText()).slice(0, 4000);
      const marker = ERROR_MARKERS.find((m) => body.includes(m));
      if (status >= 400 || !heading || marker || errors.length) {
        failures++;
        console.error(
          `✗ ${label} ${path} — status=${status} heading=${JSON.stringify(heading || "")}` +
          (marker ? ` marker=${marker}` : "") + (errors.length ? ` jsErrors=${errors.join("; ")}` : ""),
        );
      } else {
        console.log(`✓ ${label} ${path} — «${heading}»`);
      }
    } catch (e) {
      failures++;
      console.error(`✗ ${label} ${path} — ${String(e.message).slice(0, 140)}`);
    }
    await page.close();
  }
  return failures;
}

(async () => {
  const browser = await chromium.launch({ executablePath: EXE });
  let failures = 0;
  const stamp = Date.now();

  // Admin surface (real bootstrap + login).
  const admCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await admCtx.request.post(`${BASE}/api/admin/auth/bootstrap`, {
    headers: { "x-admin-token": ADMIN_TOKEN, "content-type": "application/json" },
    data: { email: `signoff.${stamp}@vitrin.ai`, password: "Adm1n!Str0ng#2026", full_name: "Signoff" },
  });
  const admLogin = await admCtx.request.post(`${BASE}/api/admin/auth/login`, {
    headers: { "content-type": "application/json" },
    data: { email: `signoff.${stamp}@vitrin.ai`, password: "Adm1n!Str0ng#2026" },
  });
  if (!admLogin.ok()) {
    console.error(`✗ admin login failed (${admLogin.status()})`);
    failures++;
  } else {
    failures += await sweep(admCtx, ADMIN_PAGES, "admin");
  }
  await admCtx.close();

  // Owner dashboard (real signup + login cookies).
  const ownCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const signup = await ownCtx.request.post(`${BASE}/api/auth/signup`, {
    headers: { "content-type": "application/json" },
    data: { email: `signoff.owner.${stamp}@shop.com`, password: "Sh0p-Str0ng!", store_name: "Signoff" },
  });
  if (!signup.ok()) {
    console.error(`✗ owner signup failed (${signup.status()})`);
    failures++;
  } else {
    failures += await sweep(ownCtx, DASH_PAGES, "dashboard");
  }
  await ownCtx.close();

  await browser.close();
  console.log(`\nsignoff-sweep: ${failures} failure(s) across ${ADMIN_PAGES.length} admin + ${DASH_PAGES.length} dashboard pages.`);
  process.exit(failures > 0 ? 1 : 0);
})().catch((e) => { console.error("signoff-sweep error:", e.message); process.exit(2); });
