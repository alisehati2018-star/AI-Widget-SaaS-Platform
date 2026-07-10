-- AI routing v2: provider quick-setup/retry knobs, model modality (for
-- embedding/rerank routing), and a dedicated signup-credit policy.
-- Extends 0018_ai_providers_pricing.sql — see docs/PRODUCT-STRATEGY.md's
-- "multi-provider distribution + failover" section for the design intent.

-- Provider-level knobs for vendor quick-setup (which discovery quirk to use
-- when fetching its live model list) and per-endpoint retry-before-failover.
ALTER TABLE ai_providers
    ADD COLUMN IF NOT EXISTS discover_kind TEXT NOT NULL DEFAULT 'openai_compatible'
        CHECK (discover_kind IN
            ('openai_compatible', 'openrouter', 'google', 'bynara', 'conduit')),
    ADD COLUMN IF NOT EXISTS max_retries SMALLINT NOT NULL DEFAULT 0
        CHECK (max_retries BETWEEN 0 AND 5),
    ADD COLUMN IF NOT EXISTS retry_backoff_ms INTEGER NOT NULL DEFAULT 250
        CHECK (retry_backoff_ms BETWEEN 0 AND 10000);

-- What "shape" a model serves. Lets the routing UI/registry offer
-- embedding/rerank sections (not just chat/analyst) and, for embeddings,
-- record the vector dimension so an admin can't route to a model whose
-- output size doesn't match the ES index's fixed dense_vector dimension.
ALTER TABLE ai_models
    ADD COLUMN IF NOT EXISTS modality TEXT NOT NULL DEFAULT 'chat'
        CHECK (modality IN ('chat', 'embedding', 'rerank')),
    ADD COLUMN IF NOT EXISTS dims INTEGER;

-- Dedicated signup-credit policy — deliberately its own table, separate from
-- `pricing_settings` (credit *value*/margin) and independent of
-- `plans.credits_per_month` (a plan's advertised monthly allowance): this is
-- the one-time grant a brand-new self-serve signup receives immediately,
-- admin-editable on its own.
CREATE TABLE IF NOT EXISTS signup_credit_policy (
    id                  BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
    auto_grant_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
    signup_credits      NUMERIC(14, 2) NOT NULL DEFAULT 5000,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO signup_credit_policy (id) VALUES (TRUE) ON CONFLICT (id) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES ('0019_ai_routing_v2')
    ON CONFLICT (version) DO NOTHING;
