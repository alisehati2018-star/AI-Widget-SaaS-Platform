-- Phase 2 (admin revenue/inbox) — turn contact_messages into an operator inbox:
-- a triage status plus an internal reply note, both edited from /admin/contact.

ALTER TABLE contact_messages ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN ('new', 'read', 'resolved'));
ALTER TABLE contact_messages ADD COLUMN IF NOT EXISTS admin_note TEXT;
ALTER TABLE contact_messages ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_contact_messages_status ON contact_messages(status, created_at);

INSERT INTO schema_migrations (version) VALUES ('0013_contact_inbox')
    ON CONFLICT (version) DO NOTHING;
