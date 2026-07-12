# تایید زندهٔ پنل ادمین + مسیر کامل پول AI — چک‌لیست امضاشده

تاریخ: ۱۴۰۵/۰۴/۲۱ · شاخه: `claude/gallant-shannon-8b31td`
محیط: PostgreSQL واقعی (هر ۲۰ مایگریشن اعمال‌شده، شامل 0019/0020) + Redis + uvicorn + بیلد تولیدی Next (`next start`) + مرورگر واقعی (Chromium/Playwright). Elasticsearch در sandbox قابل نصب نبود (پروکسی دانلود را مسدود می‌کند) — مسیرهای وابسته به ES با degrade تمیز تایید شدند و گام retrieval در تست مسیر پول به‌صورت درجا تامین شد.

## پاسخ قطعی به «صفحات نمایشی‌اند»

**هیچ صفحه‌ای نمایشی نیست.** هر ۲۶ endpoint پشتیبان صفحات ادمین روی استک زنده ۲۰۰ برگرداندند، هر عمل آزمایش‌شده اثر واقعی و قابل‌راستی‌آزمایی در دیتابیس گذاشت، و سه جاروی مرورگری (functional / responsive / a11y) روی صفحات واقعی سبز شدند. حس «نمایشی بودن» دو ریشهٔ واقعی داشت که هر دو رفع شدند:
1. **باگ‌های بازخورد UI** (موفقیت دروغین، ذخیرهٔ بی‌پیام، اسپینر بی‌نهایت) — رفع در commit `6ac641e`.
2. **یک باگ ۵۰۰ واقعی رانتایم**: ناسازگاری OTel با FastAPI ≥0.138 (`_IncludedRouter` بدون `.path` در تفکیک نام span روی PARTIAL match) که درخواست‌های سالم مسیرهای AI را ۵۰۰ می‌کرد — دقیقاً همان الگوی «صفحه کار نمی‌کند». رفع با شیم سازگاری در `setup_telemetry` (commit `3df333e`).

## چک‌لیست endpointهای پشتیبان صفحات (استک زنده)

| گروه | endpoint ها | نتیجه |
|---|---|---|
| هسته | overview، tenants (+detail/keys/credits/plan/status)، users، plans، orders، invoices، contact، audit، usage، queue، health، models، feature-flags، security، analytics، zero-results، widget-defaults، operators | همه **200** ✅ |
| AI | providers، models، routes، routing-settings، pricing، finance، provider-templates، credit-policy | همه **200** ✅ |

## مسیر بحرانی AI — قدم‌به‌قدم روی استک زنده

| # | قدم | نتیجه |
|---|---|---|
| ۱ | قالب‌های ارائه‌دهنده (`GET provider-templates`) | ۸ قالب واقعی (openrouter/openai/google/deepseek/groq/bynara/avalai/conduit) ✅ |
| ۲ | ساخت از قالب (`from-template` + کلید) | ارائه‌دهندهٔ openrouter ساخته شد، کلید ماسک‌شده ✅ |
| ۳ | **کشف مدل** (`discover`) از سرور OpenAI-compatible زنده | فهرست مدل کشف و برگردانده شد ✅ |
| ۴ | **ایمپورت گروهی** (`models/import`) با قیمت ورودی/خروجی | مدل با price sheet ذخیره شد ✅ |
| ۵ | بستن زنجیرهٔ chat (۲ مدل: primary + failover) | `{"task":"chat","count":2}` ✅ |
| ۶ | annotations اهلیت | با غیرفعال‌کردن ارائه‌دهنده، هر دو binding زنده `PROVIDER_INACTIVE` شدند و با فعال‌سازی برگشتند ✅ |
| ۷ | کلید سراسری failover (`routing-settings`) | toggle → persist → read-back ✅ |
| ۸ | گارد modality | بستن مدل chat به task embedding → 422 با پیام واضح ✅ |
| ۹ | گارد حذف ارائه‌دهندهٔ دارای مدل | 422: «۲ مدل دارد؛ اول منتقل/حذف کنید» ✅ |
| ۱۰ | حذف گروهی مدلِ داخل زنجیره | **بلاک شد** با `chain_positions` — حفاظت زنجیره ✅ |
| ۱۱ | سیاست کردیت ثبت‌نام (`credit-policy`) | تنظیم ۵۰۰ کردیت → ثبت‌نام تازه → ردیف `signup_bonus +500` در ledger ✅ |
| ۱۲ | سناریوی خطا: کلید عمداً غلط | discover → «Could not fetch the model list: 403»، check-credit → «Credit check failed: 403» — پیام واضح، نه سکوت/موفقیت دروغین ✅ |

## مسیر کامل پول (معیار پذیرش نهایی)

با یک ارائه‌دهندهٔ OpenAI-compatible محلی (جایگزین کلید واقعی؛ همان قرارداد wire) و **دقیقاً همان سیم‌کشی رانتایم API** (`DynamicProviderChain` + `WalletBudgetGuard` + `_pricer` + `_meter`):

| قدم | نتیجه |
|---|---|
| ثبت ارائه‌دهنده → کشف مدل → ایمپورت با قیمت $3/$15 per 1M → بستن زنجیرهٔ chat | از راه HTTP ادمین ✅ |
| نوبت مکالمهٔ «سخت» (مقایسه/پیشنهاد) | rung=`frontier`، provider=`fake-openai-e2e`، model=`fake-chat-1`، tokens=220/64 ✅ |
| ردیف `usage_events` | `cost=22.68` کردیت، `provider_cost=$0.00162` — **حساب توکنی دقیق**: 220×$3/1M + 64×$15/1M = $0.00162 ✓ و با حاشیهٔ ۴۰٪ و نرخ کردیت → ۲۲٫۶۸ ✓ |
| کیف پول | ۴۹۹٫۹۸ → ۴۷۷٫۳۰ (دقیقاً ۲۲٫۶۸ کسر؛ ردیف ledger ثبت شد) ✅ |
| تکرار همان سؤال | rung=`cache` (L1 hit) — هزینهٔ صفر ✅ |
| نردبان هزینه | پرسش SYNTHESIS با LLM محلیِ خاموش → degrade تمیز به rung=`search` با هزینهٔ flat ۰٫۰۱ (اصل local-first + REQ-M7-009) ✅ |
| **`/admin/ai/finance`** | credits=22.7، value=$0.00227، COGS=$0.00162، **gross margin=$0.00065**، تفکیک by_model (توکن دقیق) و by_tenant ✅ |
| صفحهٔ providers | مصرف ۳۰روزهٔ همان ارائه‌دهنده: ۱ فراخوانی، ۲۲٫۶۸ کردیت، $0.00162 ✅ |

## جاروهای مرورگری (Chromium واقعی، بیلد تولیدی)

- **functional-check**: ۰ خطا — ورود ادمین، ساخت تنانت با کلید یک‌بارهٔ واقعی، ظهور ردیف در جدول، export، toggle فلگ و برگشت آن، wizard الستیک، iframe ویجت با loader واقعی.
- **responsive-check**: ۰ overflow — شامل دو صفحهٔ جدید `/admin/providers` و `/admin/ai-config` (به فهرست جارو اضافه شدند).
- **a11y-check**: ۰ تخلف جدی/بحرانی — جاروی گسترش‌یافته یک تخلف واقعی پیدا کرد (۸ select بدون نام در ai-config) که همان‌جا رفع شد.

## آیتم‌های مختص محیط شما (خارج از توان sandbox)

1. **Elasticsearch واقعی**: نصب ES در sandbox ممکن نبود؛ چرخهٔ RAG کامل (retrieval واقعی از ایندکس) و KPIهای جست‌وجو مطابق `production-readiness.md` روی سرور شما.
2. **کلید واقعی OpenRouter**: مسیر کشف/ایمپورت/چت/سود با قرارداد یکسان تایید شد؛ فقط جایگزینی کلید لازم است.
3. **مرورگر دستی موبایل**: جاروی خودکار ۳ عرض صفحه پاس شد؛ لمس واقعی روی دستگاه سمت شما.
