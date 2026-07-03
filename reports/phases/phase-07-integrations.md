# فاز ۷ — یکپارچه‌سازی فروشگاه (OpenCart / WooCommerce)

**وضعیت: تحویل‌شده — منتظر تأیید شما برای فاز ۸**
تاریخ تحویل: ۱۴۰۵/۰۴/۱۲ · شاخه: `claude/gallant-shannon-8b31td`

## چه چیزی ساخته شد

### ۱) همگام‌سازی دلتا (pull) — دیگر no-op نیست

تا قبل از این فاز، `reconcile_tenant` فقط اجرای خودش را در `sync_state` ثبت می‌کرد و از فروشگاه چیزی نمی‌کشید؛ حتی beat دوره‌ای (`__all__`) به‌خاطر cast uuid بی‌صدا شکست می‌خورد. حالا:

| قطعه | شرح |
|---|---|
| `packages/acip_sync/fetch.py` (جدید) | دو کلاینت pull واقعی: **WooCommerce** از REST API استاندارد (`/wp-json/wc/v3/products` با `modified_after` + `dates_are_gmt=true`، صفحه‌بندی، Basic Auth روی HTTPS / query param روی HTTP طبق قاعدهٔ خود Woo) و **OpenCart** از endpoint خروجی ماژول ACIP (هدر `X-Acip-Token`، صفحه‌بندی با پرچم `more`). `fetch_changed_since(source, settings, since)` بر اساس تنظیمات tenant تصمیم می‌گیرد چیزی برای کشیدن هست یا نه |
| `services/worker/tasks.py` | `reconcile_tenant` واقعی: خواندن تنظیمات فروشگاه + watermark از PG → pull تغییرات → عبور از **همان خط لولهٔ webhook** (normalize → embedding → upsert ایدمپوتنت) → bump نسخهٔ داده → ثبت watermark و وضعیت در `sync_state`. حالت `__all__` (beat هر ۱۵ دقیقه) همهٔ tenantهای active با فروشگاه متصل را جارو می‌کند؛ خطای هر فروشگاه فقط در `sync_state` ثبت می‌شود و beat را نمی‌شکند |
| `packages/acip_sync/reconcile.py` | embedding تعمیرها حالا از `embedding_text()` کامل (برند + دسته + ویژگی‌ها) استفاده می‌کند — همان قاعدهٔ فاز ۶، تا repair کیفیت معنایی را پایین نیاورد |
| نکتهٔ منطقهٔ زمانی | watermark برای OpenCart با ساعت دیواری خود فروشگاه (بدون offset) رفت‌وبرگشت می‌شود و برای Woo مقایسه در GMT — فروشگاه‌های ایران (UTC+3:30) محصولی را از دست نمی‌دهند |

### ۲) ماژول OpenCart 3 — endpoint خروجی + توکن

- `catalog/controller/.../acip.php`: اکشن جدید **`export`** — صفحه‌بندی‌شده، فیلتر `since` روی `date_modified`، محافظت با `hash_equals` روی هدر `X-Acip-Token`؛ خروجی همان شکل canonical مسیر webhook/bulk (نام/توضیح/برند/دسته‌ها/ویژگی‌ها/قیمت/موجودی)
- تنظیم جدید **«توکن خروجی»** در فرم ادمین ماژول (کنترلر + twig + زبان en/fa) — ادمین فروشگاه یک رشتهٔ تصادفی می‌سازد و همان را در داشبورد ویترین هم وارد می‌کند
- هر ۴ فایل PHP تغییر یافته با `php -l` بدون خطا

### ۳) داشبورد — ویزارد اتصال با اعتبارنامه‌های pull

گام ۱ ویزارد (تنظیمات → اتصال فروشگاه) حالا بسته به پلتفرم، فیلد اعتبارنامه دارد:
- WooCommerce: **consumer key / consumer secret** (با راهنمای ساخت کلید Read در خود Woo)
- OpenCart: **توکن خروجی** (همان مقدار ماژول)

ذخیره از همان `PATCH /tenant/settings` (allowlist سرور با ۳ کلید جدید گسترش یافت) + i18n کامل fa/en.

### ۴) شبیه‌ساز فروشگاه pilot — `scripts/pilot_store.py`

یک «فروشگاه» محلی کوچک با ۸ محصول فارسی که **هر دو قرارداد** را همزمان پیاده می‌کند (Woo REST + خروجی ماژول OpenCart) + endpoint «ویرایش محصول» (`POST /touch/{id}`) برای دیدن دلتای واقعی. هم تست‌های خودکار از آن استفاده می‌کنند و هم شما می‌توانید بدون نصب PHP کل حلقه را روی ویندوز ببینید.

### ۵) تست‌ها

- `tests/test_sync_fetch.py` (hermetic، ۷ تست): صفحه‌بندی Woo تا صفحهٔ کوتاه، `modified_after`+`dates_are_gmt`، جای اعتبارنامه (query روی HTTP / Basic روی HTTPS)، صفحه‌بندی OpenCart با `more` + هدر توکن + since بدون offset، خطای 403، dispatch تنظیمات ناقص، reconcile با متن embedding کامل و watermark، و بقای reconcile با TEI خاموش
- `tests/integration/test_integrations.py` (PG-gated، ۴ تست، **همین‌جا پاس شد**): حلقهٔ کامل Woo (backfill ۸ محصول → اجرای دوم ۰ → touch یک محصول → دلتای فقط ۱)، قرارداد خروجی OpenCart + توکن اشتباه → `error` ثبت می‌شود نه crash، جاروی `__all__`، و heartbeat فروشگاهِ متصل‌نشده

## نتایج گیت‌ها (این سشن — Linux، PG واقعی، شبیه‌ساز pilot واقعی، ES خاموش)

| گیت | نتیجه |
|---|---|
| `pytest` | **۱۵۰ پاس / ۴ skip** (فقط ES-gated) |
| `ruff` + `mypy` | تمیز (۱۰۰ فایل) |
| `php -l` | ۴ فایل ماژول بدون خطا |
| `tsc --noEmit` + `check:all` | صفر خطا (i18n/hardcoded/size/routes/assets/dead) |
| `next build` | موفق |
| **پذیرش pull زنده** | فروشگاه شبیه‌سازی‌شده در subprocess واقعی: **۸ محصول فارسی backfill → watermark ثبت → ویرایش محصول ۴ → sync بعدی فقط همان ۱ محصول** — از مسیر واقعی worker |

## چک‌لیست پذیرش فاز ۷ (از پلن)

- [x] OpenCart 3 pilot: test connection + bulk + webhook (افزونهٔ کامل از قبل؛ این فاز endpoint خروجی + توکن اضافه شد) — نصب روی فروشگاه واقعی محلی سمت شما، راهنما در `docs/integrations-fa.md`
- [x] WooCommerce pilot (افزونهٔ کامل + pull با REST API خود Woo)
- [x] Delta reconciliation — hook دیگر no-op نیست (pull واقعی + watermark + جاروی beat)
- [x] `docs/integrations-fa.md`
- [x] پذیرش: فروشگاه pilot → sync → جست‌وجو (حلقهٔ pull با شبیه‌ساز اینجا تأیید شد؛ جست‌وجوی ویجت روی ES زندهٔ شما — دستورها پایین)
- [x] گزارش: همین فایل

## دستورات تست روی ویندوز (محیط شما — PG:5433 · ES:19500 · Redis · worker روشن)

```powershell
cd C:\...\AI-Widget-SaaS-Platform
$env:PYTHONPATH = "packages;services"

# ۱) تست‌های خودکار فاز (بدون نیاز به ES)
python -m pytest tests/test_sync_fetch.py tests/integration/test_integrations.py -q

# ۲) pilot کامل با شبیه‌ساز (حلقهٔ واقعی sync → جست‌وجو)
python scripts/pilot_store.py --port 9099
#   داشبورد → تنظیمات → اتصال فروشگاه:
#   پلتفرم WooCommerce · آدرس http://127.0.0.1:9099 · ck_pilot / cs_pilot → ذخیره
#   داشبورد → کاتالوگ → «همگام‌سازی الان» → ۸ محصول ایندکس می‌شود (worker روشن باشد)
#   داشبورد → تنظیم جست‌وجو → «گوشی سامسونگ» را تست کنید → نتیجهٔ واقعی از ES

# ۳) دلتا: ویرایش یک محصول در «فروشگاه» و sync دوباره
curl.exe -X POST http://127.0.0.1:9099/touch/4
#   → «همگام‌سازی الان» → لاگ worker: repaired=1 (فقط همان محصول)

# ۴) pilot با فروشگاه واقعی (OpenCart 3 یا WooCommerce محلی):
#   docs/integrations-fa.md را دنبال کنید — نصب افزونه، Test connection، Bulk import،
#   توکن/کلیدهای pull در ویزارد، و تماشای sync دوره‌ای هر ۱۵ دقیقه
```

## فایل‌های تغییر یافته / جدید

| فایل | نوع |
|---|---|
| `packages/acip_sync/fetch.py` · `scripts/pilot_store.py` · `tests/test_sync_fetch.py` · `tests/integration/test_integrations.py` · `docs/integrations-fa.md` | جدید |
| `services/worker/tasks.py` · `packages/acip_sync/{__init__,reconcile}.py` · `services/api/routers/tenant.py` · ماژول OpenCart (۵ فایل) · `connect-wizard.tsx` · `messages/{fa,en}/dashboard.json` | تغییر |
