/* Responsive validation: loads pages at mobile/tablet/desktop widths and fails
 * if any page overflows horizontally (the "no horizontal scrolling" rule).
 * Seeds a few tenants so admin tables actually render rows. Run against a live
 * web+backend stack. Usage: node responsive-check.cjs  (BASE, ADMIN_TOKEN env). */
const { chromium } = require("/opt/node22/lib/node_modules/playwright");

const BASE = process.env.BASE || "http://127.0.0.1:3000";
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || "dev-admin-token";
const EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const WIDTHS = [320, 375, 768, 1280];
const TOL = 2; // px rounding tolerance

const PUBLIC = ["/", "/en", "/pricing", "/features", "/docs", "/contact", "/login", "/signup",
  "/forgot-password", "/reset-password", "/verify-email", "/legal/terms", "/legal/privacy"];
const ADMIN = ["/admin", "/admin/tenants", "/admin/users", "/admin/plans", "/admin/billing",
  "/admin/usage", "/admin/analytics", "/admin/models", "/admin/health", "/admin/security",
  "/admin/flags", "/admin/audit", "/admin/settings"];
const OWNER = ["/dashboard", "/onboarding", "/dashboard/catalog", "/dashboard/search",
  "/dashboard/widget", "/dashboard/assistant", "/dashboard/knowledge", "/dashboard/analytics",
  "/dashboard/chat", "/dashboard/sales", "/dashboard/leads", "/dashboard/keys", "/dashboard/team",
  "/dashboard/credits", "/dashboard/billing", "/dashboard/audit", "/dashboard/settings"];

let failures = 0;

async function overflow(page) {
  return page.evaluate(() => {
    const el = document.documentElement;
    return Math.max(0, el.scrollWidth - el.clientWidth, document.body.scrollWidth - el.clientWidth);
  });
}

async function check(ctx, paths, widths, label) {
  for (const path of paths) {
    for (const width of widths) {
      const page = await ctx.newPage();
      await page.setViewportSize({ width, height: 900 });
      await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 20000 });
      await page.waitForTimeout(250);
      const ov = await overflow(page);
      if (ov > TOL) {
        console.error(`✗ overflow ${ov}px — ${label} ${path} @ ${width}px`);
        failures++;
      }
      await page.close();
    }
  }
}

(async () => {
  const browser = await chromium.launch({ executablePath: EXE });
  const ctx = await browser.newContext();
  const api = ctx.request;

  // Seed: bootstrap a fresh admin + a few store owners (populates admin tables).
  const stamp = Date.now();
  const adminEmail = `admin.rc.${stamp}@vitrin.ai`;
  const adminPass = "Adm1n!Str0ng#2026";
  const boot = await api.post(`${BASE}/api/admin/auth/bootstrap`, {
    headers: { "x-admin-token": ADMIN_TOKEN, "content-type": "application/json" },
    data: { email: adminEmail, password: adminPass, full_name: "Platform Admin" },
  });
  if (!boot.ok()) console.error(`! admin bootstrap ${boot.status()}: ${await boot.text()}`);
  for (let i = 1; i <= 3; i++) {
    await api.post(`${BASE}/api/auth/signup`, {
      headers: { "content-type": "application/json" },
      data: { email: `owner.rc.${stamp}.${i}@store.com`, password: "Sup3r!Str0ng#2026", store_name: `Demo Store ${i}` },
    });
  }
  await ctx.clearCookies();

  // Public pages (no auth) across all breakpoints.
  await check(ctx, PUBLIC, WIDTHS, "public");

  // Admin pages: log in as the bootstrapped admin, then sweep mobile + desktop.
  const login = await api.post(`${BASE}/api/admin/auth/login`, {
    headers: { "content-type": "application/json" },
    data: { email: adminEmail, password: adminPass },
  });
  if (!login.ok()) {
    console.error(`✗ admin login failed: ${login.status()}`);
    failures++;
  } else {
    await check(ctx, ADMIN, [375, 1280], "admin");
  }

  // Owner dashboard: log in as a seeded store owner and sweep.
  await ctx.clearCookies();
  const ownerLogin = await api.post(`${BASE}/api/auth/login`, {
    headers: { "content-type": "application/json" },
    data: { email: `owner.rc.${stamp}.1@store.com`, password: "Sup3r!Str0ng#2026" },
  });
  if (!ownerLogin.ok()) {
    console.error(`✗ owner login failed: ${ownerLogin.status()}`);
    failures++;
  } else {
    await check(ctx, OWNER, [375, 1280], "owner");
  }

  await browser.close();
  console.log(`\nresponsive-check: ${failures} overflow failure(s).`);
  process.exit(failures > 0 ? 1 : 0);
})().catch((e) => {
  console.error("responsive-check error:", e.message);
  process.exit(2);
});
