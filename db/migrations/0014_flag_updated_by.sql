-- Phase 4 (admin QA) — record WHO last changed each feature flag, so the
-- flags page can show "last changed by" next to the toggle.

ALTER TABLE feature_flags ADD COLUMN IF NOT EXISTS updated_by TEXT;

INSERT INTO schema_migrations (version) VALUES ('0014_flag_updated_by')
    ON CONFLICT (version) DO NOTHING;
