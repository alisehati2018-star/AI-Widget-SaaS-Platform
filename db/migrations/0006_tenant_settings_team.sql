-- Phase 8 — store settings/white-label + team invitations (M9 human layer).
-- Powers the store-owner dashboard: branding, store connection metadata, and
-- inviting staff into a tenant. Control-plane only.

-- Free-form per-tenant settings: white-label (logo/colors), connected store URL,
-- platform (opencart/woocommerce), widget config. JSONB keeps it schema-light.
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS settings JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Staff invitations into a tenant. The accept flow reuses password_resets to let
-- the invitee set their own password.
CREATE TABLE IF NOT EXISTS invitations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'store_staff' CHECK (role IN ('store_owner', 'store_staff')),
    invited_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invitations_tenant ON invitations(tenant_id);

INSERT INTO schema_migrations (version) VALUES ('0006_tenant_settings_team')
    ON CONFLICT (version) DO NOTHING;
