# راهنمای نصب و راه‌اندازی Vitrin روی ویندوز (محیط توسعه)

این راهنما همان محیطی را راه‌اندازی می‌کند که تست‌های فازهای تکمیل روی آن انجام می‌شود:
PostgreSQL روی پورت **۵۴۳۳**، Elasticsearch داکری روی **۱۹۵۰۰**، Redis به‌عنوان سرویس ویندوز.

## پیش‌نیازها

| نرم‌افزار | نسخه | نکته |
|---|---|---|
| Python | 3.11+ | همراه pip |
| Node.js | 20+ | برای داشبورد Next.js |
| PostgreSQL | 16+ | این راهنما پورت ۵۴۳۳ را فرض می‌کند |
| Redis | 7+ | سرویس ویندوز یا Memurai |
| Docker Desktop | آخرین | فقط برای Elasticsearch |

## ۱) پایگاه‌داده و سرویس‌ها

```powershell
# Elasticsearch (داکر، پورت 19500)
docker run -d --name vitrin-es -p 19500:9200 `
  -e discovery.type=single-node -e xpack.security.enabled=false `
  docker.elastic.co/elasticsearch/elasticsearch:9.2.0

# دیتابیس و کاربر (psql -p 5433 -U postgres)
CREATE USER acip WITH PASSWORD '<رمز>';
CREATE DATABASE acip OWNER acip;
```

## ۲) تنظیمات (.env در ریشهٔ مخزن)

```ini
PG_HOST=localhost
PG_PORT=5433
PG_USER=acip
PG_PASSWORD=<رمز>
PG_DB=acip
REDIS_URL=redis://localhost:6379/0
ES_HOST=http://localhost:19500
ADMIN_TOKEN=<توکن-عملیاتی-قوی>
AUTH_SECRET=<حداقل ۳۲ نویسهٔ تصادفی>
EMAIL_PROVIDER=console
BILLING_PROVIDER=manual
```

## ۳) نصب وابستگی‌ها و مهاجرت‌ها

```powershell
pip install -e .
python scripts/apply_migrations.py       # همهٔ 0001 تا 0013 را اعمال می‌کند

cd apps/web
npm install
```

## ۴) اجرای سرویس‌ها (هر کدام در یک ترمینال)

```powershell
# API (ترمینال ۱)
$env:PYTHONPATH = "packages;services"
python -m uvicorn api.main:app --port 8000

# Worker پس‌زمینه + زمان‌بند (ترمینال ۲)
.\scripts\start-worker.ps1 -WithBeat

# داشبورد (ترمینال ۳)
cd apps/web
npm run build
npm run start        # http://localhost:3000
```

نکتهٔ worker: در ویندوز pool پیش‌فرض Celery کار نمی‌کند؛ اسکریپت `start-worker.ps1`
به‌صورت خودکار از `--pool solo` استفاده می‌کند (حالت تک‌پردازه برای توسعه).
پس از اجرا، صفحهٔ **ادمین → صف** باید worker را آنلاین نشان دهد.

## ۵) ساخت اولین ادمین

```powershell
curl -X POST http://localhost:8000/admin/auth/bootstrap `
  -H "x-admin-token: <ADMIN_TOKEN>" -H "content-type: application/json" `
  -d '{\"email\":\"admin@example.com\",\"password\":\"<رمز-قوی>\",\"full_name\":\"مدیر\"}'
```

سپس در `http://localhost:3000/admin/login` وارد شوید. ادمین‌های بعدی را از
صفحهٔ **اپراتورها** بسازید — دیگر به توکن نیاز نیست.

## ۶) تست سلامت

```powershell
curl http://localhost:8000/healthz                    # {"status":"ok"}
python -m pytest tests/integration -q                 # تست‌های یکپارچه روی PG
```

در داشبورد ادمین: صفحهٔ **سلامت سامانه** باید PG/Redis/ES را سبز نشان دهد
(اگر ES خاموش باشد، صفحات تحلیل به‌جای خطا حالت «degraded» می‌گیرند)،
و صفحهٔ **صف** باید broker و workerهای آنلاین را فهرست کند.
