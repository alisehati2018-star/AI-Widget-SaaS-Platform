-- AI provider registry + token-based pricing (FinOps completion).
-- Replaces the env-only single-frontier config with a DB-backed, admin-managed
-- registry: providers → models (with real per-1M-token provider costs) →
-- ordered routes per task, plus platform-wide pricing (credit value + margin).
-- usage_events gains provider/model/provider_cost so every call carries its
-- actual COGS next to the credits charged — the basis of the profit report.

-- Providers: one row per API vendor (OpenAI-compatible) or local endpoint.
CREATE TABLE IF NOT EXISTS ai_providers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL DEFAULT 'openai-compatible'
                CHECK (kind IN ('openai-compatible', 'local')),
    base_url    TEXT NOT NULL,
    api_key     TEXT NOT NULL DEFAULT '',   -- returned masked by the API
    is_local    BOOLEAN NOT NULL DEFAULT FALSE,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    timeout_s   NUMERIC(6, 2) NOT NULL DEFAULT 30,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Models: what each provider serves, at what provider cost (USD per 1M tokens,
-- the industry-standard unit on every provider price sheet).
CREATE TABLE IF NOT EXISTS ai_models (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id        UUID NOT NULL REFERENCES ai_providers(id) ON DELETE CASCADE,
    model              TEXT NOT NULL,
    label              TEXT,
    input_usd_per_1m   NUMERIC(14, 6) NOT NULL DEFAULT 0,
    output_usd_per_1m  NUMERIC(14, 6) NOT NULL DEFAULT 0,
    enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider_id, model)
);
CREATE INDEX IF NOT EXISTS idx_ai_models_provider ON ai_models(provider_id);

-- Routes: per task, the ordered chain of models to try (position 0 first).
-- Tasks: 'chat' (assistant frontier chain), 'analyst' (admin insight engine).
-- Embedding/rerank stay env-configured (they are local infra, not per-call
-- token-metered vendors) until a vendor need appears.
CREATE TABLE IF NOT EXISTS ai_routes (
    task      TEXT NOT NULL,
    position  INTEGER NOT NULL,
    model_id  UUID NOT NULL REFERENCES ai_models(id) ON DELETE CASCADE,
    PRIMARY KEY (task, position)
);

-- Platform pricing: single row. usd_per_credit sets what one credit is worth;
-- margin_percent is the platform markup applied on top of provider cost when
-- converting to credits; search_credits is the flat price of a search call;
-- local_*_usd_per_1m attribute an (electricity/amortisation) cost to the
-- owned local model so its margin is honest instead of implicitly 100%.
CREATE TABLE IF NOT EXISTS pricing_settings (
    id                    BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
    usd_per_credit        NUMERIC(14, 8) NOT NULL DEFAULT 0.0001,
    margin_percent        NUMERIC(6, 2)  NOT NULL DEFAULT 30,
    search_credits        NUMERIC(10, 4) NOT NULL DEFAULT 0.01,
    local_input_usd_per_1m  NUMERIC(14, 6) NOT NULL DEFAULT 0,
    local_output_usd_per_1m NUMERIC(14, 6) NOT NULL DEFAULT 0,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO pricing_settings (id) VALUES (TRUE) ON CONFLICT (id) DO NOTHING;

-- Every usage event now records which vendor/model served it and the actual
-- provider cost (USD) — `cost` keeps meaning credits charged to the tenant.
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS provider      TEXT;
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS model         TEXT;
ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS provider_cost NUMERIC(14, 8) NOT NULL DEFAULT 0;

INSERT INTO schema_migrations (version) VALUES ('0018_ai_providers_pricing')
    ON CONFLICT (version) DO NOTHING;
