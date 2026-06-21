-- Phase A — email verification tokens + contact-form messages.
-- Control-plane only. Tokens are stored hashed (never raw).

CREATE TABLE IF NOT EXISTS email_verifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_email_verifications_user ON email_verifications(user_id);

-- Public contact-form submissions (for the record + operator follow-up).
CREATE TABLE IF NOT EXISTS contact_messages (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    message     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_contact_messages_time ON contact_messages(created_at);

INSERT INTO schema_migrations (version) VALUES ('0007_email_verification_contact')
    ON CONFLICT (version) DO NOTHING;
