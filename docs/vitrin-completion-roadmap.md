# پلن تکمیل حرفه‌ای Vitrin — نسخهٔ زنده (تیک‌خورده)

> این فایل نسخهٔ اجرایی پلن شماست و بعد از هر فاز به‌روزرسانی می‌شود.
> قانون اجرا: هر فاز پس از تحویل **متوقف** می‌شود تا شما صریحاً تأیید کنید.

## وضعیت فازها

| فاز | عنوان | وضعیت |
|-----|-------|--------|
| ۱ | Admin Tenant Management | ✅ تأییدشده ([گزارش](../reports/phases/phase-01-admin-tenant.md)) |
| ۲ | Admin Revenue, Plans, Users, Inbox | ✅ تأییدشده ([گزارش](../reports/phases/phase-02-admin-revenue.md)) |
| ۳ | Admin Observability و امنیت | ✅ تأییدشده ([گزارش](../reports/phases/phase-03-admin-observability.md)) |
| ۴ | Admin ES Console, Agent, Widget, QA | ✅ تأییدشده ([گزارش](../reports/phases/phase-04-admin-qa.md)) |
| ۵ | Owner Dashboard (۱۷ صفحه) | ✅ تأییدشده ([گزارش](../reports/phases/phase-05-owner-dashboard.md)) |
| ۶ | موتور هوشمند: ES + Sync + Inference | ✅ تأییدشده ([گزارش](../reports/phases/phase-06-engine.md)) |
| ۷ | یکپارچه‌سازی OpenCart / WooCommerce | ✅ تأییدشده — بازبینی مجدد کامل ([گزارش](../reports/phases/phase-07-integrations.md)) |
| ۸ | Dev Sign-off (تست نهایی ویندوز) | ✅ تأییدشده — بازبینی مجدد ([گزارش](../reports/dev-signoff.md)) — اقلام ES-دار سمت شما |
| ۹ | انتقال سرور + hardening (عملیاتی) | ✅ تأییدشده — بازبینی مجدد با ۳ اصلاح ([گزارش](../reports/phases/phase-09-hardening.md)) |
| ۱۰ | PSP + Invoice PDF (عملیاتی) | ✅ **تحویل‌شده** ([گزارش](../reports/phases/phase-10-psp.md)) |
| ۱۱ | Production Go-Live | ✅ **تحویل‌شده — Go-Live نهایی منتظر تأیید متنی شما** ([گزارش](../reports/production-readiness.md)) |

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
- [x] **تأیید شما برای فاز ۳** ✅ (پس از بازبینی مجدد ۲۲مرحله‌ای + اصلاح همگام‌سازی نشان پیام)

---

## فاز ۳ — ادمین: Observability و امنیت ✅

- [x] `GET /admin/audit` — فیلتر actor/action/tenant/date + cursor (+ خروجی CSV)
- [x] `GET /admin/usage` — فیلتر tenant/route/rung (+ بازهٔ روز) + export CSV
- [x] `GET /admin/queue` — worker heartbeat + active tasks (Celery inspect؛ عمق صف از Redisِ خود broker)
- [x] `GET /admin/security` — قفل‌های هر دو صفحهٔ هویتی + `POST /admin/security/unlock`
- [x] degraded flags در analytics/insight/zero-results/analyst به‌جای 500
- [x] UI: بنر degraded تحلیل + نشان Template/LLM تحلیلگر · Usage/Audit فیلتر+export · Security unlock · Queue worker list · Models reachability ping · Health sparkline + تأخیر وابستگی‌ها
- [x] `scripts/start-worker.ps1` + مستندات نصب فارسی (`docs/INSTALL-fa.md`)
- [x] پذیرش: ES خاموش → degraded نه crash · audit فیلتر tenant · worker واقعی در صفحهٔ queue
- [x] گزارش: `reports/phases/phase-03-admin-observability.md`
- [x] **تأیید شما برای فاز ۴** ✅ (پس از بازبینی مجدد ۱۹مرحله‌ای بدون هیچ نقص)

---

## فاز ۴ — ادمین: ES Console, Agent, Widget و QA ✅

- [x] ES wizard راه‌اندازی اولیه (ensure-index → reindex اختیاری → alias) + log عملیات (همهٔ اکشن‌های کنسول هم ثبت می‌شوند)
- [x] Agent: history مکالمه (به‌ازای هر فروشگاه، ماندگار در مرورگر) + دکمهٔ clear
- [x] Synonyms: placeholderهای hardcoded → i18n (fa+en)
- [x] Widget: preview واقعی `/widget/v1.js` در iframe sandbox (+ refresh بعد از ذخیره)
- [x] Flags: توضیح تأثیر (i18n) + last changed by (migration `0014`)
- [x] fe-qa: ۷ route ادمین به responsive (پوشش کامل ۲۰ مسیر) + ۴ چک functional جدید + a11y ادمین (۸ صفحه با ورود واقعی؛ نقص select بدون نام در همهٔ صفحات رفع شد)
- [x] پذیرش: `check:all` سبز + responsive همهٔ routeهای ادمین + a11y صفر نقض
- [x] گزارش: `reports/phases/phase-04-admin-qa.md`
- [x] **تأیید شما برای فاز ۵** ✅

---

## فاز ۵ — داشبورد فروشگاه‌دار ✅

- [x] Overview: KPI + هشدار اعتبار کم + چک‌لیست onboarding زنده (۴ گام از وضعیت واقعی)
- [x] Catalog: وضعیت sync (last sync + doc count از ES با تفکیک «خالی/خاموش») + دکمهٔ «sync now»
- [x] Search: تست جست‌وجوی زنده (`POST /tenant/search-test`) + دکمهٔ «امتحان» روی عبارت‌های بدون‌نتیجه
- [x] Chat/Assistant: وضعیت inference برای مالک (`GET /tenant/assistant-status`) + empty state راهنما
- [x] Analytics/Sales/Chat: degraded states (بنر + پرچم backend)
- [x] Leads: فیلتر status (چیپ با شمارش) + bulk actions (انتخاب گروهی + اعمال وضعیت)
- [x] Billing: پنل پیش‌نمایش upgrade (تناسب‌سنجی) + دانلود فاکتور HTML قابل چاپ
- [x] Widget: embed واقعی + تست زنده در صفحه (loader واقعی در iframe + کلید اختیاری)
- [x] Knowledge: جست‌وجو در مقالات
- [x] Team: pending invites (نشان + شمارنده) + resend (`POST /tenant/team/resend`)
- [x] Settings: wizard اتصال OpenCart/Woo (۳ گام با تیک از وضعیت واقعی)
- [x] Backend: `GET /tenant/sync-status` + `POST /tenant/sync/trigger` (+ ثبت اجرای worker در sync_state)
- [x] پذیرش: signup → onboarding ۴از۴ → widget embed روی localhost + degraded states (۲۴ چک زنده)
- [x] گزارش: `reports/phases/phase-05-owner-dashboard.md`
- [x] **تأیید شما برای فاز ۶** ✅

---

## فاز ۶ — موتور هوشمند: ES + Sync + Inference ✅

- [x] bootstrap خودکار index + graceful degradation (503 با کد واضح: `search_unavailable` / `index_not_ready` / `assistant_unavailable`)
- [x] `scripts/seed_catalog.py` — ۱۰۰ محصول فارسی + tenant demo + api_key (+ `--dry-run` و `--no-embeddings`)
- [x] bulk sync نمونه + fixture (`tests/fixtures/catalog_fa.json` + تست ingest در `tests/integration/test_engine.py`)
- [x] golden set eval — ۵۰ کوئری فارسی (`eval/golden_set/golden_fa.jsonl`) + KPI runner (`run_eval --kpi`) + groundedness runner (`eval/groundedness.py`)
- [ ] پذیرش: `/v1/search` و `/v1/chat` پاسخ واقعی روی localhost + ثبت KPIها (روی ویندوز شما با ES روشن — دستورها در گزارش فاز)
- [x] گزارش: `reports/phases/phase-06-engine.md` + **تأیید شما** ✅ (پس از بازبینی مجدد با ۳ اصلاح)

---

## فاز ۷ — یکپارچه‌سازی فروشگاه ✅

- [x] OpenCart 3 pilot: test connection + bulk + webhook (+ endpoint خروجی `export` با توکن برای pull) — نصب روی فروشگاه واقعی سمت شما طبق `docs/integrations-fa.md`
- [x] WooCommerce pilot (+ pull با REST API استاندارد Woo: consumer key/secret فقط‌خواندنی)
- [x] Delta reconciliation — hook غیر no-op: `acip_sync/fetch.py` + `reconcile_tenant` واقعی (watermark + جاروی beat برای همهٔ tenantهای متصل + ثبت خطا در sync_state)
- [x] `docs/integrations-fa.md`
- [x] پذیرش: فروشگاه pilot (شبیه‌ساز `scripts/pilot_store.py` با ۸ محصول فارسی) → sync → دلتا فقط محصول ویرایش‌شده (۴ تست E2E پاس؛ جست‌وجوی ویجت روی ES زندهٔ شما)
- [x] گزارش: `reports/phases/phase-07-integrations.md` + **تأیید شما** ✅ (بازبینی مجدد: سریال‌سازی Celery/ایمنی ویزارد/عدم پیشروی watermark در خطا تأیید؛ نکتهٔ حذف در pull به مستند اضافه شد؛ ۱۱ تست سبز)

---

## فاز ۸ — Dev Sign-off ✅

- [x] چک‌لیست صفحات: جاروی زندهٔ خودکار ۲۰ ادمین + ۱۶ داشبورد (`signoff-sweep.cjs`) — ۳۶/۳۶ سبز + نمونهٔ fa/RTL
- [x] `check:all` + responsive + functional + a11y سبز · integration tests با ES داکر → سمت شما (دستورها در گزارش)
- [x] graceful 503 در `/v1/*` وقتی ES down — curl زنده + تست خودکار
- [x] `reports/dev-signoff.md` — فاز عملیاتی با دستور متنی شما («این سه تا فاز رو بصورت کامل انجام بده») آغاز شد

---

## فاز ۹ — انتقال سرور (عملیاتی) ✅
- [x] `docs/DEPLOYMENT-SERVER.md` (راهنمای کامل فارسی)
- [x] compose production (`infra/docker-compose.prod.yml` + `Caddyfile` + `apps/web/Dockerfile` + `.env.production.example`)
- [x] backup/restore تست‌شده (`infra/backup.sh` + `restore.sh` — چرخهٔ کامل روی PG واقعی: ۲۲ جدول/۱۵ migration/۵۱۴ tenant یکسان)
- [x] TLS (Caddy خودکار) + `COOKIE_SECURE` + HSTS — در compose اجباری
- [x] MFA/TOTP ادمین (RFC 6238 با stdlib + migration `0015` + UI + تأیید زندهٔ کامل)
- [x] IP allowlist `/admin/*` (`ADMIN_IP_ALLOWLIST` — fail-closed؛ تأیید زندهٔ 403)
- [x] monitoring (Prometheus داخلی + alerts در compose)
- [x] load test (`scripts/load_test.py` — نمونه: healthz ۴۸۲rps/p95=87ms؛ اعداد search روی سرور شما با ES)
- [x] گزارش: `reports/phases/phase-09-hardening.md` + **تأیید شما** ⏸️

## فاز ۱۰ — PSP (عملیاتی) ✅
- [x] زرین‌پال v4 (request/StartPay/callback با **verify سمت سرور**؛ sandbox با یک env) + مسیر manual پابرجا + webhook امضادار قبلی
- [x] Invoice PDF فارسی سمت سرور (fpdf2 + uharfbuzz، فونت auto-discover) + endpoint دانلود + fallback تمیز به HTML
- [x] UI checkout: redirect به درگاه + بنر نتیجهٔ پرداخت + دکمهٔ PDF (i18n کامل)
- [x] تست‌ها: ۵ hermetic + ۳ E2E با درگاه جعلی (پرداخت موفق/انصراف/idempotency) — همه پاس
- [ ] تراکنش sandbox روی staging با merchant زرین‌پال شما (اعتبارنامه سمت شما — دستورها در گزارش)
- [x] گزارش: `reports/phases/phase-10-psp.md`

## فاز ۱۱ — Go-Live ✅
- [x] `reports/production-readiness.md` (نقشهٔ هدف→شواهد + ۶ قلم باز اجرایی + ریسک‌ها)
- [x] runbook SLO/DR: `docs/RUNBOOK-SLO-DR.md` (SLOها، playbook رخدادها، DR با RPO/RTO، تشدید)
- [ ] **تأیید متنی نهایی شما برای Go-Live** ⏸️ (پس از بستن اقلام باز بند ۳ گزارش آمادگی)

---

## تکمیل ماژول‌های فروشگاهی — `/plugins` + ایندکس سفارش ✅
- [x] یکپارچه‌سازی مسیر: ماژول‌های کامل OpenCart 3 / وردپرس از `integrations/` به
      مسیر درخواستی `/plugins` منتقل شدند (پوشه‌بندی/ساختار native هر CMS
      دست‌نخورده)؛ استاب‌های قدیمی تک‌فایلی حذف شدند.
- [x] ایندکس **سفارش** در Elasticsearch (قبلاً فقط محصول ایندکس می‌شد): mapping،
      normalize، ingest ایدمپوتنت، bootstrap ایندکس، endpointهای
      `/v1/sync/order/webhook` و `/v1/sync/order/bulk`.
- [x] هر دو ماژول: تنظیم «همگام‌سازی سفارش‌ها» + رویدادهای افزودن/تغییر وضعیت
      سفارش (ادمین و storefront) + دکمهٔ ورود کامل سوابق سفارش‌ها.
- [x] رفع یک ناهماهنگی موجود: پارسر webhook محصول WooCommerce با شکل واقعی
      payload افزونه هماهنگ شد (event/product envelope، نه فیلدهای تخت).
- [x] `docs/api-reference-fa.md` — مرجع کامل API: احراز هویت/امنیت کلید (و
      اتصال آن به پلن مستأجر)، تمام endpointها، و شکل دقیق داده برای محصول و سفارش.

---

## تکمیل مدیریت کردیت، چند-ارائه‌دهندگی هوش مصنوعی و سودآوری ✅
- [x] تحلیل کامل + مقایسه با OpenRouter/LiteLLM/Portkey:
      `reports/ai-billing-providers-analysis-fa.md`.
- [x] Migration `0018` — `ai_providers`/`ai_models`/`ai_routes`/`pricing_settings`
      + ستون‌های `provider`/`model`/`provider_cost` روی `usage_events`.
- [x] موتور قیمت‌گذاری مبتنی بر توکن (`acip_billing/pricing.py`) — هزینهٔ واقعی
      ارائه‌دهنده → سود پلتفرم → کردیت، با fallback کامل به رفتار قبلی.
- [x] Registry پویا (`acip_gateway/registry.py`) — چند ارائه‌دهنده/مدل، مسیریابی
      per-task قابل‌تغییر بدون ری‌استارت، همیشه با ترمینال محلی.
- [x] `WalletBudgetGuard` — کیف‌پول واقعی مستأجر اکنون در مسیر درخواست اعمال
      می‌شود (نه فقط نمایشی)؛ رفع باگ سقف ماهانه که در واقع «همیشگی» بود.
- [x] `/admin/ai/*` (providers, models, routes, pricing, finance) + پنل ادمین
      (`/admin/models`: کارت‌های ارائه‌دهنده/مسیریابی/قیمت‌گذاری/سود).
- [x] ۲۹ تست واحد جدید؛ `ruff`/`mypy`/`pytest`/`tsc`/`check:all`/`next build` سبز.
