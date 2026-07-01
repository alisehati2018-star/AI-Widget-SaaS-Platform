-- Phase 1 (completion roadmap) — operator notes on a tenant.
-- Free-text field the platform operator can keep per store (support context,
-- onboarding state, payment arrangements). Control-plane only, never exposed
-- to the tenant itself.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS admin_notes TEXT;

INSERT INTO schema_migrations (version) VALUES ('0012_tenant_admin_notes')
    ON CONFLICT (version) DO NOTHING;
