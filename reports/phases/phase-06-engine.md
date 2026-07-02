# فاز ۶ — موتور هوشمند: ES + Sync + Inference

**وضعیت: تحویل‌شده — منتظر تأیید شما برای فاز ۷**
تاریخ تحویل: ۱۴۰۵/۰۴/۱۲ · شاخه: `claude/gallant-shannon-8b31td`

## چه چیزی ساخته شد

### ۱) Bootstrap خودکار index + degradation تمیز (503 با کد ثابت)

| قطعه | شرح |
|---|---|
| `services/api/main.py` | هنگام startup، ایندکس کاتالوگ **به‌صورت best-effort** پشت alias ساخته می‌شود (`ensure_catalogue_index`). اگر ES خاموش باشد فقط `es.bootstrap_skipped` لاگ می‌شود و API بدون معطلی بالا می‌آید — هرگز بلاک نمی‌کند |
| `packages/acip_core/config.py` | فلگ جدید `ES_BOOTSTRAP_ON_STARTUP` (پیش‌فرض true) برای محیط‌هایی که چرخهٔ ایندکس فقط از کنسول ادمین مدیریت می‌شود |
| `services/api/routers/v1.py` | `/v1/search` و `/v1/suggest`: ES خاموش → **503 با کد `search_unavailable`** · ایندکس هنوز ساخته‌نشده → **503 با کد `index_not_ready`** · `/v1/chat` و `/v1/chat/stream` → **503 با کد `assistant_unavailable`**. دیگر هیچ 500 خامی به ویجت نمی‌رسد؛ ویجت می‌تواند پیام «چند لحظه دیگر تلاش کنید» نشان دهد |

### ۲) کاتالوگ نمونهٔ فارسی + اسکریپت seed

| قطعه | شرح |
|---|---|
| `tests/fixtures/catalog_fa.json` | **۱۰۰ محصول فارسی واقعی** (`p-001` … `p-100`) در ۱۰ گروه: موبایل و لوازم جانبی، لپ‌تاپ، کفش، تلویزیون، صوتی، ساعت هوشمند، پوشاک، لوازم خانگی، آرایشی، ورزش و کتاب — با برند، دسته‌بندی، ویژگی‌ها، قیمت، موجودی و popularity |
| `scripts/seed_catalog.py` | با یک فرمان: tenant دمو (`demo-fa`) + کلید widget و کلید sync (فقط یک‌بار چاپ می‌شوند) + ایندکس ۱۰۰ محصول از **همان خط لولهٔ واقعی sync** (normalize → embedding اختیاری → upsert ایدمپوتنت → bump نسخهٔ داده). گزینه‌ها: `--dry-run` (فقط اعتبارسنجی، بدون PG/ES) و `--no-embeddings` (فقط lexical؛ بدون نیاز به TEI) |
| `packages/acip_sync/normalize.py` | شکل REST حالا فیلد `popularity` را هم به سند canonical نگاشت می‌کند (rank_feature) |

### ۳) Golden set + KPI eval + groundedness

| قطعه | شرح |
|---|---|
| `eval/golden_set/golden_fa.jsonl` | **۵۰ کوئری فارسی داوری‌شده** (`fa-001` … `fa-050`) با درجهٔ ۱–۳: برند («گوشی سامسونگ»)، مترادف («تی وی ارزان»، «نوت بوک اپل»)، املای متفاوت («لپتاپ گیمینگ»)، ویژگی («تلویزیون ۵۵ اینچ»)، قصد قیمتی، برند لاتین («nike کفش»)، نام مدل («ایرپاد پرو»، «ردمی نوت») و عنوان کتاب — همهٔ شناسه‌های داوری‌شده در fixture موجودند |
| `eval/run_eval.py` | اندازه‌گیری تأخیر هر کوئری + `p95_latency_ms` + فلگ جدید **`--kpi`**: گزارش PASS/FAIL روی هدف‌های headline (NDCG@10 ≥ 0.80 · p95 < 150ms · zero-result < 5%) و exit code=1 در صورت شکست — قابل استفاده به‌عنوان gate در CI |
| `eval/groundedness.py` | KPI چهارم (groundedness ≥ 95%): هر نوبت دستیار **grounded** است اگر یا refuse کند یا پاسخش citation داشته باشد و **تک‌تک محصولات cite‌شده واقعاً در ایندکس همان فروشگاه موجود باشند** (بررسی مستقیم `es.exists`). خروجی JSON + PASS/FAIL هر نوبت |

### ۴) تست‌ها — `tests/integration/test_engine.py`

- **PG-gated (همین‌جا اجرا و پاس شد):** با ES خاموش، `/v1/search` و `/v1/suggest` و `/v1/chat` روی سرور واقعی uvicorn با کلید widget واقعی → **503 با کد ثابت** (نه 500) + بدون کلید → 401
- **ES-gated (روی ویندوز شما اجرا می‌شود):** ۲۰ محصول fixture از خط لولهٔ واقعی وارد ایندکس → «گوشی سامسونگ» باید یکی از گوشی‌های سامسونگ را اول برگرداند + «لپتاپ» (بی‌فاصله) نباید zero-result شود

## نتایج گیت‌ها (محیط توسعهٔ این سشن — Linux، PG واقعی، ES خاموش)

| گیت | نتیجه |
|---|---|
| `pytest` | **۱۳۹ پاس / ۴ skip** (skipها فقط ES-gated) |
| `ruff` + `mypy` | تمیز (۹۸ فایل) |
| `seed_catalog.py --dry-run` | «dry-run OK: 100 products validated» |
| startup با ES خاموش | API بالا آمد + فقط `es.bootstrap_skipped` در لاگ |
| `run_eval --kpi` (بدون ES) | گزارش KPI تولید شد؛ NDCG=0 و zero-result=1 با provider خالی → FAIL و exit 1 (رفتار درستِ gate) |
| فرانت‌اند | در این فاز هیچ فایل فرانت تغییری نکرد — گیت‌های فاز ۵ معتبرند |

> **صادقانه:** در این محیط ES در دسترس نیست (قانون پروژه: تست ES فقط سمت شما). بنابراین **اعداد نهایی KPI باید روی ویندوز شما با ES روشن ثبت شوند** — دستورهایش پایین آمده و خروجی `--kpi` مستقیم PASS/FAIL هر هدف را چاپ می‌کند.

## چک‌لیست پذیرش فاز ۶ (از پلن)

- [x] bootstrap خودکار index + graceful degradation (503 با کد واضح) — تست خودکار + تأیید زنده
- [x] `scripts/seed_catalog.py` — ۱۰۰ محصول فارسی + tenant دمو + api_key
- [x] bulk sync نمونه + fixture (`tests/fixtures/catalog_fa.json` + تست ingest)
- [x] golden set ۵۰ کوئری + KPI runner (`--kpi`) + groundedness runner
- [ ] ثبت اعداد KPI روی ES زنده (سمت شما — دستورها پایین) و پاسخ واقعی `/v1/search` + `/v1/chat` روی localhost
- [x] گزارش: همین فایل

## دستورات تست روی ویندوز (محیط شما — PG:5433 · ES:19500 · Redis)

```powershell
cd C:\...\AI-Widget-SaaS-Platform
$env:PYTHONPATH = "packages;services"

# ۰) پیش‌نیاز: ES داکر روشن (پورت 19500) + PG + Redis + API (پورت 8000)
#    نکته: با ES روشن، خود API هنگام start ایندکس را می‌سازد (لاگ es.bootstrap)

# ۱) seed کاتالوگ دمو — ۱۰۰ محصول + tenant + کلیدها (کلیدها فقط یک‌بار چاپ می‌شوند!)
python scripts/seed_catalog.py --no-embeddings
#    (اگر سرویس embedding/TEI دارید، بدون --no-embeddings اجرا کنید تا kNN هم فعال شود)
#    خروجی: tenant id + widget key + sync key + یک فرمان curl آماده

# ۲) جست‌وجوی واقعی روی localhost (کلید widget چاپ‌شده را جایگزین کنید)
curl.exe -s http://localhost:8000/v1/search -H "x-api-key: WIDGET_KEY" -H "content-type: application/json" -d "{\"query\": \"گوشی سامسونگ\"}"
curl.exe -s "http://localhost:8000/v1/suggest?q=گوشی" -H "x-api-key: WIDGET_KEY"

# ۳) دستیار واقعی
curl.exe -s http://localhost:8000/v1/chat -H "x-api-key: WIDGET_KEY" -H "content-type: application/json" -d "{\"message\": \"یک گوشی سامسونگ ارزان می‌خواهم\"}"

# ۴) KPIهای جست‌وجو روی golden set (tenant id مرحلهٔ ۱ را جایگزین کنید)
python -m eval.run_eval --golden eval/golden_set/golden_fa.jsonl --tenant TENANT_ID --kpi
#    → سه سطر PASS/FAIL برای NDCG@10 ≥ 0.80 · p95 < 150ms · zero-result < 5%

# ۵) KPI groundedness دستیار (۲۰ نوبت اول golden set)
python -m eval.groundedness --tenant TENANT_ID --limit 20
#    → groundedness باید ≥ 0.95 باشد (exit 1 اگر کمتر)

# ۶) تست‌های خودکار ES-gated
python -m pytest tests/integration/test_engine.py tests/integration/test_search_es.py -q

# ۷) تست degradation: داکر ES را خاموش کنید و دوباره جست‌وجو بزنید
#    → باید 503 با {"error":{"code":"search_unavailable"}} بگیرید، نه 500
```

> اگر NDCG کمتر از هدف شد: اول بدون `--no-embeddings` (با TEI) تکرار کنید؛ سپس مترادف‌های فروشگاه را از کنسول ادمین (Synonyms) اضافه کنید و دوباره eval بگیرید — همین چرخه، فرایند رسمی tuning است.

## فایل‌های تغییر یافته / جدید

| فایل | نوع |
|---|---|
| `services/api/main.py` · `services/api/routers/v1.py` · `packages/acip_core/config.py` · `packages/acip_sync/normalize.py` · `eval/run_eval.py` | تغییر |
| `scripts/seed_catalog.py` · `tests/fixtures/catalog_fa.json` · `eval/golden_set/golden_fa.jsonl` · `eval/groundedness.py` · `tests/integration/test_engine.py` | جدید |
