-- ACIP Phase 1 — sync reconciliation state (M3: REQ-M3-002)
-- Per-tenant/source high-watermark for delta reconciliation + backfill.
-- Control-plane metadata only.

CREATE TABLE IF NOT EXISTS sync_state (
    tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source         TEXT NOT NULL,                       -- opencart | woocommerce | rest
    high_watermark TIMESTAMPTZ,                         -- max store updated_at seen
    last_run_at    TIMESTAMPTZ,
    last_status    TEXT,
    PRIMARY KEY (tenant_id, source)
);

-- Optional per-tenant webhook secret for signature verification (GAP-B6).
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS webhook_secret TEXT;

INSERT INTO schema_migrations (version) VALUES ('0002_sync_state')
    ON CONFLICT (version) DO NOTHING;
