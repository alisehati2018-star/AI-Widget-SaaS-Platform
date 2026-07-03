-- 0017: bilingual plan content (audit W3). The pricing/billing pages render
-- name_fa/description_fa/features_fa on the Persian locale (falling back to
-- the base columns), so the point of sale reads natively in Persian.
ALTER TABLE plans ADD COLUMN IF NOT EXISTS name_fa TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS description_fa TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS features_fa JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Persian content for the seeded catalogue (idempotent by code).
UPDATE plans SET
  name_fa = 'رایگان',
  description_fa = 'جست‌وجوی ترکیبی فارسی را روی یک فروشگاه امتحان کنید.',
  features_fa = '["۱ فروشگاه","جست‌وجوی ترکیبی فارسی","۵ هزار اعتبار هوش مصنوعی در ماه","پشتیبانی انجمن"]'::jsonb
WHERE code = 'free';

UPDATE plans SET
  name_fa = 'شروع',
  description_fa = 'برای فروشگاه‌های رو به رشد که دستیار خرید می‌خواهند.',
  features_fa = '["۱ فروشگاه","جست‌وجو + دستیار RAG","۵۰ هزار اعتبار هوش مصنوعی در ماه","داشبورد تحلیل","پشتیبانی ایمیلی"]'::jsonb
WHERE code = 'starter';

UPDATE plans SET
  name_fa = 'حرفه‌ای',
  description_fa = 'لایهٔ کامل هوش با موتور بینش و جذب سرنخ.',
  features_fa = '["۳ فروشگاه","همهٔ امکانات پلن شروع","موتور بینش و سرنخ","۲۵۰ هزار اعتبار هوش مصنوعی در ماه","پشتیبانی اولویت‌دار"]'::jsonb
WHERE code = 'pro';

UPDATE plans SET
  name_fa = 'سازمانی',
  description_fa = 'درون‌سازمانی، SSO، سقف‌های سفارشی و SLA.',
  features_fa = '["فروشگاه نامحدود","مدل‌های self-hosted","SSO + گزارش حسابرسی","SLA سفارشی","پشتیبانی اختصاصی"]'::jsonb
WHERE code = 'enterprise';

INSERT INTO schema_migrations (version) VALUES ('0017_plan_i18n')
ON CONFLICT (version) DO NOTHING;
