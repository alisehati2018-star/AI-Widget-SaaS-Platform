# فاز ۳ — ادمین: Observability و امنیت

**وضعیت: تحویل‌شده — منتظر تأیید شما برای فاز ۴**
تاریخ تحویل: ۱۴۰۵/۰۴/۱۱ · شاخه: `claude/gallant-shannon-8b31td`

## چه چیزی ساخته شد

### Backend

| Endpoint | شرح |
|---|---|
| `GET /admin/audit` (گسترش) | فیلتر actor / پیشوند action / فروشگاه / بازهٔ تاریخ + **cursor** keyset برای صفحات بعدی + `fmt=csv` برای خروجی CSV (تا ۱۰هزار ردیف با همان فیلتر) |
| `GET /admin/usage` (گسترش) | فیلتر فروشگاه / مسیر / پله (rung) / بازهٔ ۷–۳۶۶ روز؛ جمع‌ها و توزیع پله **روی همان فیلتر**؛ فهرست ۵۰ رویداد اخیر؛ `fmt=csv` |
| `GET /admin/queue` (گسترش) | علاوه بر broker و عمق صف: **بازرسی زندهٔ Celery** — workerهای آنلاین، تعداد وظایف در حال اجرا و وظیفه‌های ثبت‌شده. عمق صف حالا از دیتابیس Redisِ خود broker خوانده می‌شود (قبلاً DB اشتباه را می‌خواند) |
| `GET /admin/security` (گسترش) | حساب‌های قفل هر **دو صفحهٔ هویتی** (مشتری + ادمین) با برچسب plane؛ رویدادهای auth هر دو صفحه |
| `POST /admin/security/unlock` (جدید) | بازکردن دستی قفل (صفرکردن شمارنده + حذف locked_until) برای customer یا admin + audit |
| `GET /admin/analytics` · `/insight` · `/zero-results` · `POST /analyst` | **پرچم degraded به‌جای 500**: اگر Elasticsearch در دسترس نباشد پاسخ 200 با دادهٔ خالی و `degraded: true` برمی‌گردد |
| `GET /admin/health` (گسترش) | تأخیر هر وابستگی (میلی‌ثانیه) + تاریخچهٔ غلتان ۹۶ نمونه در Redis برای sparkline |
| `POST /admin/models/ping` (جدید) | تست دسترسی سرویس‌های inference (embeddings/reranker/LLM) با تأخیر |

### Frontend

| صفحه | تغییر |
|---|---|
| **گزارش حسابرسی** | نوار فیلتر (بازیگر/پیشوند عملیات/فروشگاه/از–تا تاریخ، debounce) + ستون فروشگاه + دکمهٔ «موارد قدیمی‌تر» (cursor) + خروجی CSV |
| **مصرف** | نوار فیلتر (فروشگاه/مسیر/پله/بازهٔ ۷/۳۰/۹۰ روز) + جدول رویدادهای اخیر (زمان/فروشگاه/مسیر/پله/تأخیر/هزینه) + خروجی CSV + کارت‌های جمع روی فیلتر فعلی |
| **صف** | جدول Workerهای آنلاین (وضعیت/وظایف در حال اجرا) + فهرست وظیفه‌های ثبت‌شده + شمارندهٔ workerها؛ تازه‌سازی هر ۱۰ ثانیه |
| **امنیت** | ستون «نوع حساب» (ادمین/مشتری) + دکمهٔ **بازکردن قفل** برای هر حساب قفل‌شده |
| **مدل‌ها** | دکمهٔ «تست دسترسی مدل‌ها» → نشان در دسترس/خارج از دسترس + تأخیر برای هر سرویس |
| **سلامت سامانه** | ستون تأخیر برای هر وابستگی + **sparkline روند تأخیر PG** (همان کامپوننت نمودار فاز ۱ با tooltip) |
| **تحلیل** | بنر هشدار degraded وقتی ES خاموش است (به‌جای صفحهٔ شکسته) + نشان «قالب/LLM» برای پاسخ تحلیلگر + پیام degraded تحلیلگر |

### اسکریپت و مستندات
- `scripts/start-worker.ps1` — اجرای worker روی ویندوز (خودکار `--pool solo` که تنها حالت سازگار ویندوز است + سوییچ `-WithBeat` برای زمان‌بند)
- `docs/INSTALL-fa.md` — راهنمای کامل نصب فارسی روی ویندوز (PG:5433، ES داکری :19500، Redis، مهاجرت‌ها، API، worker، داشبورد، ساخت ادمین اول، تست سلامت)

### تست‌ها
- `tests/integration/test_admin_observability.py` — ۷ تست end-to-end روی PG واقعی:
  فیلترهای audit (فروشگاه/عملیات/بازیگر/تاریخ + رد تاریخ خراب + cursor) · فیلترهای usage + خروجی CSV (هدر download + محتوای فیلترشده) · شکل پاسخ queue · **قفل ادمین → نمایش در صفحهٔ امنیت با plane → unlock → ورود موفق فوری** + خطاهای تمیز · degraded (۲۰۰ نه ۵۰۰) برای analytics/insight/zero-results/analyst و در حالت ES خاموش `degraded=true` با دادهٔ خالی · تأخیر + تاریخچهٔ health · شکل پاسخ models/ping

## نتایج گیت‌ها (محیط توسعهٔ این سشن — Linux، PG واقعی، ES خاموش، worker واقعی)

| گیت | نتیجه |
|---|---|
| `pytest` (کل مجموعه + integration روی PG) | **۱۳۵ پاس / ۳ skip** (فقط ES) |
| `ruff` + `mypy` | تمیز (۸۹ فایل) |
| `tsc --noEmit` + `npm run check:all` | صفر خطا/هشدار |
| `next build` | موفق — ۱۰۳ صفحه |
| functional-check / responsive-check | ۰ خطا / ۰ سرریز |
| تأیید زندهٔ مرورگر (۱۵ چک Playwright) | فیلتر و CSV حسابرسی → فیلترهای مصرف (پله/فروشگاه) و CSV → **worker واقعی آنلاین در صفحهٔ صف** → قفل ادمین + بازکردن قفل از UI → ping مدل‌ها → sparkline سلامت → **بنر degraded تحلیل با ES خاموش** و پاسخ تحلیلگر بدون crash |

## چک‌لیست پذیرش فاز ۳ (از پلن)

- [x] ES خاموش → degraded نه crash (تست خودکار + تأیید زندهٔ UI)
- [x] audit با فیلتر tenant (تست خودکار + تأیید زندهٔ UI)
- [x] worker در صفحهٔ queue (Celery واقعی با `--pool solo` اجرا و در UI آنلاین دیده شد)
- [x] گزارش: همین فایل
- [ ] **تأیید شما برای شروع فاز ۴**

## دستورات تست روی ویندوز (محیط شما)

```powershell
# 1) اجرای worker (ترمینال جدا) — صفحهٔ ادمین → صف باید آن را آنلاین نشان دهد
.\scripts\start-worker.ps1 -WithBeat

# 2) تست‌های خودکار فاز ۳
$env:PYTHONPATH = "packages;services"
python -m pytest tests/integration/test_admin_observability.py -v

# 3) تست دستی UI → http://localhost:3000/admin
#    حسابرسی: فیلتر فروشگاه/عملیات/تاریخ → «موارد قدیمی‌تر» → خروجی CSV
#    مصرف: فیلتر پله/مسیر/فروشگاه → خروجی CSV
#    صف: worker آنلاین + وظیفه‌های ثبت‌شده
#    امنیت: یک حساب را با چند ورود ناموفق قفل کنید → دکمهٔ «بازکردن قفل»
#    مدل‌ها: «تست دسترسی مدل‌ها»
#    سلامت: چند ثانیه بمانید تا sparkline تأخیر PG شکل بگیرد
#    تحلیل: ES را خاموش کنید → بنر degraded به‌جای خطا؛ روشن کنید → دادهٔ واقعی

# 4) راهنمای کامل نصب: docs/INSTALL-fa.md
```

## فایل‌های تغییر
`services/api/routers/admin.py` · `scripts/start-worker.ps1` (جدید) ·
`docs/INSTALL-fa.md` (جدید) ·
`apps/web/app/[locale]/admin/{audit,usage,queue,security,models,health,analytics}/page.tsx` ·
`apps/web/lib/datetime.ts` (+formatTime) · `apps/web/app/globals.css` (+alert-warning) ·
`messages/{fa,en}/admin.json` · `tests/integration/test_admin_observability.py` (جدید) ·
`docs/vitrin-completion-roadmap.md` (نسخهٔ تیک‌خورده)
