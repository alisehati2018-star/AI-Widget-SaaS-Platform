-- Phase B — knowledge base (assistant grounding content) + feature flags.
-- Control-plane only.

-- Per-tenant knowledge-base articles the assistant can ground answers on
-- (FAQ, policies, guides) — complements the synced catalogue.
CREATE TABLE IF NOT EXISTS kb_articles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    published   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kb_articles_tenant ON kb_articles(tenant_id);

-- Platform feature flags (global on/off + optional description).
CREATE TABLE IF NOT EXISTS feature_flags (
    key         TEXT PRIMARY KEY,
    enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed the known toggles (idempotent).
INSERT INTO feature_flags (key, enabled, description) VALUES
  ('assistant_enabled', TRUE,  'Shopping assistant (RAG chat) available to tenants.'),
  ('insight_engine',    TRUE,  'Demand-gap / why-summary insight surfaces.'),
  ('lead_capture',      TRUE,  'In-conversation lead capture.'),
  ('agent_actions',     FALSE, 'Money-moving agent actions (order/payment/discount).'),
  ('signups_open',      TRUE,  'Self-serve signup is open to the public.')
ON CONFLICT (key) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES ('0008_kb_feature_flags')
    ON CONFLICT (version) DO NOTHING;
