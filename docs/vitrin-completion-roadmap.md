# پلن تکمیل حرفه‌ای Vitrin — نسخهٔ زنده (تیک‌خورده)

> این فایل نسخهٔ اجرایی پلن شماست و بعد از هر فاز به‌روزرسانی می‌شود.
> قانون اجرا: هر فاز پس از تحویل **متوقف** می‌شود تا شما صریحاً تأیید کنید.

## وضعیت فازها

| فاز | عنوان | وضعیت |
|-----|-------|--------|
| ۱ | Admin Tenant Management | ✅ تأییدشده ([گزارش](../reports/phases/phase-01-admin-tenant.md)) |
| ۲ | Admin Revenue, Plans, Users, Inbox | ✅ **تحویل‌شده — منتظر تأیید شما** ([گزارش](../reports/phases/phase-02-admin-revenue.md)) |
| ۳ | Admin Observability و امنیت | ⬜ منتظر تأیید فاز ۲ |
| ۴ | Admin ES Console, Agent, Widget, QA | ⬜ |
| ۵ | Owner Dashboard (۱۷ صفحه) | ⬜ |
| ۶ | موتور هوشمند: ES + Sync + Inference | ⬜ |
| ۷ | یکپارچه‌سازی OpenCart / WooCommerce | ⬜ |
| ۸ | Dev Sign-off (تست نهایی ویندوز) | ⬜ |
| ۹ | انتقال سرور + hardening (عملیاتی) | ⬜ |
| ۱۰ | PSP + Invoice PDF (عملیاتی) | ⬜ |
| ۱۱ | Production Go-Live | ⬜ |

---

## فاز ۱ — ادمین: زیرساخت عملیات و Tenant Management ✅

### Backend
- [x] `GET /admin/tenants/{id}` — پروفایل کامل (slug, name, plan, status, credits, subscription, tracking, created_at, api_keys بدون مادهٔ محرمانه, sync_state, team_size, admin_notes)
- [x] `GET /admin/tenants/{id}/keys` — فهرست کلیدها
- [x] `POST /admin/tenants/{id}/keys` — صدور کلید (widget/sync) با نمایش یک‌بارهٔ کلید خام
- [x] `POST /admin/tenants/{id}/keys/{key_id}/revoke` — ابطال کلید
- [x] `POST /admin/tenants/{id}/credits` — تنظیم دستی اعتبار (ledger + audit)
- [x] `PATCH /admin/tenants/{id}/plan` — تغییر دستی پلن/اشتراک (upsert + دورهٔ تازه + audit)
- [x] `PATCH /admin/tenants/{id}/notes` — یادداشت اپراتور
- [x] گسترش `GET /admin/overview` — سری روزانهٔ ۷/۳۰/۹۰: signups، usage، paid revenue، failed payments (پروکسی صادقانهٔ MRR تاریخی = درآمد روزانه)
- [x] گسترش `GET /admin/tenants` — جست‌وجو + فیلتر status/plan + صفحه‌بندی سرور

### Frontend
- [x] **Overview** — کارت‌های KPI + ۴ نمودار روند (tooltip/crosshair، تاریخ شمسی، رنگ اعتبارسنجی‌شده با validate_palette) + سوییچ بازه + هشدار معوق + دسترسی سریع + حالت خطا/خالی
- [x] **Tenants list** — جست‌وجوی زنده، فیلتر status/plan، صفحه‌بندی
- [x] **Tenant detail** — پنل پروفایل + کلیدها + یادداشت (ستون اول)، اعتبار + تغییر پلن + چرخهٔ عمر/حاکمیت (ستون دوم)؛ **refetch بعد از هر mutation**
- [x] **Login** — redirect با نشست فعال + پیام خطای دقیق سرور

### DB / تست / گزارش
- [x] migration `0012` — `tenants.admin_notes`
- [x] تست‌ها: `tests/integration/test_admin_tenant.py` — ۸ تست E2E روی PG واقعی (پوشهٔ integration به‌جای ریشهٔ tests، چون ریشه فقط hermetic است)
- [x] گزارش: `reports/phases/phase-01-admin-tenant.md`

### پذیرش
- [x] ایجاد tenant → پروفایل کامل → suspend → activate → export (تأیید زنده با Playwright + PG در محیط توسعه؛ دستورات ویندوز در گزارش فاز)
- [x] Overview نمودار با دادهٔ PG پر شد
- [x] **تأیید شما برای فاز ۲** ✅ (پس از بازبینی مجدد کامل: اصلاح bucketing منطقهٔ زمانی روندها + رفع ۳ سرریز responsive)

---

## فاز ۲ — ادمین: Revenue, Plans, Users و Inbox ✅

### Backend
- [x] `POST /admin/plans` + `DELETE /admin/plans/{id}` — CRUD کامل پلن (حذفِ پلنِ در حال استفاده → 409 با شمارش مراجع)
- [x] `GET /admin/invoices` — فاکتورهای کل پلتفرم + فیلتر + خلاصهٔ درآمد روی همان فیلتر
- [x] `GET /admin/contact` + `PATCH /admin/contact/{id}` — inbox پیام‌های تماس (migration `0013`: status/admin_note/updated_at)
- [x] `GET/POST/PATCH/DELETE /admin/operators` + `POST /admin/operators/{id}/status` — CRUD ادمین‌ها با قوانین ایمنی (بدون self-suspend/delete؛ حفاظت از آخرین ادمین فعال؛ تعلیق = ابطال نشست‌ها)
- [x] گسترش `GET /admin/users` — جست‌وجو + فیلتر role/status + صفحه‌بندی (و حذف مسیر شکستهٔ ارتقا به platform_admin)

### Frontend
- [x] Plans: دکمهٔ «پلن جدید» + confirm حذف + validation
- [x] Billing: تب Invoices + فیلتر status/tenant + خلاصهٔ درآمد
- [x] Users: فیلتر role/status + جست‌وجوی ایمیل/نام/فروشگاه + صفحه‌بندی
- [x] صفحهٔ جدید `/admin/contact` — inbox با mark-read خودکار + یادداشت پیگیری + resolve/بازگشایی
- [x] صفحهٔ جدید `/admin/operators` — مدیریت ادمین‌ها (افزودن/نام/تعلیق/حذف + نشان «شما»)
- [x] Settings: لینک به Operators + نمایش نشست فعال
- [x] i18n (fa+en) + افزودن به nav

### پذیرش
- [x] ساخت پلن جدید → نمایش در صفحهٔ عمومی قیمت‌گذاری (`/pricing`)
- [x] inbox contact کار می‌کند (تأیید زنده + تست خودکار)
- [x] ادمین دوم بدون bootstrap token (از UI ساخته و وارد شد)
- [x] گزارش: `reports/phases/phase-02-admin-revenue.md`
- [ ] **تأیید شما برای فاز ۳** ⏸️

---

## فاز ۳ — ادمین: Observability و امنیت ⬜

- [ ] `GET /admin/audit` — فیلتر actor/action/tenant/date + cursor
- [ ] `GET /admin/usage` — فیلتر tenant/route/rung + export CSV
- [ ] `GET /admin/queue` — worker heartbeat + active tasks (Celery inspect)
- [ ] `GET /admin/security` — unlock دستی حساب‌های قفل
- [ ] degraded flags در analytics/insight/analyst به‌جای 500
- [ ] UI: Analytics badge «Template» + empty state برای ES down · Usage/Audit فیلتر+export · Security unlock · Queue worker list · Models reachability ping · Health sparkline
- [ ] `scripts/start-worker.ps1` + به‌روزرسانی مستندات نصب فارسی
- [ ] پذیرش: ES خاموش → degraded نه crash · audit فیلتر tenant · worker در صفحهٔ queue
- [ ] گزارش: `reports/phases/phase-03-admin-observability.md` + **تأیید شما**

---

## فاز ۴ — ادمین: ES Console, Agent, Widget و QA ⬜

- [ ] ES wizard راه‌اندازی اولیه (ensure-index → reindex → alias) + log عملیات
- [ ] Agent: history مکالمه + دکمهٔ clear
- [ ] Synonyms: placeholderهای hardcoded → i18n
- [ ] Widget: preview واقعی `/widget/v1.js` در iframe sandbox
- [ ] Flags: توضیح تأثیر + last changed by
- [ ] fe-qa: افزودن ۶ route ادمین به responsive + گسترش functional + a11y ادمین
- [ ] پذیرش: `check:all` سبز + responsive همهٔ routeهای ادمین
- [ ] گزارش: `reports/phases/phase-04-admin-qa.md` + **تأیید شما**

---

## فاز ۵ — داشبورد فروشگاه‌دار ⬜

- [ ] Overview: KPI + هشدار اعتبار + چک‌لیست onboarding
- [ ] Catalog: وضعیت sync (last sync + doc count از ES) + دکمهٔ «sync now»
- [ ] Search: تست جست‌وجوی زنده + لینک zero-results
- [ ] Chat/Assistant: وضعیت inference + empty state راهنما
- [ ] Analytics/Sales: degraded states
- [ ] Leads: فیلتر status + bulk actions
- [ ] Billing: پیش‌نمایش upgrade + دانلود فاکتور (HTML)
- [ ] Widget: embed واقعی + تست در صفحه
- [ ] Knowledge: جست‌وجو در مقالات
- [ ] Team: pending invites + resend
- [ ] Settings: wizard اتصال OpenCart/Woo
- [ ] Backend: `GET /tenant/sync-status` + `POST /tenant/sync/trigger`
- [ ] پذیرش: signup → onboarding → widget embed روی localhost + degraded states
- [ ] گزارش: `reports/phases/phase-05-owner-dashboard.md` + **تأیید شما**

---

## فاز ۶ — موتور هوشمند: ES + Sync + Inference ⬜

- [ ] bootstrap خودکار index + graceful degradation (503 با کد واضح)
- [ ] `scripts/seed_catalog.py` — ۱۰۰ محصول فارسی + tenant demo + api_key
- [ ] bulk sync نمونه + fixture
- [ ] golden set eval — ۵۰ کوئری فارسی (KPI: NDCG@10 ≥ 0.80 · p95 < 150ms · zero-result < 5% · groundedness ≥ 95%)
- [ ] پذیرش: `/v1/search` و `/v1/chat` پاسخ واقعی روی localhost + ثبت KPIها
- [ ] گزارش: `reports/phases/phase-06-engine.md` + **تأیید شما**

---

## فاز ۷ — یکپارچه‌سازی فروشگاه ⬜

- [ ] OpenCart 3 pilot: test connection + bulk + webhook با فروشگاه واقعی محلی
- [ ] WooCommerce pilot
- [ ] Delta reconciliation (hook غیر no-op در `acip_sync`)
- [ ] `docs/integrations-fa.md`
- [ ] پذیرش: فروشگاه pilot → sync → جست‌وجو در ویجت
- [ ] گزارش: `reports/phases/phase-07-integrations.md` + **تأیید شما**

---

## فاز ۸ — Dev Sign-off ⬜

- [ ] چک‌لیست دستی ۲۰ صفحه ادمین + ۱۷ صفحه dashboard
- [ ] integration tests با ES داکر + `check:all` + responsive + functional سبز
- [ ] graceful 503 در `/v1/*` وقتی ES down
- [ ] `reports/dev-signoff.md` — **فقط پس از تأیید متنی شما فاز عملیاتی شروع می‌شود**

---

## فاز ۹ — انتقال سرور (عملیاتی) ⬜
- [ ] `docs/DEPLOYMENT-SERVER.md` · compose production · backup/restore تست‌شده · TLS + `COOKIE_SECURE` · MFA/TOTP ادمین · IP allowlist `/admin/*` · monitoring · load test

## فاز ۱۰ — PSP (عملیاتی) ⬜
- [ ] Stripe/ZarinPal + webhook production + Invoice PDF + UI checkout (sandbox روی staging)

## فاز ۱۱ — Go-Live ⬜
- [ ] `reports/production-readiness.md` + SLO/DR runbook + تأیید نهایی شما
