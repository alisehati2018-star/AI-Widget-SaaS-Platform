-- ACIP leads (Phase 2, M10: REQ-M10-004 lead capture)
-- PII-minimised, tenant-scoped lead records captured in-conversation.
-- Access-controlled via the operator/admin plane; retention policy is set in
-- Phase 3 (GAP-B4). Control-plane only.

CREATE TABLE IF NOT EXISTS leads (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email       TEXT,
    phone       TEXT,
    has_intent  BOOLEAN NOT NULL DEFAULT FALSE,
    source      TEXT NOT NULL DEFAULT 'chat',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_leads_tenant_time ON leads(tenant_id, created_at);

INSERT INTO schema_migrations (version) VALUES ('0003_leads')
    ON CONFLICT (version) DO NOTHING;
