# گزارش آمادگی تولید (Production Readiness) — فاز ۱۱

تاریخ: ۱۴۰۵/۰۴/۱۲ · شاخه: `claude/gallant-shannon-8b31td`
مراجع: [dev-signoff](dev-signoff.md) · [استقرار](../docs/DEPLOYMENT-SERVER.md) · [runbook](../docs/RUNBOOK-SLO-DR.md)

## ۱) نقشهٔ هدف‌های headline → شواهد

| هدف (blueprint §1/§18) | وضعیت | شواهد |
|---|---|---|
| ایزولهٔ tenant ۱۰۰٪ (ناقض انتشار) | ✅ در کد و تست | فیلتر اجباری `tenant_id` در query-builder مرکزی + تست واحد و تست ES-gated |
| جست‌وجو p95 < 150ms | ⏳ اندازه‌گیری روی ES زندهٔ شما | harness آماده: `run_eval --kpi` + `load_test.py`؛ مسیر HTTP این‌جا سالم سنجیده شد |
| NDCG@10 ≥ 0.80 | ⏳ روی ES زنده | golden set ۵۰ کوئری + gate خودکار |
| zero-result < 5٪ | ⏳ روی ES زنده | همان gate |
| groundedness ≥ 95٪ | ⏳ روی ES زنده | `eval/groundedness.py` (تأیید citation در ایندکس خود tenant) |
| degrade تمیز (search هرگز به AI وابسته نیست) | ✅ تأیید زنده | 503 کددار در `/v1/*` با ES خاموش؛ BM25-only با TEI خاموش؛ پاسخ template با LLM خاموش |
| دسترس‌پذیری 99.9٪ | ✅ ابزار آماده | compose تولید + healthcheckها + Prometheus/alerts + runbook |

## ۲) چک‌لیست آمادگی

**کد و تست** — ✅ آماده
- ۱۶۸ تست پاس / ۴ skip فقط-ES · ruff/mypy تمیز (۱۰۴ فایل) · tsc/check:all/build صفر خطا
- جاروی sign-off: ۳۶/۳۶ صفحه سالم · fe-qa (functional/responsive/a11y) سبز

**امنیت** — ✅ آماده
- دو صفحهٔ هویتی مجزا (ادمین/مشتری)، Argon2/bcrypt، قفل تدریجی، نشست‌های revoke‌پذیر
- **TOTP ادمین** با گارد ضدتکرار (کد مصرف‌شده حتی در پنجرهٔ skew مرده است) — چرخهٔ کامل زنده تأیید شد
- **IP allowlist** برای `/admin/*` (fail-closed) — زنده تأیید شد
- CSRF + security headers + HSTS/COOKIE_SECURE اجباری در compose تولید؛ CORS محدود به دامنهٔ وب
- webhook امضادار (HMAC) · کلیدهای API هش‌شده · فاکتور HTML با escape کامل

**پرداخت (فاز ۱۰)** — ✅ آماده (sandbox)؛ production پس از دریافت merchant واقعی
- زرین‌پال v4: checkout → StartPay → callback → **verify سمت سرور** (redirect به‌تنهایی هیچ‌چیز فعال نمی‌کند)
- انصراف/شکست → order=failed، بدون فعال‌سازی؛ callback تکراری idempotent
- فاکتور PDF فارسی (shaping کامل) + HTML چاپی؛ مسیر manual همچنان کنار PSP برقرار است

**عملیات** — ✅ آماده
- compose تولید (فقط Caddy روی اینترنت، TLS خودکار، ES امن) · backup/restore **تست‌شده** · Prometheus + alerts · load test · runbook SLO/DR

## ۳) اقلام باز (پیش از Go-Live واقعی — همه سمت شما)

| # | قلم | مرجع |
|---|---|---|
| ۱ | اجرای تست‌های ES-gated + ثبت ۴ KPI روی ویندوز/سرور با ES روشن | dev-signoff بند ۴ |
| ۲ | pilot فروشگاه واقعی (OpenCart/Woo) → sync → جست‌وجوی ویجت | docs/integrations-fa.md |
| ۳ | استقرار سرور طبق راهنما + چک‌لیست تحویل (TLS، allowlist، TOTP همهٔ ادمین‌ها، cron backup، load test تولید) | docs/DEPLOYMENT-SERVER.md §۸ |
| ۴ | merchant واقعی زرین‌پال + یک تراکنش sandbox روی staging و سپس production | phase-10 report |
| ۵ | مدل‌های inference (TEI embedding + LLM) روی GPU/سرویس — بدون آن‌ها search واژگانی و پاسخ template است (طراحی‌شده) | DEPLOYMENT-SERVER |
| ۶ | **تأیید متنی نهایی شما برای Go-Live** | این گزارش |

## ۴) ریسک‌های باقی‌مانده و کاهش

| ریسک | کاهش |
|---|---|
| کیفیت رتبه‌بندی روی دادهٔ واقعی فروشگاه ≠ fixture | چرخهٔ رسمی tuning: eval → مترادف‌ها → re-eval (گزارش فاز ۶) |
| قطعی PSP | سفارش pending می‌ماند، fallback دستی، playbook در runbook |
| تک‌سروری (SPOF) | backup/DR با RTO<30م؛ ارتقا به HA در v2 (خارج از محدودهٔ GA طبق پلن) |
| گم‌شدن webhook فروشگاه | reconciliation دلتای ۱۵دقیقه‌ای self-healing (فاز ۷) |

**نتیجه:** پلتفرم از نظر کد، تست، امنیت و ابزار عملیاتی برای Go-Live آماده است؛ ۶ قلم بند ۳ (اجرایی/اعتبارنامه‌ای، سمت شما) باز است و Go-Live نهایی طبق پلن به تأیید متنی شما گره خورده است.
