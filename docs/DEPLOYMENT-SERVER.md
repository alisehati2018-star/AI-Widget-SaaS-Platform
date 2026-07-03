# راهنمای استقرار سرور تولید (Vitrin) — فاز ۹

استقرار تک‌سرور با Docker Compose. فقط Caddy (پورت ۸۰/۴۴۳) روی اینترنت باز است؛ دیتابیس‌ها فقط داخل شبکهٔ داکرند.

## ۱) پیش‌نیاز سرور

- Ubuntu 22.04+ (یا معادل)، حداقل **۸ گیگ RAM** (ES نصفش را می‌خواهد؛ ۱۶ گیگ توصیه)
- Docker + Docker Compose v2
- دو رکورد DNS به IP سرور: `app.example.com` (وب) و `api.example.com` (API)
- `vm.max_map_count` برای ES:
  ```bash
  echo vm.max_map_count=262144 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p
  ```

## ۲) پیکربندی

```bash
git clone <repo> vitrin && cd vitrin
cp .env.production.example .env.production
# همهٔ مقادیر خالی را پر کنید — secretها با: openssl rand -hex 32
nano .env.production
```

نکات امنیتی اجباری (در compose تولید به‌صورت پیش‌فرض روشن‌اند):

| قلم | مقدار تولید |
|---|---|
| TLS | خودکار توسط Caddy (Let's Encrypt، تمدید خودکار) |
| `COOKIE_SECURE` / `HSTS_ENABLED` / `CSRF_ENABLED` | `true` (در compose ثابت شده) |
| `ADMIN_IP_ALLOWLIST` | IP دفتر/VPN شما — `/admin/*` از بقیهٔ دنیا **403** می‌گیرد (پاسخ `ip_not_allowed`) |
| MFA ادمین | بعد از اولین ورود، از **تنظیمات ← ورود دومرحله‌ای (TOTP)** برای همهٔ ادمین‌ها فعال کنید |
| ES security | روشن (`ELASTIC_PASSWORD`) |
| کلید‌ها/توکن‌ها | فقط در `.env.production`؛ هرگز commit نشود |

## ۳) بالا آوردن

```bash
docker compose -f infra/docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f infra/docker-compose.prod.yml ps       # همه باید healthy شوند
```

migrationها بار اول خودکار اعمال می‌شوند (mount در `/docker-entrypoint-initdb.d`). برای ارتقاهای بعدی:

```bash
docker compose -f infra/docker-compose.prod.yml exec api \
  python scripts/apply_migrations.py
```

اولین ادمین (فقط یک بار، از خود سرور):

```bash
curl -s https://api.example.com/admin/auth/bootstrap \
  -H "x-admin-token: $ADMIN_TOKEN" -H "content-type: application/json" \
  -d '{"email":"ops@example.com","password":"<قوی>","full_name":"Ops"}'
```

سپس: ورود به `https://app.example.com/fa/admin/login` → تنظیمات → **فعال‌سازی TOTP**.

## ۴) پشتیبان‌گیری و بازیابی (تست‌شده)

```bash
# پشتیبان (PG dump + Redis SAVE + snapshot ES در repo مانت‌شده /snapshots):
PG_HOST=... PG_PASSWORD=... ES_URL=http://localhost:9200 ES_PASSWORD=... \
  ./infra/backup.sh /var/backups/vitrin

# بازیابی PG (dump با --clean ساخته شده؛ روی دیتابیس موجود جایگزین می‌کند):
PG_HOST=... PG_PASSWORD=... PG_DB=acip ./infra/restore.sh /var/backups/vitrin/pg-acip-*.sql.gz
```

- cron پیشنهادی: روزانه + نگهداری ۱۴ نسخه؛ خروجی را به یک مقصد خارج از سرور همگام کنید.
- کاتالوگ ES از فروشگاه‌ها بازسازی‌پذیر است (bulk import / reconciliation)؛ snapshot فقط برای بازیابی سریع است:
  `POST /_snapshot/vitrin/snap-<stamp>/_restore`
- RPO = فاصلهٔ backup (پیش‌فرض ۲۴h) · RTO ≈ نصب compose + restore (< ۳۰ دقیقه).
- این چرخه در محیط توسعه تست شده است: dump → restore به دیتابیس تازه → ۲۲ جدول / ۱۵ migration / شمار tenantها یکسان.

## ۵) مانیتورینگ

```bash
docker compose -f infra/docker-compose.prod.yml --profile monitoring up -d prometheus
```

- Prometheus داخلی است (پورت publish نمی‌شود) و `/metrics` سرویس API را می‌خواند؛ قواعد هشدار در `infra/alerts.yml`
- سلامت سریع: `curl https://api.example.com/healthz` و صفحهٔ ادمین **Health** (تأخیر وابستگی‌ها + sparkline)
- لاگ‌ها: `docker compose -f ... logs -f api worker`

## ۶) تست بار (پذیرش)

```bash
# روی سرور یا از بیرون؛ کلید widget واقعی بدهید:
PYTHONPATH=packages:services python scripts/load_test.py \
  --url https://api.example.com/v1/search --key <WIDGET_KEY> \
  --concurrency 20 --requests 500
# هدف blueprint: search p95 < 150ms · p99 < 300ms (با ES روشن و کش گرم)
```

خروجی JSON شامل rps + p50/p95/p99 + شمارش statusهاست. نکته: زیر فشار، محدودیت نرخ هر tenant ممکن است 429 برگرداند — رفتار درست است؛ برای تست ظرفیت خام، چند کلید/tenant موازی استفاده کنید.

## ۷) به‌روزرسانی نسخه

```bash
git pull
docker compose -f infra/docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f infra/docker-compose.prod.yml exec api python scripts/apply_migrations.py
```

## ۸) چک‌لیست تحویل سرور

- [ ] DNS + گواهی TLS صادر شد (`https://app...` و `https://api...` سبز)
- [ ] `ADMIN_IP_ALLOWLIST` تنظیم و از یک IP خارج از فهرست ۴۰۳ گرفتید
- [ ] TOTP برای همهٔ ادمین‌ها فعال
- [ ] backup روزانهٔ cron + یک restore آزمایشی موفق
- [ ] Prometheus بالا و هشدارها فعال
- [ ] load test اجرا و اعداد ثبت شد
- [ ] seed یا اتصال فروشگاه واقعی + جست‌وجوی ویجت روی دامنهٔ تولید
