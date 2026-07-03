# فاز ۹ — انتقال سرور و سخت‌سازی عملیاتی

**وضعیت: تحویل‌شده — منتظر تأیید شما**
تاریخ تحویل: ۱۴۰۵/۰۴/۱۲ · شاخه: `claude/gallant-shannon-8b31td`

## چه چیزی ساخته شد

### ۱) MFA/TOTP برای ادمین‌های پلتفرم (RFC 6238، بدون وابستگی جدید)

| قطعه | شرح |
|---|---|
| `packages/acip_auth/totp.py` | پیاده‌سازی استاندارد TOTP با stdlib (SHA-1/6رقم/۳۰ثانیه — سازگار با Google Authenticator/Aegis/1Password)؛ تأیید constant-time با پنجرهٔ ±۱ برای انحراف ساعت؛ **با بردارهای مرجع RFC 6238 تست شده** |
| migration `0015` | `admin_users.totp_secret` + `totp_enabled` — تا قبل از confirm با کد زنده، اجبار فعال نمی‌شود (نیمه‌کاره ماندن ثبت‌نام کسی را قفل نمی‌کند) |
| `/admin/auth/totp` (GET) · `/totp/enroll` · `/totp/confirm` · `/totp/disable` | enroll با گذرواژه؛ confirm با کد زنده؛ disable به گذرواژه **و** کد نیاز دارد (نشست دزدیده‌شده به‌تنهایی نمی‌تواند حساب را ضعیف کند)؛ همه با audit |
| ورود | بعد از فعال‌سازی، گذرواژهٔ تنها → `401 totp_required` (فرم فیلد کد را نشان می‌دهد)؛ کد اشتباه در همان نردبان lockout گذرواژه حساب می‌شود |
| UI | کارت «ورود دومرحله‌ای» در تنظیمات ادمین (secret + آدرس otpauth + تأیید) و فیلد کد در صفحهٔ ورود — fa/en کامل |

**تأیید زنده:** چرخهٔ کامل روی مرورگر واقعی (فارسی/RTL): فعال‌سازی از تنظیمات → خروج → ورود فقط‌گذرواژه، فیلد کد ظاهر شد → ورود با کد ✓. + تست E2E خودکار (`tests/integration/test_admin_totp.py`) و ۴ تست واحد با بردارهای RFC.

### ۲) IP allowlist برای `/admin/*`

- `AdminIpAllowlistMiddleware` (پشتیبانی IP و CIDR؛ ورودی خراب **fail-closed**) + تنظیم `ADMIN_IP_ALLOWLIST`
- فقط سطح `/admin` گیت می‌شود؛ سطح عمومی و فروشنده آزاد است
- **تأیید زنده:** API با `ADMIN_IP_ALLOWLIST=203.0.113.0/24` → `/healthz` 200 ولی `/admin/tenants` → **403 `ip_not_allowed`** + ۴ تست hermetic

### ۳) Compose تولید + TLS

- `infra/docker-compose.prod.yml`: فقط Caddy پورت باز دارد (۸۰/۴۴۳)؛ ES با security روشن + volume snapshot؛ API با `--proxy-headers` (IP واقعی پشت پروکسی برای allowlist/rate-limit/نشست‌ها)؛ worker+beat؛ web؛ Prometheus با پروفایل `monitoring`
- `infra/Caddyfile`: TLS خودکار Let's Encrypt برای دامنهٔ وب و API
- `COOKIE_SECURE=true` · `HSTS_ENABLED=true` · `CSRF_ENABLED=true` در compose ثابت شده‌اند
- `apps/web/Dockerfile` (چندمرحله‌ای) + `.env.production.example` با راهنمای تولید secret

### ۴) پشتیبان‌گیری/بازیابی — تست‌شده

- `infra/backup.sh` گسترش یافت: + snapshot الاستیک (repo `vitrin` روی `/snapshots` که compose مانت می‌کند، با `ES_URL`)
- `infra/restore.sh` (جدید): بازیابی dump با تأیید خودکار (شمار جدول/migration/tenant)
- **تست زنده در همین سشن:** backup از PG واقعی (224KB gz) → restore به دیتابیس تازه → **۲۲ جدول / ۱۵ migration / ۵۱۴ tenant یکسان** ✓

### ۵) مانیتورینگ و تست بار

- Prometheus + `alerts.yml` (از قبل موجود) حالا در compose تولید wired شد (شبکهٔ داخلی، بدون پورت عمومی)
- `scripts/load_test.py` (جدید): بار همزمان با گزارش rps + p50/p95/p99 + شمارش statusها در برابر هدف‌های blueprint
- **اجرای نمونه در این سشن:** `/healthz` → **۴۸۲ rps، p95=87ms** · `/v1/search` با ES خاموش → 503های تمیز + فعال‌شدن درست rate-limit هر tenant (429) زیر فشار. اعداد واقعی search روی سرور شما با ES روشن ثبت می‌شود

### ۶) مستند استقرار — `docs/DEPLOYMENT-SERVER.md`

راهنمای کامل فارسی: پیش‌نیاز سرور، DNS/TLS، `.env.production`، بالا آوردن، bootstrap اولین ادمین + فعال‌سازی TOTP، backup/restore با cron و RPO/RTO، مانیتورینگ، load test، ارتقا، و چک‌لیست تحویل.

## گیت‌ها (بعد از همهٔ تغییرات)

| گیت | نتیجه |
|---|---|
| `pytest` | **۱۵۹ پاس / ۴ skip** (۹ تست جدید فاز ۹) |
| `ruff` + `mypy` | تمیز (۱۰۲ فایل) |
| `tsc --noEmit` + `check:all` + `next build` | صفر خطا |
| تأیید زنده | TOTP کامل در UI فارسی · IP allowlist 403 · backup→restore یکسان · load test اجرا شد |

## چک‌لیست پذیرش فاز ۹ (از پلن)

- [x] `docs/DEPLOYMENT-SERVER.md`
- [x] compose production (+ Caddy TLS + Dockerfile وب + env نمونه)
- [x] backup/restore تست‌شده (چرخهٔ کامل روی PG واقعی)
- [x] TLS + `COOKIE_SECURE` (+ HSTS) — در compose تولید اجباری
- [x] MFA/TOTP ادمین — backend + UI + تست + تأیید زنده
- [x] IP allowlist `/admin/*` — middleware + تست + تأیید زنده
- [x] monitoring (Prometheus داخلی + alerts + صفحهٔ Health ادمین)
- [x] load test (`scripts/load_test.py` + اجرای نمونه؛ اعداد نهایی روی سرور تولید با ES)

## اقلام سمت شما هنگام انتقال واقعی سرور

1. اجرای `docs/DEPLOYMENT-SERVER.md` روی سرور (DNS، `.env.production`، `up -d --build`)
2. `python scripts/apply_migrations.py` (برای دیتابیس موجود؛ نصب تازه خودکار است) — migration `0015` را اعمال می‌کند
3. فعال‌سازی TOTP برای همهٔ ادمین‌ها + تنظیم `ADMIN_IP_ALLOWLIST`
4. cron پشتیبان روزانه + یک restore آزمایشی
5. load test روی دامنهٔ تولید با ES روشن و ثبت p95/p99
