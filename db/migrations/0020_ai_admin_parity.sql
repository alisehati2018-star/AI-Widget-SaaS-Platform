-- AI admin parity pass: bring the provider/model/routing admin surface to
-- full feature parity with the reviewed reference product's admin UX
-- (quick templates, discovery, credit check, priority display, context
-- window, and an eligibility-annotated use-case binding editor) while
-- keeping Vitrin's own (cleaner) single ordered-chain-per-task design —
-- see 0018/0019 for the tables this extends.

-- `priority` is informational/display ordering for the provider list (and a
-- sensible default sort when picking a provider to bind) — NOT a second,
-- competing failover mechanism; Vitrin's one ordered chain per task
-- (`ai_routes`) is the single source of truth for failover order.
ALTER TABLE ai_providers
    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 0;

-- `context_window` mirrors the reference product's per-model field so the
-- admin model form/table can show and edit it (purely informational —
-- nothing in the gateway enforces it today). `is_free_tier` flags models
-- with no real per-token cost (auto-derived on discovery-import when both
-- costs are zero) so the Models page can badge/filter free vs. paid models.
ALTER TABLE ai_models
    ADD COLUMN IF NOT EXISTS context_window INTEGER,
    ADD COLUMN IF NOT EXISTS is_free_tier BOOLEAN NOT NULL DEFAULT FALSE;

-- Global kill-switch for cross-endpoint failover/retry: when disabled, the
-- registry only ever tries the first (primary) endpoint of a chain — no
-- retry, no falling over to position 2+. Per-provider `max_retries` still
-- governs retry COUNT when this is on; this is the master on/off switch.
CREATE TABLE IF NOT EXISTS ai_routing_settings (
    id                 BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
    failover_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO ai_routing_settings (id) VALUES (TRUE) ON CONFLICT (id) DO NOTHING;

INSERT INTO schema_migrations (version) VALUES ('0020_ai_admin_parity')
    ON CONFLICT (version) DO NOTHING;
