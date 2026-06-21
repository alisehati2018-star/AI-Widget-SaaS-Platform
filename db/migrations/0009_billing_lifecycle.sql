-- Phase E — billing lifecycle: order kind/credits + invoices.
-- Control-plane only. Manual model (no live PSP); a signed webhook or operator
-- confirmation marks orders paid.

-- Distinguish plan purchases from credit top-ups, and carry top-up credit amount.
ALTER TABLE orders ADD COLUMN IF NOT EXISTS kind    TEXT NOT NULL DEFAULT 'subscription'
    CHECK (kind IN ('subscription', 'topup'));
ALTER TABLE orders ADD COLUMN IF NOT EXISTS credits NUMERIC(14, 2) NOT NULL DEFAULT 0;
-- Top-up orders carry no plan.
ALTER TABLE orders ALTER COLUMN plan_id DROP NOT NULL;

-- Invoices: one per paid order, with a human-friendly sequential number.
CREATE TABLE IF NOT EXISTS invoices (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    number      BIGINT GENERATED ALWAYS AS IDENTITY,
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_id    UUID REFERENCES orders(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    amount      NUMERIC(12, 2) NOT NULL,
    currency    TEXT NOT NULL DEFAULT 'USD',
    status      TEXT NOT NULL DEFAULT 'paid' CHECK (status IN ('paid', 'void')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_time ON invoices(tenant_id, created_at);

INSERT INTO schema_migrations (version) VALUES ('0009_billing_lifecycle')
    ON CONFLICT (version) DO NOTHING;
