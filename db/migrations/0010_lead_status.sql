-- ACIP lead pipeline (M10) — give captured leads a workable status + notes so
-- store owners can triage them (new → contacted → qualified → won/lost).
-- Control-plane only.

ALTER TABLE leads ADD COLUMN IF NOT EXISTS status     TEXT NOT NULL DEFAULT 'new';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS notes      TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

INSERT INTO schema_migrations (version) VALUES ('0010_lead_status')
    ON CONFLICT (version) DO NOTHING;
