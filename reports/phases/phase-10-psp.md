# فاز ۱۰ — PSP (زرین‌پال) + فاکتور PDF + Checkout در UI

**وضعیت: تحویل‌شده**
تاریخ تحویل: ۱۴۰۵/۰۴/۱۲ · شاخه: `claude/gallant-shannon-8b31td`

## چه چیزی ساخته شد

### ۱) درگاه پرداخت زرین‌پال (v4)

| قطعه | شرح |
|---|---|
| `packages/acip_billing/psp.py` | `ZarinPalProvider`: ساخت پرداخت (`payment/request.json` → آدرس StartPay) و **verify سمت سرور** (`payment/verify.json`؛ کد 100/101). آدرس پایه configurable — production/sandbox/تست با یک env عوض می‌شود |
| checkout پلن + خرید اعتبار | هر دو مسیر (`/tenant/billing/checkout` و `/topup`) با `BILLING_PROVIDER=zarinpal` سفارش pending می‌سازند، authority را روی سفارش ذخیره و `redirect_url` برمی‌گردانند. خطای درگاه → **502 `psp_unavailable`** و سفارش pending می‌ماند (قابل تلاش مجدد). مسیر manual دست‌نخورده کنار PSP کار می‌کند |
| `GET /billing/callback` | برگشت از درگاه: سفارش با authority پیدا می‌شود (جدیدترین)، فقط با `Status=OK` **و verify موفق سمت سرور** paid می‌شود → فعال‌سازی پلن/اعتبار + صدور فاکتور + ایمیل + audit → redirect به داشبورد با `payment=success`. انصراف/شکست → سفارش `failed` و **هیچ‌چیز فعال نمی‌شود**. callback تکراری idempotent است |
| تنظیمات | `ZARINPAL_MERCHANT_ID` · `ZARINPAL_BASE_URL` (sandbox: `https://sandbox.zarinpal.com`) — به compose تولید و `.env.production.example` اضافه شد |

### ۲) فاکتور PDF فارسی

- `packages/acip_billing/invoice_pdf.py`: رندر سمت سرور با fpdf2 + uharfbuzz (**shaping کامل فارسی + RTL**)؛ فونت auto-discover (Vazirmatn → DejaVu → FreeSerif → Tahoma ویندوز) یا `INVOICE_FONT_PATH`
- `GET /tenant/billing/invoices/{number}/pdf` — دانلود مستقیم؛ بدون فونت/موتور → **503 تمیز** با راهنمای استفاده از نسخهٔ HTML چاپی (که همیشه هست)
- وابستگی‌های جدید در pyproject: `fpdf2` + `uharfbuzz` (روی ویندوز: `pip install -e .`)
- خروجی نمونه رندر و به‌صورت بصری تأیید شد (جدول RTL، متن شکل‌گرفته)

### ۳) UI پرداخت

- صفحهٔ billing از قبل `next=redirect` را هندل می‌کرد؛ حالا **بنر نتیجهٔ پرداخت** از `?payment=success|failed` (با پاک‌سازی URL) + دکمهٔ **PDF** کنار HTML برای هر فاکتور + i18n کامل fa/en
- جدول فاکتورها به کامپوننت `invoices-card.tsx` منتقل شد (سقف ۳۰۰ خط)

### ۴) تست‌ها

- **hermetic (۵ تست، `tests/test_psp.py`):** ساخت پرداخت (merchant/amount/callback/metadata)، ردشدن request، پذیرش کد 100 و 101 و رد بقیه در verify، خطای شبکه → `PspError`، رندر PDF فارسی
- **E2E (۳ تست، `tests/integration/test_billing_psp.py`، همین‌جا پاس):** زرین‌پال جعلی (قرارداد کامل request/verify) + uvicorn واقعی با `BILLING_PROVIDER=zarinpal` → **signup → checkout → StartPay → callback → verify → پلن active + فاکتور + دانلود PDF واقعی**؛ مسیر انصراف (NOK) → سفارش failed و پلن تغییری نمی‌کند؛ authority ناشناس → redirect شکست؛ callback تکراری idempotent
- **تأیید زندهٔ UI:** بنر موفق/ناموفق فارسی روی صفحهٔ billing واقعی + پاک‌شدن query از URL

## گیت‌ها

pytest کامل: **۱۶۸ پاس / ۴ skip** (فقط ES) · ruff + mypy تمیز (۱۰۴ فایل) · tsc + check:all + next build صفر خطا.

## راه‌اندازی روی staging/production (سمت شما)

```powershell
pip install -e .            # وابستگی‌های جدید PDF (fpdf2 + uharfbuzz)
# sandbox زرین‌پال روی staging:
$env:BILLING_PROVIDER = "zarinpal"
$env:ZARINPAL_MERCHANT_ID = "<merchant sandbox>"
$env:ZARINPAL_BASE_URL = "https://sandbox.zarinpal.com"
# WIDGET_BASE_URL باید آدرس عمومی API باشد (callback درگاه به آن برمی‌گردد)
# سپس از داشبورد → پلن و صورت‌حساب → انتخاب پلن → درگاه sandbox → برگشت با بنر موفق
# production: فقط merchant واقعی + ZARINPAL_BASE_URL پیش‌فرض
```

نکته: مبلغ سفارش به‌صورت عدد صحیح به درگاه می‌رود (واحد = پیکربندی پنل زرین‌پال شما — ریال/تومان). `BILLING_CURRENCY` را هماهنگ تنظیم کنید.
