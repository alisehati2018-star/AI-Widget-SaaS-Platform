# راهنمای یکپارچه‌سازی فروشگاه با ویترین (OpenCart 3 / WooCommerce)

اتصال فروشگاه دو مسیر مکمل دارد که با هم صحت داده را تضمین می‌کنند:

| مسیر | جهت | چه زمانی |
|---|---|---|
| **Push (webhook + bulk)** | فروشگاه → ویترین | لحظه‌ای — با هر افزودن/ویرایش/حذف محصول، افزونه همان محصول را می‌فرستد |
| **Pull (همگام‌سازی دلتا)** | ویترین → فروشگاه | هر ۱۵ دقیقه — ویترین خودش محصولات تغییرکرده از آخرین watermark را می‌کشد؛ حتی اگر webhookای گم شود ایندکس همگرا می‌ماند |

---

## ۱) OpenCart 3

### نصب افزونه
1. پوشهٔ `integrations/opencart3` را فشرده کنید (فایل `install.xml` + پوشهٔ `upload`) و از **Extensions → Installer** آپلود کنید.
2. از **Extensions → Extensions → Modules** ماژول **ACIP** را Install و سپس Edit کنید.

### تنظیمات ماژول
| فیلد | مقدار |
|---|---|
| وضعیت | فعال |
| آدرس API | آدرس سرور ویترین (مثلاً `http://localhost:8000`) |
| کلید ویجت | از داشبورد ویترین → کلیدها → نوع widget |
| کلید همگام‌سازی | از داشبورد ویترین → کلیدها → نوع sync |
| **توکن خروجی** | یک رشتهٔ تصادفی طولانی بسازید (مثلاً خروجی `openssl rand -hex 24`) |
| جایگزینی جست‌وجو / نمایش ویجت | دلخواه |

3. دکمهٔ **«آزمایش اتصال»** را بزنید (باید سبز شود) و سپس **«ورود کامل کاتالوگ اکنون»** برای backfill اولیه.

### اتصال pull (دلتا)
در داشبورد ویترین → **تنظیمات → اتصال فروشگاه**: پلتفرم OpenCart، آدرس فروشگاه، و **همان توکن خروجی** را وارد و ذخیره کنید. از این پس worker ویترین هر ۱۵ دقیقه endpoint زیر را می‌خواند:

```
GET {store}/index.php?route=extension/module/acip/export&since=...&page=N&limit=100
Header: X-Acip-Token: <توکن>
```

پاسخ: `{"products": [...], "more": true|false}` — محصولات تغییرکرده بعد از watermark، قدیمی‌ترین اول. توکن اشتباه → 403.

### رویدادهای push
افزونه روی `addProduct/editProduct/deleteProduct` رویداد ثبت می‌کند و به `/v1/sync/webhook?source=opencart` می‌فرستد (حذف → tombstone).

---

## ۲) WooCommerce (وردپرس)

### نصب افزونه
1. پوشهٔ `integrations/wordpress/acip-search` را zip کنید و از **افزونه‌ها → افزودن → بارگذاری** نصب و فعال کنید.
2. در برگهٔ تنظیمات افزونه: آدرس API، کلید widget و کلید sync را وارد کنید؛ **Test connection** و سپس **Bulk import**.

### اتصال pull (دلتا)
1. در وردپرس: **WooCommerce → Settings → Advanced → REST API → Add key** با دسترسی **Read** — یک `consumer_key` (ck_...) و `consumer_secret` (cs_...) می‌گیرید.
2. در داشبورد ویترین → **تنظیمات → اتصال فروشگاه**: پلتفرم WooCommerce، آدرس سایت، و همین دو مقدار را ذخیره کنید.

ویترین هر ۱۵ دقیقه می‌خواند:

```
GET {store}/wp-json/wc/v3/products?modified_after=<watermark>&dates_are_gmt=true&orderby=modified&order=asc&per_page=100&page=N
```

روی HTTPS اعتبارنامه‌ها با Basic Auth و روی HTTP محلی به‌صورت query param ارسال می‌شوند (قاعدهٔ خود WooCommerce).

### رویدادهای push
افزونه روی هوک‌های `woocommerce_update_product` / `new_product` / حذف، محصول را به `/v1/sync/webhook?source=woocommerce` می‌فرستد.

---

## ۳) چرخهٔ همگام‌سازی دلتا — چطور کار می‌کند

1. worker (beat هر ۱۵ دقیقه، یا دکمهٔ «همگام‌سازی الان» داشبورد) برای هر فروشگاه متصل `reconcile` اجرا می‌کند.
2. آخرین `high_watermark` از جدول `sync_state` خوانده می‌شود؛ فقط محصولات جدیدتر از آن کشیده می‌شوند.
3. هر محصول از **همان خط لولهٔ webhook** می‌گذرد: normalize → embedding (اختیاری) → upsert ایدمپوتنت با external version — پس تکرار یا بی‌ترتیبی هرگز ایندکس را خراب نمی‌کند.
4. اگر چیزی تعمیر شد، نسخهٔ دادهٔ tenant عوض می‌شود (کش‌ها باطل) و watermark جدید ثبت می‌شود.
5. خطای فروشگاه/شبکه در `sync_state.last_status = error` ثبت می‌شود و در داشبورد (کاتالوگ) دیده می‌شود — هیچ‌وقت beat را نمی‌شکند.

نکتهٔ منطقهٔ زمانی: برای OpenCart، watermark با همان ساعتِ دیواریِ خود فروشگاه رفت‌وبرگشت می‌شود (بدون offset) و برای WooCommerce مقایسه در GMT انجام می‌شود (`dates_are_gmt=true`) — پس فروشگاه‌های با ساعت ایران محصولی را از دست نمی‌دهند.

---

## ۴) pilot محلی بدون نصب PHP (شبیه‌ساز)

اگر می‌خواهید حلقهٔ کامل را بدون نصب OpenCart/وردپرس ببینید:

```powershell
cd C:\...\AI-Widget-SaaS-Platform
$env:PYTHONPATH = "packages;services"

# ۱) فروشگاه شبیه‌سازی‌شده با ۸ محصول فارسی (Woo + OpenCart همزمان)
python scripts/pilot_store.py --port 9099
#    Woo:      ck_pilot / cs_pilot        OpenCart: pilot-token

# ۲) در داشبورد ویترین → تنظیمات → اتصال فروشگاه:
#    پلتفرم: WooCommerce · آدرس: http://127.0.0.1:9099
#    consumer key: ck_pilot · consumer secret: cs_pilot → ذخیره

# ۳) داشبورد → کاتالوگ → «همگام‌سازی الان» (worker باید روشن باشد)
#    → ۸ محصول ایندکس می‌شود؛ سپس در صفحهٔ «تنظیم جست‌وجو» عبارت «گوشی سامسونگ» را تست کنید

# ۴) دلتای واقعی: یک محصول را در فروشگاه «ویرایش» کنید و دوباره sync بزنید
curl.exe -X POST http://127.0.0.1:9099/touch/4
#    → اجرای بعدی فقط همان ۱ محصول را می‌کشد (در لاگ worker: repaired=1)

# ۵) تست‌های خودکار همین حلقه
python -m pytest tests/integration/test_integrations.py -q
```

## ۵) عیب‌یابی

| علامت | علت رایج | راه‌حل |
|---|---|---|
| `last_status = error` در کاتالوگ | آدرس/توکن/کلید اشتباه، فروشگاه خاموش | «آزمایش اتصال» در افزونه؛ توکن خروجی دو طرف یکسان باشد |
| sync همیشه 0 محصول | watermark جلوتر از تغییرات است | طبیعی است — فقط تغییرات جدید کشیده می‌شوند؛ برای backfill کامل از دکمهٔ bulk افزونه استفاده کنید |
| Woo روی HTTP خطای 401 | Basic Auth روی HTTP پذیرفته نمی‌شود | ویترین خودش روی HTTP اعتبارنامه را query param می‌فرستد؛ کلید را با دسترسی Read بسازید |
| محصولات فارسی ناقص | زبان پیش‌فرض فروشگاه | ماژول از `config_language_id` فروشگاه می‌خواند؛ زبان فارسی را پیش‌فرض کنید |
