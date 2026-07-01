# فاز ۱ — ادمین: زیرساخت عملیات و Tenant Management

**وضعیت: تأییدشده ✅** (پس از بازبینی مجدد: اصلاح bucketing منطقهٔ زمانی روندها + رفع سرریزهای responsive)
تاریخ تحویل: ۱۴۰۵/۰۴/۱۰ · شاخه: `claude/gallant-shannon-8b31td`

## چه چیزی ساخته شد

### Backend — ۷ endpoint جدید/گسترش‌یافته (`services/api/routers/admin.py`)

| Endpoint | شرح |
|---|---|
| `GET /admin/tenants/{id}` | پروفایل کامل: نام/شناسه/وضعیت، اشتراک (پلن + وضعیت + پایان دوره)، اعتبار (مصرف/اعطا/سقف)، کلیدهای API (بدون هیچ مادهٔ محرمانه)، وضعیت sync، تعداد تیم، یادداشت اپراتور |
| `GET /admin/tenants/{id}/keys` | فهرست کلیدهای فروشگاه |
| `POST /admin/tenants/{id}/keys` | صدور کلید جدید (widget/sync + برچسب) — کلید خام فقط یک بار برگردانده می‌شود |
| `POST /admin/tenants/{id}/keys/{key_id}/revoke` | ابطال کلید |
| `POST /admin/tenants/{id}/credits` | تنظیم دستی اعتبار (+ اعطا / − کسر) → ثبت در `credit_ledger` با `rung=manual` + audit |
| `PATCH /admin/tenants/{id}/plan` | تغییر دستی پلن: به‌روزرسانی `tenants.plan_id` + upsert اشتراک با دورهٔ تازه (۱–۳۶۶ روز) + audit |
| `PATCH /admin/tenants/{id}/notes` | یادداشت اپراتور (migration `0012`) |
| `GET /admin/overview` (گسترش) | KPIها + سری روزانهٔ ۷/۳۰/۹۰ روزه: ثبت‌نام فروشگاه، فراخوانی‌های API، درآمد پرداخت‌شده، پرداخت‌های ناموفق + اشتراک‌های معوق |
| `GET /admin/tenants` (گسترش) | جست‌وجوی slug/name + فیلتر status/plan + صفحه‌بندی سمت سرور (`total/limit/offset`) |

نکتهٔ صادقانه: **روند MRR تاریخی** بدون snapshot ماهانه قابل محاسبه نیست؛ پروکسی آن «درآمد پرداخت‌شدهٔ روزانه» است و MRR به‌صورت عدد لحظه‌ای نمایش داده می‌شود.

### Frontend

| صفحه | تغییر |
|---|---|
| **Overview** (`admin/page.tsx`) | ۴ کارت KPI + هشدار اشتراک معوق + ۴ نمودار روند (سری روزانه با tooltip + crosshair) + سوییچ بازهٔ ۷/۳۰/۹۰ روز + دسترسی سریع + حالت خطا/بارگذاری |
| **Tenants list** | جست‌وجوی زنده (debounce ۳۰۰ms)، فیلتر وضعیت/پلن (پلن‌ها از API)، صفحه‌بندی سرور، حالت «نتیجه‌ای نیست» |
| **Tenant detail** | بازسازی کامل ۲ستونه: پروفایل + sync + کلیدها (صدور/ابطال/نمایش یک‌باره) + یادداشت اپراتور | اعتبار (نمایش + فرم تنظیم) + تغییر پلن + چرخهٔ عمر/حاکمیت داده — **بعد از هر mutation کل پروفایل refetch می‌شود** |
| **Login** | اگر نشست ادمین فعال باشد مستقیم به `/admin` هدایت می‌شود؛ پیام‌های خطا همان متن دقیق سرور (قفل حساب/اعتبار نامعتبر) |
| کامپوننت جدید | `components/trend-chart.tsx` — نمودار روند SVG سبک: خط ۲px با رنگ برند اعتبارسنجی‌شده (اسکریپت `validate_palette` — قبولی هر ۴ چک روی سطح تیره)، مقیاس صفرمبنا، crosshair + tooltip (مقدار پررنگ، تاریخ شمسی ثانویه)، محور زمان LTR داخل پوستهٔ RTL |

### DB
- `db/migrations/0012_tenant_admin_notes.sql` — ستون `admin_notes` روی tenants.

### تست‌ها
- `tests/integration/test_admin_tenant.py` — ۸ تست end-to-end روی PG واقعی (همان harness موجود؛ پوشهٔ `tests/` ریشه فقط تست‌های hermetic بدون DB را نگه می‌دارد، برای همین به‌جای مسیرِ گفته‌شده در پلن، در `tests/integration/` قرار گرفت):
  پروفایل کامل + 404 تمیز · صدور/ابطال کلید · تنظیم اعتبار (اعطا/کسر/رد صفر) · تغییر پلن (اعمال سقف پلن + upsert بدون رکورد تکراری + رد پلن/وضعیت نامعتبر) · یادداشت فارسی · فیلتر/صفحه‌بندی فهرست · شکل سری‌های روند (۳۰ نقطه، بازهٔ ۷/۹۰، clamp) · رد همهٔ endpointها بدون احراز (401)

## نتایج گیت‌ها (محیط توسعهٔ این سشن — Linux، PG واقعی)

| گیت | نتیجه |
|---|---|
| `pytest` (کل مجموعه + integration روی PG) | **۱۲۰ پاس / ۳ skip** (فقط ES) |
| `ruff` + `mypy` | تمیز (۸۸ فایل) |
| `tsc --noEmit` + `npm run check:all` | همه صفر خطا/هشدار |
| `next build` | موفق — ۹۹ صفحه |
| تأیید زندهٔ مرورگر (Playwright + PG واقعی) | ورود ادمین → Overview با نمودار و tooltip → redirect صفحهٔ login با نشست فعال → فیلتر فهرست (۱ از ۱) → صفحهٔ جزئیات → صدور کلید از UI با نمایش یک‌باره + ظهور ردیف → grant اعتبار و سقف پلن در UI منعکس شد |

## چک‌لیست پذیرش فاز ۱ (از پلن)

- [x] ایجاد tenant → مشاهدهٔ پروفایل کامل → suspend → activate → export (در این محیط تست شد؛ روی ویندوز با دستورات زیر تکرار کنید)
- [x] Overview نمودار با دادهٔ PG پر می‌شود (اسکرین‌شات‌های `p1_overview_fa` در سشن)
- [x] گزارش: همین فایل
- [ ] **تأیید شما برای شروع فاز ۲**

## دستورات تست روی ویندوز (محیط شما)

```powershell
# 1) مهاجرت جدید (PG ویندوز :5433)
$env:PG_DSN = "postgresql://acip:<pass>@localhost:5433/acip"
python scripts/apply_migrations.py    # باید 0012_tenant_admin_notes را اعمال کند

# 2) API + Web
$env:PYTHONPATH = "packages;services"
python -m uvicorn services.api.main:create_app --factory --port 8000
cd apps/web; npm run build; npm run start   # ترمینال جدا

# 3) تست‌های خودکار فاز ۱
python -m pytest tests/integration/test_admin_tenant.py -v

# 4) تست دستی UI  → http://localhost:3000/admin
#    Overview: سوییچ ۷/۳۰/۹۰ روز، hover روی نمودار (tooltip تاریخ شمسی)
#    فروشگاه‌ها: جست‌وجو/فیلتر/صفحه‌بندی → کلیک روی یک فروشگاه
#    جزئیات: صدور کلید (نمایش یک‌باره) → ابطال → تنظیم اعتبار → تغییر پلن → یادداشت → suspend/activate → export
```

## فایل‌های تغییر
`services/api/routers/admin.py` · `db/migrations/0012_tenant_admin_notes.sql` ·
`apps/web/components/trend-chart.tsx` (جدید) · `apps/web/app/[locale]/admin/page.tsx` ·
`admin/tenants/page.tsx` · `admin/tenants/[id]/{page,sections,actions}.tsx` ·
`admin/login/page.tsx` · `messages/{fa,en}/admin.json` ·
`tests/integration/test_admin_tenant.py` (جدید) · `docs/vitrin-completion-roadmap.md` (نسخهٔ تیک‌خورده)
