-- 0016: TOTP replay guard (Phase 9 re-verification hardening).
-- Persist the last accepted time step per admin; a code at or before it is
-- rejected, so a sniffed 6-digit code can never be replayed inside the
-- clock-skew window.
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS totp_last_step BIGINT NOT NULL DEFAULT 0;

INSERT INTO schema_migrations (version) VALUES ('0016_totp_replay_guard')
ON CONFLICT (version) DO NOTHING;
