# Phase G-Preflight — Runtime Bring-Up Completion Report

> Plan ref: `reports/recovery-plan-80plus.md` (IN-1 + partial VA-4). First-ever
> runtime execution of the control plane. Date: 2026-06-21. HEAD `28653df`.

## Environment (no Docker)

The managed container's Docker daemon is **down**, so the stack was brought up
natively from the tools that *are* present:

| Component | Used | Notes |
|---|---|---|
| PostgreSQL | **16.13** (local cluster, port 5432) | Production target is **18**; migrations use only features valid on both. |
| Redis | 8-compatible `redis-server` (6379) | `PING → PONG`. |
| API | uvicorn `api.main:app` (8000) | Live against PG + Redis. |
| Elasticsearch | **not available** | No ES binary; Java 21 present but ES not installed. Search/RAG/analytics paths therefore unvalidated. |

## What was validated (PASS)

### Schema / migrations — first runtime execution
- All **6 migrations (0001→0006) applied cleanly** on real Postgres.
- 15 tables created: `tenants, plans, api_keys, usage_events, schema_migrations,
  sync_state, leads, credit_ledger, audit_log, users, auth_sessions,
  password_resets, subscriptions, orders, invitations`.
- `schema_migrations` records all 6 versions; plan catalogue seeded
  (free/starter/pro/enterprise with prices + credits).

### Health
- `/healthz` → `{"status":"ok"}`.
- `/readyz` → `postgres: ok, redis: ok, elasticsearch: unavailable` (degraded,
  correct). Confirms the **`elasticsearch[async]`/aiohttp fix at runtime** —
  `AiohttpHttpNode` connects (and fails only because ES is absent), no import error.

### Identity & auth (live PG)
- `bootstrap-admin` (operator token) → platform admin created.
- `signup` → tenant + store_owner + trial subscription provisioned atomically.
- `login` → access+refresh issued; `/auth/me` resolves the principal.
- **Refresh rotation + reuse detection:** first refresh OK; replay of the used
  token → **401**.
- **Brute-force lockout:** 5 bad logins → **429 account_locked**.

### Authorization / RBAC
- Admin endpoint via platform_admin JWT → **200** (dual-auth works).
- Same endpoint via store_owner JWT → **401**; via no auth → **401**.
- Tenant endpoint with no token → **401**.

### Tenant-scoped operations (live PG)
- `/tenant/profile`, `/tenant/keys` (create returns one-time raw key) work and
  are scoped to the caller's tenant.

### Billing lifecycle (live PG)
- `checkout(pro)` → pending order, **server-authoritative price $149**.
- Admin `mark-paid` → subscription **active**, **250 000 credits granted**.
- **Signed webhook** (HMAC-SHA256) → `starter` activated; **bad signature → 401**.
- `/admin/overview` → tenants 1, users 2, active_subscriptions 1, MRR 49;
  `/admin/orders` revenue_total 198 over 2 orders.

### Static suite
- `93 passed, 3 skipped` (unchanged); ruff/mypy clean.

## Findings (to feed later phases — NOT fixed in preflight)

| ID | Sev | Finding | Fix location |
|---|---|---|---|
| GP-1 | **Medium** | JSONB columns returned as **strings** (`/tenant/profile` → `"settings":"{}"`), because no JSON codec is registered on the asyncpg pool. Frontend treats `settings` as an object (`settings.platform`), so catalog/widget pages would misbehave. | `packages/acip_core/clients.py` `get_pg_pool` → `connection.set_type_codec('jsonb'/'json', json.loads/dumps)`. Fold into Phase B. |
| GP-2 | Expected | ES absent → `/v1/search` 500, and `/v1/chat`, `/v1/suggest`, `/tenant/analytics`, `/admin/analytics`, insight all **unvalidated**. | Requires ES 9.x (Docker or local install) — Phase G full validation. |
| GP-3 | Note | Validated on PG16; production target PG18. Migrations valid on both; re-confirm on PG18 at full validation. | Phase G. |
| GP-4 | Note | `subscriptions` has `UNIQUE(tenant_id)`; a second paid order upserts/replaces the active plan (correct for single-subscription model). | none |

## Outcome

IN-1 (runtime bring-up) is **substantially complete for the control plane**:
auth, RBAC, tenant scoping, and the full manual-billing lifecycle are now
**runtime-proven**, not just statically green. The **data plane (ES: search,
RAG, analytics)** remains unvalidated pending an Elasticsearch instance.

**Next per plan:** fix GP-1 opportunistically, then proceed to Phase A
(product completeness) — stopping for approval after each phase. Full ES-backed
validation (golden set, KPIs, isolation on a live cluster) is the Phase-G exit.
