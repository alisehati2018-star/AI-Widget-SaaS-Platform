# راهنمای نصب و اجرای Vitrin (توسعه محلی — Windows)

این راهنما برای محیط توسعه‌ای است که:

- **PostgreSQL 18** روی ویندوز نصب است (پورت `5433`)
- **Redis** روی ویندوز نصب است (پورت `6379`)
- **Elasticsearch** داخل Docker اجرا می‌شود (پورت `19500` روی میزبان)
- **API، Worker و Frontend** روی خود ویندوز اجرا می‌شوند (بدون Docker برای اپ)

تنظیمات اتصال از فایل `.env` در ریشه پروژه خوانده می‌شود.

---

## پیش‌نیازها

| ابزار | نسخه پیشنهادی | توضیح |
|---|---|---|
| Python | 3.11+ (شما: 3.12) | بک‌اند FastAPI + Celery |
| Node.js | 20+ | فرانت‌اند Next.js |
| PostgreSQL | 18 | پورت `5433` (PG17 معمولاً `5432`) |
| Redis | 5+ | پورت `6379` |
| Docker Desktop | اخیر | فقط برای Elasticsearch |
| Git | — | کلون پروژه |

مسیر `psql` در این راهنما:

```text
C:\Program Files\PostgreSQL\18\bin\psql.exe
```

---

## ۱. دریافت پروژه و فایل محیط

```powershell
cd "C:\Users\AliSehati\Desktop\AI Widget SaaS Platform"
```

اگر `.env` ندارید، از قالب کپی کنید و مقادیر را تنظیم کنید:

```powershell
Copy-Item .env.example .env
```

مقادیر مهم در `.env` شما:

```env
ES_HOST=http://localhost:19500
PG_HOST=localhost
PG_PORT=5433
PG_DB=acip
PG_USER=acip
PG_PASSWORD=1234
REDIS_URL=redis://localhost:6379/0
ADMIN_TOKEN=dev-operator-token-change-me
AUTH_SECRET=<یک رشته تصادفی ۶۴ کاراکتری>
APP_BASE_URL=http://localhost:3000
```

> `AUTH_SECRET` باید مقدار داشته باشد؛ در غیر این صورت لاگین/ثبت‌نام کار نمی‌کند.

---

## ۲. نصب وابستگی‌های Python

از **ریشه پروژه** اجرا کنید:

```powershell
pip install ".[dev]"
```

بررسی نصب (اختیاری):

```powershell
ruff check .
mypy packages services eval
pytest -q
```

---

## ۳. نصب وابستگی‌های Frontend

```powershell
cd apps\web
npm install
cd ..\..
```

---

## ۴. Elasticsearch (فقط Docker)

Elasticsearch باید در Docker در حال اجرا باشد و از طریق پورت میزبان در دسترس باشد.

اگر ES شما روی پورت `19500` است (مطابق `.env`):

```powershell
# فقط Elasticsearch را بالا بیاورید — postgres/redis داخل compose لازم نیست
docker compose -f infra/docker-compose.yml up -d elasticsearch
```

> اگر ES شما کانتینر جداگانه با پورت `19500` است، همان را نگه دارید. در پنل ادمین (`/admin/elasticsearch`) آدرس `http://localhost:19500` را وارد کنید.

بررسی سلامت:

```powershell
curl http://localhost:19500
```

---

## ۵. PostgreSQL 18 — حذف و ساخت مجدد دیتابیس

این مرحله **تمام داده‌های دیتابیس `acip` را پاک می‌کند** و جداول را از نو می‌سازد.

### ۵.۱ حذف دیتابیس و کاربر قبلی

```powershell
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

# قطع اتصال‌های فعال
& $psql -h localhost -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'acip' AND pid <> pg_backend_pid();"

# حذف دیتابیس و نقش
& $psql -h localhost -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS acip;"
& $psql -h localhost -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "DROP ROLE IF EXISTS acip;"
```

### ۵.۲ ساخت دیتابیس و کاربر جدید

```powershell
& $psql -h localhost -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
  "CREATE ROLE acip WITH LOGIN PASSWORD '1234';"
& $psql -h localhost -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
  "CREATE DATABASE acip OWNER acip;"
& $psql -h localhost -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1 -c `
  "GRANT ALL PRIVILEGES ON DATABASE acip TO acip;"
```

### ۵.۳ اجرای migrationها (ساخت جداول)

همه فایل‌های SQL داخل `db/migrations/` به ترتیب نام اجرا می‌شوند:

```powershell
$env:PGPASSWORD = "1234"

Get-ChildItem "db\migrations\*.sql" | Sort-Object Name | ForEach-Object {
    Write-Host "Applying $($_.Name)..."
    & $psql -h localhost -p 5433 -U acip -d acip -v ON_ERROR_STOP=1 -f $_.FullName
}
```

**روش جایگزین با Python** (همان DSN پیش‌فرض `localhost:5433`):

```powershell
$env:PG_DSN = "postgresql://acip:1234@localhost:5433/acip"
python scripts/apply_migrations.py
```

> این اسکریپت روی دیتابیس **خالی** طراحی شده. اگر دیتابیس از قبل migration دارد، ابتدا مرحله ۵.۱ را انجام دهید.

### ۵.۴ بررسی موفقیت

```powershell
& $psql -h localhost -p 5433 -U acip -d acip -c "SELECT version FROM schema_migrations ORDER BY version;"
& $psql -h localhost -p 5433 -U acip -d acip -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
```

باید **۱۸ migration** و **۲۶ جدول** ببینید (مثلاً `tenants`, `users`, `plans`, `api_keys`, ...).

---

## ۵.۵ اجرای Seed (داده‌های پیش‌فرض)

Migrationها خودشان **پلن‌ها** (free/starter/pro/enterprise)، **feature flags** و **pricing_settings** را seed می‌کنند.

برای tenant دمو + ۱۰۰ محصول فارسی در Elasticsearch:

```powershell
# ۱) فایل مترادف‌های فارسی را داخل کانتینر ES کپی کنید (یک‌بار)
docker exec elastic mkdir -p /usr/share/elasticsearch/config/analysis
docker cp infra\elasticsearch\analysis\synonyms_fa.txt elastic:/usr/share/elasticsearch/config/analysis/synonyms_fa.txt

# ۲) seed کاتالوگ (بدون embedding — سریع‌تر، بدون نیاز به مدل)
$env:PYTHONPATH = "packages;services"
$env:PYTHONIOENCODING = "utf-8"
python scripts/seed_catalog.py --no-embeddings
```

خروجی شامل **widget key** و **sync key** است (فقط یک‌بار چاپ می‌شوند — ذخیره کنید).

### ساخت ادمین پلتفرم

```powershell
curl -X POST http://localhost:8000/admin/auth/bootstrap `
  -H "x-admin-token: dev-operator-token-change-me" `
  -H "content-type: application/json" `
  -d '{\"email\":\"admin@vitrin.ai\",\"password\":\"ChangeMe-Str0ng!\",\"full_name\":\"Admin\"}'
```

---

## ۶. Redis

سرویس Redis ویندوز باید روی `localhost:6379` در حال اجرا باشد.

```powershell
# بررسی (اگر redis-cli نصب است)
redis-cli ping
# پاسخ مورد انتظار: PONG
```

> اگر `docker compose` قبلاً Redis روی پورت `6379` بالا آورده، با Redis محلی تداخل دارد. فقط یکی را نگه دارید:

```powershell
docker compose -f infra/docker-compose.yml stop redis postgres
```

---

## ۷. اجرای سیستم

سه پنجره PowerShell جدا باز کنید. همه دستورات از **ریشه پروژه**.

### ترمینال ۱ — API (بک‌اند)

```powershell
cd "C:\Users\AliSehati\Desktop\AI Widget SaaS Platform"
$env:PYTHONPATH = "packages;services"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

بررسی:

```powershell
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

`/readyz` باید وضعیت `postgres`, `redis` و `elasticsearch` را `ok` گزارش کند.

### ترمینال ۲ — Worker (Celery)

```powershell
cd "C:\Users\AliSehati\Desktop\AI Widget SaaS Platform"
.\scripts\start-worker.ps1
```

> روی ویندوز از pool `solo` استفاده می‌شود (محدودیت Celery).

### ترمینال ۳ — Frontend (Next.js)

```powershell
cd "C:\Users\AliSehati\Desktop\AI Widget SaaS Platform\apps\web"
npm run dev
```

---

## ۸. آدرس‌های مهم

| بخش | آدرس |
|---|---|
| سایت / داشبورد فروشگاه | http://localhost:3000 |
| ثبت‌نام / ورود | http://localhost:3000/signup · `/login` |
| داشبورد مالک فروشگاه | http://localhost:3000/dashboard |
| پنل ادمین پلتفرم | http://localhost:3000/admin |
| ورود ادمین | http://localhost:3000/admin/login |
| API + Swagger | http://localhost:8000/docs |
| Elasticsearch (Docker) | http://localhost:19500 |

---

## ۹. ساخت اولین ادمین پلتفرم

بعد از بالا آمدن API:

```powershell
curl -X POST http://localhost:8000/admin/auth/bootstrap `
  -H "x-admin-token: dev-operator-token-change-me" `
  -H "content-type: application/json" `
  -d '{\"email\":\"admin@vitrin.ai\",\"password\":\"ChangeMe-Str0ng!\",\"full_name\":\"Admin\"}'
```

مقدار `x-admin-token` باید با `ADMIN_TOKEN` در `.env` یکی باشد.

سپس در http://localhost:3000/admin/login وارد شوید.

---

## ۱۰. اتصال Elasticsearch از پنل ادمین

1. وارد `/admin` شوید.
2. بخش **Elasticsearch** را باز کنید.
3. آدرس کلاستر را `http://localhost:19500` قرار دهید (مطابق `ES_HOST` در `.env`).
4. تست اتصال را بزنید و در صورت نیاز ایندکس/ویزارد راه‌اندازی را ادامه دهید.

---

## ۱۱. خلاصه دستورات (چک‌لیست سریع)

```powershell
# ریشه پروژه
pip install ".[dev]"
cd apps\web; npm install; cd ..\..

# ریست دیتابیس (مرحله ۵ — فقط وقتی می‌خواهید از صفر شروع کنید)
# ... دستورات بخش ۵ ...

# اجرا
$env:PYTHONPATH = "packages;services"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# ترمینال جدید:
.\scripts\start-worker.ps1
# ترمینال جدید:
cd apps\web; npm run dev
```

---

## عیب‌یابی رایج

| مشکل | راه‌حل |
|---|---|
| `readyz` → postgres unavailable | سرویس `postgresql-x64-18` را چک کنید؛ پورت `5433` و `.env` را بررسی کنید |
| `readyz` → redis unavailable | Redis ویندوز را استارت کنید؛ تداخل با Redis داکر را برطرف کنید |
| `readyz` → elasticsearch unavailable | کانتینر ES را چک کنید؛ `ES_HOST=http://localhost:19500` |
| migration خطای duplicate | دیتابیس خالی نیست — ابتدا بخش ۵.۱ (DROP DATABASE) را اجرا کنید |
| لاگین کار نمی‌کند | `AUTH_SECRET` در `.env` خالی نباشد |
| پورت 6379 اشغال است | `docker compose -f infra/docker-compose.yml stop redis` |

---

*آخرین به‌روزرسانی: توسعه محلی Windows — PostgreSQL 18 بومی + Elasticsearch در Docker*
