# Dev Sign-off — فاز ۸ (تست نهایی توسعه)

تاریخ: ۱۴۰۵/۰۴/۱۲ · شاخه: `claude/gallant-shannon-8b31td`
محیط اجرا: Linux (سشن توسعه) — PG واقعی، Redis واقعی، worker واقعی، API + Web زنده، **ES خاموش** (طبق قانون پروژه، تست ES سمت شما)

## ۱) چک‌لیست صفحات — ۲۰ صفحهٔ ادمین + ۱۶ صفحهٔ داشبورد (جاروی زندهٔ خودکار)

ابزار: `apps/web/scripts/fe-qa/signoff-sweep.cjs` — ورود واقعی (bootstrap ادمین + signup مالک)، بارگذاری هر صفحه، بررسی heading + error boundary + خطای JS. **نتیجه: ۳۶/۳۶ سبز، صفر خطا.**

| سطح | صفحات (همه ✓) |
|---|---|
| ادمین (۲۰) | نمای کلی · Tenants · Users · Plans · Billing · Analytics · Usage · Audit · Security · Queue · Health · Models · Elasticsearch · Synonyms · Agent · Widget · Flags · Contact · Operators · Settings |
| داشبورد (۱۶) | نمای کلی · کاتالوگ · تنظیم جست‌وجو · دستیار · دانش‌نامه · تحلیل جست‌وجو · تبدیل · گفت‌وگو · سرنخ‌ها · پلن و صورت‌حساب · اعتبار · کلیدها · ویجت · تیم · گزارش فعالیت · تنظیمات |

بررسی فارسی/RTL: نمونه‌های `/fa/admin` («نمای کلی پلتفرم») و `/fa/admin/elasticsearch` («کنترل الستیک‌سرچ») با `dir=rtl` تأیید شد؛ پوشش کامل i18n با گیت `i18n-check` (صفر خطا).

## ۲) گیت‌های خودکار

| گیت | نتیجه |
|---|---|
| `pytest` (کل، روی PG زنده) | **۱۵۰ پاس / ۴ skip** (skipها فقط ES-gated) |
| `ruff` + `mypy` | تمیز (۱۰۰ فایل) |
| `php -l` (ماژول OpenCart) | بدون خطا |
| `tsc --noEmit` + `npm run check:all` | صفر خطا (i18n/hardcoded/size/routes/assets/dead) |
| `functional-check` | 0 failure |
| `responsive-check` (همهٔ ۲۰ مسیر ادمین + عمومی) | 0 overflow |
| `a11y-check` (عمومی + ۸ صفحهٔ ادمین با ورود واقعی) | 0 نقض serious/critical |
| `next build` | موفق |

## ۳) Graceful 503 در `/v1/*` با ES خاموش — تأیید زنده (curl واقعی + کلید widget واقعی)

| Endpoint | پاسخ |
|---|---|
| `POST /v1/search` | **503** `{"error":{"code":"search_unavailable",...}}` |
| `GET /v1/suggest` | **503** `search_unavailable` |
| `POST /v1/chat` | **503** `assistant_unavailable` |
| بدون کلید | 401 `unauthorized` (نه 503) |

+ تست خودکار همین رفتار: `tests/integration/test_engine.py::test_v1_degrades_to_503_when_es_down` (پاس).

## ۴) موارد ES-دار — چک‌لیست سمت شما (ویندوز، ES داکر :19500)

```powershell
$env:PYTHONPATH = "packages;services"
# تست‌های integration با ES واقعی (تنها ۴ skip باقی‌مانده):
python -m pytest tests/integration/test_search_es.py tests/integration/test_engine.py -q
# KPIهای جست‌وجو + groundedness (فاز ۶):
python scripts/seed_catalog.py --no-embeddings
python -m eval.run_eval --golden eval/golden_set/golden_fa.jsonl --tenant TENANT_ID --kpi
python -m eval.groundedness --tenant TENANT_ID --limit 20
# جاروی صفحات روی ویندوز (اختیاری):
cd apps/web; $env:ADMIN_TOKEN="..."; node scripts/fe-qa/signoff-sweep.cjs
```

- [ ] چهار تست ES-gated سبز
- [ ] KPIها ثبت (NDCG@10 ≥ 0.80 · p95 < 150ms · zero-result < 5% · groundedness ≥ 95%)
- [ ] جست‌وجو/چت ویجت روی فروشگاه pilot (راهنما: `docs/integrations-fa.md`)

## ۵) نتیجه

توسعه از دید این سشن **کامل و سبز** است؛ تنها اقلام وابسته به ES زنده باقی مانده که در بند ۴ فهرست شد. طبق پلن، فازهای عملیاتی (۹ به بعد) پس از تأیید متنی شما آغاز می‌شوند — که در پیام «این سه تا فاز رو بصورت کامل انجام بده» صادر شده و فاز ۹ در ادامهٔ همین تحویل اجرا شده است.
