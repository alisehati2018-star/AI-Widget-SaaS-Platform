-- ACIP control-plane base schema (Phase 0, T-P0-004 / REQ-M1-004)
-- Scope: tenants, plans, api_keys, usage. Control-plane metadata ONLY —
-- no shopper-facing/catalogue data lives in PostgreSQL (blueprint §3.4).
-- Billing ledger, quotas, and isolation enforcement are Phase 3 (M11);
-- this migration only establishes the foundational tables.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Plans: pricing/quota tiers (filled out in M11). Phase 0 = skeleton.
CREATE TABLE IF NOT EXISTS plans (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tenants: one store = one isolated tenant (§9.1).
CREATE TABLE IF NOT EXISTS tenants (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    plan_id       UUID REFERENCES plans(id),
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- API keys: scoped, least-privilege, bound to a tenant + role (§9.2).
-- Only a hash is stored, never the raw key. Verification logic is M11.
CREATE TABLE IF NOT EXISTS api_keys (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_hash      TEXT NOT NULL UNIQUE,
    scope         TEXT NOT NULL CHECK (scope IN ('widget', 'admin', 'sync')),
    label         TEXT,
    revoked       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);

-- Usage: per-call metering stream feed (one row per model/search call).
-- The AI gateway will populate this (REQ-M6-012). Phase 0 = table only.
CREATE TABLE IF NOT EXISTS usage_events (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    route         TEXT,
    rung          TEXT,
    tokens_in     INTEGER NOT NULL DEFAULT 0,
    tokens_out    INTEGER NOT NULL DEFAULT 0,
    cache_outcome TEXT,
    latency_ms    INTEGER,
    cost          NUMERIC(12, 6) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_usage_tenant_time ON usage_events(tenant_id, occurred_at);

-- Schema version bookkeeping.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version       TEXT PRIMARY KEY,
    applied_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO schema_migrations (version) VALUES ('0001_init_control_plane')
    ON CONFLICT (version) DO NOTHING;
