-- Fully separate platform admins (operators) from store users (customers):
-- a dedicated table + a dedicated session table, so the admin identity plane
-- shares no row, no query, and (at the API layer) no auth endpoint with the
-- tenant/customer plane. Idempotent: safe to re-run after the source rows
-- have already been migrated out of `users`.

CREATE TABLE IF NOT EXISTS admin_users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    full_name      TEXT,
    status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended')),
    failed_logins  INTEGER NOT NULL DEFAULT 0,
    locked_until   TIMESTAMPTZ,
    last_login_at  TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_users_email_lower ON admin_users(lower(email));

-- Refresh-token sessions for the admin plane, mirroring `auth_sessions` but
-- keyed to `admin_users` — no foreign key ever crosses between the two planes.
CREATE TABLE IF NOT EXISTS admin_sessions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id  UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    jti_hash       TEXT NOT NULL UNIQUE,
    user_agent     TEXT,
    ip             INET,
    expires_at     TIMESTAMPTZ NOT NULL,
    revoked        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_user ON admin_sessions(admin_user_id);

-- One-time data move: any existing platform_admin rows in `users` become the
-- source of truth in `admin_users`. Naturally idempotent — once moved, the
-- WHERE role = 'platform_admin' source set is empty on subsequent runs.
INSERT INTO admin_users
    (id, email, password_hash, full_name, status, failed_logins, locked_until, last_login_at, created_at, updated_at)
SELECT id, email, password_hash, full_name, status, failed_logins, locked_until, last_login_at, created_at, updated_at
FROM users WHERE role = 'platform_admin'
ON CONFLICT (email) DO NOTHING;

DELETE FROM users WHERE role = 'platform_admin';

-- `users` now holds store owners/staff only — every row must belong to a tenant.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_tenant_role_ck;
ALTER TABLE users ALTER COLUMN tenant_id SET NOT NULL;

INSERT INTO schema_migrations (version) VALUES ('0011_admin_users')
    ON CONFLICT (version) DO NOTHING;
