# فاز ۲ — ادمین: Revenue, Plans, Users و Inbox

**وضعیت: تحویل‌شده — منتظر تأیید شما برای فاز ۳**
تاریخ تحویل: ۱۴۰۵/۰۴/۱۰ · شاخه: `claude/gallant-shannon-8b31td`

## چه چیزی ساخته شد

### Backend — endpointهای جدید/گسترش‌یافته

| Endpoint | شرح |
|---|---|
| `POST /admin/plans` | ساخت پلن جدید (کد یکتا + اعتبارسنجی کامل؛ کد تکراری → 409) |
| `DELETE /admin/plans/{id}` | حذف پلن استفاده‌نشده؛ اگر tenant/اشتراک/سفارشی به آن اشاره کند → 409 با شمارش مراجع («به‌جای حذف، مخفی کنید») |
| `GET /admin/invoices` | فاکتورهای کل پلتفرم: جست‌وجوی فروشگاه + فیلتر paid/void + صفحه‌بندی + **خلاصهٔ درآمد روی همان فیلتر** (مبلغ/تعداد پرداخت‌شده) |
| `GET /admin/contact` | inbox پیام‌های فرم تماس عمومی: فیلتر وضعیت (new/read/resolved) + جست‌وجوی نام/ایمیل + شمارش هر وضعیت + صفحه‌بندی |
| `PATCH /admin/contact/{id}` | تغییر وضعیت + یادداشت پیگیری داخلی (migration `0013`) |
| `GET/POST /admin/operators` | فهرست/افزودن ادمین پلتفرم (جدول جدا از کاربران فروشگاه) — **بدون نیاز به bootstrap token** |
| `PATCH /admin/operators/{id}` | ویرایش نام |
| `POST /admin/operators/{id}/status` | تعلیق/فعال‌سازی — تعلیق، نشست‌های زنده را هم بلافاصله باطل می‌کند |
| `DELETE /admin/operators/{id}` | حذف اپراتور |
| `GET /admin/users` (گسترش) | جست‌وجوی ایمیل/نام/فروشگاه + فیلتر role/status + صفحه‌بندی سرور |

**قوانین ایمنی اپراتورها (در تراکنش DB):** هیچ ادمینی نمی‌تواند خودش را معلق یا حذف کند؛ آخرین ادمینِ فعال هرگز قابل تعلیق/حذف نیست.

**اصلاح جانبی:** مسیر قدیمی «ارتقای کاربر فروشگاه به platform_admin» در `/admin/users/{email}/role` حذف شد — بعد از جداسازی کامل دو صفحهٔ هویتی (migration 0011، `users.tenant_id NOT NULL`) آن مسیر به خطای دیتابیس می‌خورد؛ حالا نقش فقط بین `store_owner`/`store_staff` جابه‌جا می‌شود و ادمین‌ها فقط از `/admin/operators` ساخته می‌شوند.

### Frontend

| صفحه | تغییر |
|---|---|
| **Plans** | دکمهٔ «پلن جدید» + فرم ساخت با اعتبارسنجی سمت کلاینت (کد/نام/مقادیر منفی) + دکمهٔ حذف با confirm + پیام‌های خطای دقیق سرور |
| **Billing** | دو تب «سفارش‌ها / فاکتورها»؛ تب فاکتورها: ۳ کارت خلاصهٔ درآمد + جست‌وجوی فروشگاه (debounce) + فیلتر وضعیت + صفحه‌بندی |
| **Users** | جست‌وجوی زنده + فیلتر نقش/وضعیت + صفحه‌بندی سرور + suspend/activate برای همهٔ کاربران فروشگاه |
| **`/admin/contact` (جدید)** | چیپ‌های وضعیت با شمارش زنده، جست‌وجو، فهرست + پنل جزئیات دوستونه؛ باز کردن پیامِ «جدید» خودکار «خوانده‌شده» می‌شود؛ یادداشت پیگیری + «پاسخ‌داده‌شده/بازگشایی» + دکمهٔ پاسخ با ایمیل |
| **`/admin/operators` (جدید)** | جدول اپراتورها (نام/وضعیت/نشست‌های فعال/آخرین ورود) + نشان «شما» + فرم افزودن ادمین + ویرایش نام + تعلیق/فعال‌سازی/حذف با confirm |
| **Settings** | ردیف «نشست فعلی» + کارت «اپراتورهای پلتفرم» با لینک مدیریت |
| **Nav** | «پیام‌های تماس» در گروه مشتریان + «اپراتورها» در گروه پلتفرم |

### DB
- `db/migrations/0013_contact_inbox.sql` — ستون‌های `status` (new/read/resolved) + `admin_note` + `updated_at` روی `contact_messages` + ایندکس وضعیت.

### تست‌ها
- `tests/integration/test_admin_revenue.py` — ۸ تست end-to-end روی PG واقعی:
  ساخت پلن → **نمایش در `/plans` عمومی** → مخفی‌سازی → حذف · اعتبارسنجی/کد تکراری · ردِ حذف پلنِ در حال استفاده (409) · شکل/فیلتر فاکتورها · چرخهٔ کامل inbox تماس (ثبت عمومی → new → read + یادداشت فارسی → فیلتر/شمارش → خطاهای تمیز) · CRUD اپراتور **بدون bootstrap** + ورود واقعی ادمین دوم + تعلیق⇒ابطال نشست⇒ردِ ورود · قوانین self-action با JWT · حفاظت از آخرین ادمین فعال

## نتایج گیت‌ها (محیط توسعهٔ این سشن — Linux، PG واقعی)

| گیت | نتیجه |
|---|---|
| `pytest` (کل مجموعه + integration روی PG) | **۱۲۸ پاس / ۳ skip** (فقط ES) |
| `ruff` + `mypy` | تمیز (۸۹ فایل) |
| `tsc --noEmit` + `npm run check:all` | صفر خطا/هشدار (i18n·hardcoded·size·routes·assets·dead) |
| `next build` | موفق — ۱۰۳ صفحه (۲ مسیر جدید) |
| functional-check / responsive-check | ۰ خطا / ۰ سرریز |
| سرریز صفحات جدید (۳۷۵/۷۶۸/۱۲۸۰) | هر ۵ صفحهٔ فاز ۲ × ۳ عرض = ۰px |
| تأیید زندهٔ مرورگر (Playwright) | ساخت پلن از UI → ظهور در فهرست ادمین **و صفحهٔ عمومی `/pricing`** → inbox تماس (باز کردن، یادداشت، resolve) → تب فاکتورها → افزودن ادمین دوم از UI و **ورود موفق بدون هیچ توکنی** → صفحهٔ operators با نشان «شما» و بدون دکمهٔ تعلیق/حذف برای خود |

## چک‌لیست پذیرش فاز ۲ (از پلن)

- [x] ساخت پلن جدید → نمایش در صفحهٔ قیمت‌گذاری عمومی (تست خودکار + تأیید زندهٔ مرورگر)
- [x] inbox contact کار می‌کند (ثبت از فرم عمومی → triage در ادمین)
- [x] ادمین دوم بدون bootstrap token (از UI ساخته و وارد شد)
- [x] گزارش: همین فایل
- [ ] **تأیید شما برای شروع فاز ۳**

## دستورات تست روی ویندوز (محیط شما)

```powershell
# 1) مهاجرت جدید (PG ویندوز :5433)
$env:PG_DSN = "postgresql://acip:<pass>@localhost:5433/acip"
python scripts/apply_migrations.py    # باید 0013_contact_inbox را اعمال کند

# 2) API + Web
$env:PYTHONPATH = "packages;services"
python -m uvicorn services.api.main:create_app --factory --port 8000
cd apps/web; npm run build; npm run start   # ترمینال جدا

# 3) تست‌های خودکار فاز ۲
python -m pytest tests/integration/test_admin_revenue.py -v

# 4) تست دستی UI → http://localhost:3000/admin
#    پلن‌ها: «پلن جدید» → ساخت → دیدن آن در http://localhost:3000/pricing → حذف با confirm
#    صورت‌حساب: تب «فاکتورها» → فیلتر وضعیت + جست‌وجوی فروشگاه
#    کاربران: جست‌وجوی ایمیل + فیلتر نقش/وضعیت
#    پیام‌های تماس: از صفحهٔ عمومی contact پیام بفرستید → در ادمین triage کنید
#    اپراتورها: افزودن ادمین دوم → خروج → ورود با ادمین جدید (بدون توکن)
```

## فایل‌های تغییر
`services/api/routers/admin.py` · `services/api/routers/admin_operators.py` (جدید) ·
`services/api/main.py` · `db/migrations/0013_contact_inbox.sql` (جدید) ·
`apps/web/app/[locale]/admin/{plans,billing,users,settings}/page.tsx` ·
`admin/billing/invoices.tsx` (جدید) · `admin/contact/page.tsx` (جدید) ·
`admin/operators/page.tsx` (جدید) · `components/shell.tsx` ·
`messages/{fa,en}/admin.json` · `tests/integration/test_admin_revenue.py` (جدید) ·
`docs/vitrin-completion-roadmap.md` (نسخهٔ تیک‌خورده)
