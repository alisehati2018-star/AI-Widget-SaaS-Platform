# Control-plane migrations

Plain, ordered SQL migrations for the PostgreSQL control plane (REQ-M1-004).
Applied automatically on first boot via the `postgres` container's
`/docker-entrypoint-initdb.d` mount (see `infra/docker-compose.yml`).

| Version | Purpose | Phase |
|---|---|---|
| `0001_init_control_plane.sql` | tenants, plans, api_keys, usage_events, schema_migrations | 0 |

**Scope discipline:** control-plane metadata only. Catalogue, vectors,
chat-memory, and analytics live in Elasticsearch (§3.4). Billing ledger,
quotas, and isolation enforcement are added in Phase 3 (M11).

A migration tool (e.g. Alembic) is introduced when the first programmatic
schema change is needed; Phase 0 uses ordered SQL for simplicity.
