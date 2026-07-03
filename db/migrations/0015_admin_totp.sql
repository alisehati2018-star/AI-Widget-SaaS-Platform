-- 0015: TOTP two-factor auth for platform admins (Phase 9 hardening).
-- totp_secret is set at enrollment; totp_enabled flips only after the admin
-- confirms a live code, so a half-finished enrollment never locks anyone out.
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS totp_secret TEXT;
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;

INSERT INTO schema_migrations (version) VALUES ('0015_admin_totp')
ON CONFLICT (version) DO NOTHING;
