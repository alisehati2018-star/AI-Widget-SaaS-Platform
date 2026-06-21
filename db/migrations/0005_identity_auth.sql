-- Phase 5 — Identity, Auth, Plans & Subscriptions (M9/M11 human-facing layer).
-- Adds people (users + roles), session/refresh-token storage, password resets,
-- public plan pricing for the marketing site, and a payment-provider-agnostic
-- subscription + order model for the self-serve "buy a plan" flow.
-- Control-plane only (PostgreSQL); no shopper/catalogue data here (§3.4).

-- People who log in: platform admins (no tenant) and store owners/staff (one tenant).
CREATE TABLE IF NOT EXISTS users (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email              TEXT NOT NULL UNIQUE,
    password_hash      TEXT NOT NULL,
    full_name          TEXT,
    role               TEXT NOT NULL CHECK (role IN ('platform_admin', 'store_owner', 'store_staff')),
    tenant_id          UUID REFERENCES tenants(id) ON DELETE CASCADE,
    status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'pending')),
    email_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    failed_logins      INTEGER NOT NULL DEFAULT 0,
    locked_until       TIMESTAMPTZ,
    last_login_at      TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- A tenant user MUST have a tenant; a platform admin MUST NOT.
    CONSTRAINT users_tenant_role_ck CHECK (
        (role = 'platform_admin' AND tenant_id IS NULL)
        OR (role <> 'platform_admin' AND tenant_id IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users(lower(email));

-- Refresh-token sessions: only the token's jti hash is stored; tokens are
-- single-use (rotated on refresh) and revocable (logout / security events).
CREATE TABLE IF NOT EXISTS auth_sessions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti_hash           TEXT NOT NULL UNIQUE,
    user_agent         TEXT,
    ip                 INET,
    expires_at         TIMESTAMPTZ NOT NULL,
    revoked            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);

-- Single-use password-reset tokens (only the hash is stored).
CREATE TABLE IF NOT EXISTS password_resets (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash         TEXT NOT NULL UNIQUE,
    expires_at         TIMESTAMPTZ NOT NULL,
    used_at            TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_password_resets_user ON password_resets(user_id);

-- Public pricing surface for the marketing site (plans table already exists).
ALTER TABLE plans ADD COLUMN IF NOT EXISTS description       TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_monthly     NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS currency          TEXT NOT NULL DEFAULT 'USD';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS credits_per_month NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS is_public         BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS sort_order        INTEGER NOT NULL DEFAULT 100;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS features          JSONB NOT NULL DEFAULT '[]'::jsonb;

-- A tenant's current plan enrolment.
CREATE TABLE IF NOT EXISTS subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id             UUID NOT NULL REFERENCES plans(id),
    status              TEXT NOT NULL DEFAULT 'trialing'
                        CHECK (status IN ('trialing', 'active', 'past_due', 'canceled')),
    current_period_end  TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_tenant ON subscriptions(tenant_id);

-- Payment-provider-agnostic orders for the "buy plan" flow. The provider field
-- lets us wire Stripe / ZarinPal / manual-invoice later without schema change.
CREATE TABLE IF NOT EXISTS orders (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id            UUID NOT NULL REFERENCES plans(id),
    amount             NUMERIC(12, 2) NOT NULL,
    currency           TEXT NOT NULL DEFAULT 'USD',
    status             TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'paid', 'failed', 'refunded')),
    provider           TEXT NOT NULL DEFAULT 'manual',
    provider_ref       TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at            TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_orders_tenant_time ON orders(tenant_id, created_at);

-- Seed the public plan catalogue (idempotent on plan code).
INSERT INTO plans (code, name, description, price_monthly, currency, credits_per_month,
                   monthly_credit_cap, rate_limit_per_min, is_public, sort_order, features)
VALUES
  ('free', 'Free', 'Try Persian hybrid search on one store.', 0, 'USD', 5000,
   5000, 60, TRUE, 10,
   '["1 store","Hybrid Persian search","5k AI credits/mo","Community support"]'::jsonb),
  ('starter', 'Starter', 'For growing stores that want the shopping assistant.', 49, 'USD', 50000,
   50000, 120, TRUE, 20,
   '["1 store","Search + RAG assistant","50k AI credits/mo","Analytics dashboard","Email support"]'::jsonb),
  ('pro', 'Pro', 'Full intelligence layer with insight + lead capture.', 149, 'USD', 250000,
   250000, 600, TRUE, 30,
   '["3 stores","Everything in Starter","Insight & lead engine","250k AI credits/mo","Priority support"]'::jsonb),
  ('enterprise', 'Enterprise', 'On-prem, SSO, custom limits and SLA.', 0, 'USD', 0,
   1000000, 2000, TRUE, 40,
   '["Unlimited stores","Self-hosted models","SSO + audit","Custom SLA","Dedicated support"]'::jsonb)
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name, description = EXCLUDED.description,
  price_monthly = EXCLUDED.price_monthly, credits_per_month = EXCLUDED.credits_per_month,
  is_public = EXCLUDED.is_public, sort_order = EXCLUDED.sort_order, features = EXCLUDED.features;

INSERT INTO schema_migrations (version) VALUES ('0005_identity_auth')
    ON CONFLICT (version) DO NOTHING;
