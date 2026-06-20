-- ACIP Phase 3 — billing, audit, governance (M11)
-- Credit ledger + plan limits (REQ-M11-009), audit log (REQ-M11-007),
-- and per-tenant governance flags (REQ-M11-006). Control-plane only.

-- Plan limits: monthly credit cap + per-minute rate limit (REQ-M11-003/009).
ALTER TABLE plans ADD COLUMN IF NOT EXISTS monthly_credit_cap NUMERIC(14, 2) NOT NULL DEFAULT 100000;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS rate_limit_per_min INTEGER NOT NULL DEFAULT 120;

-- Tenant governance flags (REQ-M11-006: disable tracking; residency is on-prem).
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS tracking_enabled BOOLEAN NOT NULL DEFAULT TRUE;

-- Append-only credit ledger (REQ-M11-009): one row per charge/grant.
CREATE TABLE IF NOT EXISTS credit_ledger (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    delta       NUMERIC(14, 4) NOT NULL,   -- negative = spend, positive = grant
    rung        TEXT,
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_tenant_time ON credit_ledger(tenant_id, created_at);

-- Append-only audit log (REQ-M11-007): admin actions, key issuance, money tools.
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   UUID REFERENCES tenants(id) ON DELETE SET NULL,
    actor       TEXT NOT NULL,             -- 'operator' | 'system' | tenant slug
    action      TEXT NOT NULL,
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON audit_log(tenant_id, created_at);

INSERT INTO schema_migrations (version) VALUES ('0004_billing_audit_governance')
    ON CONFLICT (version) DO NOTHING;
