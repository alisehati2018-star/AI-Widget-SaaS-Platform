# Runbook عملیات: SLO، رخداد و بازیابی فاجعه (Vitrin) — فاز ۱۱

مرجع سریع تیم عملیات. مکمل `docs/DEPLOYMENT-SERVER.md` (استقرار) و `reports/production-readiness.md` (وضعیت آمادگی).

## ۱) SLOها (از blueprint)

| سرویس | SLO | سنجه |
|---|---|---|
| دسترس‌پذیری API | **۹۹.۹٪** ماهانه (بودجهٔ خطا ≈ ۴۳ دقیقه/ماه) | `/healthz` از monitoring خارجی + Prometheus `vitrin_http_requests_total` |
| جست‌وجو | p95 < ۱۵۰ms · p99 < ۳۰۰ms | `vitrin_http_request_duration_seconds` + `scripts/load_test.py` |
| پیشنهادگر (suggest) | < ۵۰ms | همان |
| دستیار (اولین توکن) | < ۱.۵s | لاگ `latency_ms` نوبت‌ها |
| نرخ بدون‌نتیجه | < ۵٪ | داشبورد ادمین ← Analytics |
| صحت ایزولهٔ tenant | ۱۰۰٪ — **ناقض انتشار** | تست‌های isolation در CI |

اصل degrade (§14.1): **جست‌وجو هرگز به AI وابسته نیست** — TEI/LLM خاموش ⇒ BM25 و پاسخ template؛ ES خاموش ⇒ `/v1/*` با 503 کد21دار؛ PG خاموش ⇒ فقط auth/billing می‌خوابد، جست‌وجوی کش‌شده زنده می‌ماند.

## ۲) پاسخ به هشدارها (playbookهای رخداد)

### ES down / قرمز (`search_unavailable` در پاسخ‌ها)
1. `docker compose -f infra/docker-compose.prod.yml ps` و `logs elasticsearch` — شایع: OOM (heap)، دیسک پر (watermark 95%)
2. دیسک: `df -h` → آزادسازی/بزرگ‌کردن، سپس `PUT _cluster/settings` برای خروج از read-only در صورت قفل ایندکس
3. restart سرویس؛ bootstrap ایندکس خودکار است؛ تا برگشتن، ویجت 503 تمیز نشان می‌دهد (رفتار طراحی‌شده — کاربر crash نمی‌بیند)
4. بعد از برگشت: `python -m eval.run_eval ... --kpi` برای اطمینان از سلامت رتبه‌بندی

### PG down
1. `logs postgres`؛ شایع: دیسک/OOM. سرویس restart می‌شود (`restart: unless-stopped`)
2. اگر داده خراب است: **DR بند ۴** — restore از آخرین backup
3. تا برگشتن: جست‌وجوی کش‌شده کار می‌کند؛ ورود/billing خطا می‌دهد — بنر status اطلاع‌رسانی کنید

### Worker/صف عقب‌افتاده (sync اجرا نمی‌شود)
1. صفحهٔ ادمین **Queue** → worker heartbeat + عمق صف؛ یا `logs worker`
2. `docker compose restart worker`؛ رخدادهای مسموم در DLQ می‌مانند (صفحهٔ Queue) — بعد از رفع علت، replay
3. sync هر tenant وضعیت خودش را در `sync_state` دارد (کاتالوگ داشبورد) — خطای یک فروشگاه بقیه را نمی‌خواباند

### پرداخت‌ها fail می‌شوند (`psp_unavailable` / callback=failed)
1. `logs api | grep psp` — خطای شبکهٔ زرین‌پال یا merchant نامعتبر
2. سفارش‌های pending پول کم نکرده‌اند (فعال‌سازی فقط بعد از verify سمت سرور)؛ مشتری می‌تواند دوباره تلاش کند
3. قطعی طولانی PSP: موقتاً `BILLING_PROVIDER=manual` (تأیید اپراتوری) و برگشت بعد از رفع

### حساب ادمین قفل/در خطر
1. قفل عادی: صفحهٔ ادمین **Security** → unlock
2. سوءظن نفوذ: عضویت در `ADMIN_IP_ALLOWLIST` را چک کنید؛ گذرواژه + TOTP را reset کنید (totp_enabled=false از DB فقط با دسترسی مستقیم سرور: `UPDATE admin_users SET totp_enabled=false, totp_secret=NULL WHERE email=...`)؛ همهٔ نشست‌ها: `UPDATE admin_sessions SET revoked=true WHERE admin_user_id=...`

### دیسک پر
`du -sh /var/lib/docker/volumes/*` — مصرف اصلی: es-data و pg-data و backupها. لاگ‌روتیشن داکر + پاک‌سازی snapshotهای کهنه (`DELETE _snapshot/vitrin/<old>`).

## ۳) پایش روزانه (چک ۵ دقیقه‌ای)

- `https://api.<domain>/healthz` سبز · صفحهٔ ادمین **Health** (تأخیر ES/PG/Redis + sparkline)
- Prometheus targets سبز؛ هشدارهای `infra/alerts.yml` بی‌صدا
- خروجی cron پشتیبانِ دیشب موجود و > 0 بایت
- صفحهٔ **Queue**: worker heartbeat < ۲ دقیقه

## ۴) DR — بازیابی فاجعه

**RPO:** فاصلهٔ backup (پیش‌فرض ۲۴h؛ برای کاهش، cron را ساعتی کنید) · **RTO هدف:** < ۳۰ دقیقه.

سناریوی از-دست-رفتن کامل سرور:
1. سرور جدید طبق `docs/DEPLOYMENT-SERVER.md` (DNS را به IP جدید بزنید؛ Caddy گواهی تازه می‌گیرد)
2. `docker compose ... up -d` تا PG خالی بالا بیاید، سپس:
   `PG_HOST=... ./infra/restore.sh <آخرین pg-*.sql.gz>` (اسکریپت شمار جدول/migration/tenant را تأیید می‌کند)
3. کاتالوگ ES: یا restore از snapshot (`POST _snapshot/vitrin/<snap>/_restore`) یا بازسازی از فروشگاه‌ها (bulk import افزونه + reconciliation — self-healing)
4. Redis بازسازی‌پذیر است (کش/صف)؛ چیزی لازم نیست
5. صحت: `/healthz` · ورود ادمین (TOTP کار می‌کند چون secret در PG است) · جست‌وجوی ویجت · یک پرداخت آزمایشی sandbox
6. رخداد را در audit log ثبت کنید

تمرین DR: هر فصل یک‌بار restore روی محیط staging (همان دستور بند ۲) — آخرین اجرا: در توسعه تأیید شده (۲۲ جدول/۱۵+۱ migration/tenantها یکسان).

## ۵) تشدید (escalation)

1. اپراتور کشیک: طبق این runbook تا ۳۰ دقیقه
2. حل نشد → مالک فنی پروژه + ثبت رخداد (زمان شروع، اثر، اقدام‌ها)
3. رخداد امنیتی (نشت کلید/داده): کلیدهای متأثر را فوراً revoke (داشبورد/ادمین)، `AUTH_SECRET` را نچرخانید مگر با برنامه (همهٔ نشست‌ها باطل می‌شود)، گزارش کتبی
