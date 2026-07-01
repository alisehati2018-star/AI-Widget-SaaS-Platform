# Vitrin — AI Commerce Intelligence Platform

On-premise, multi-tenant **Persian hybrid search + grounded RAG shopping
assistant + analytics** for OpenCart / WooCommerce stores, built on
**Elasticsearch** with a local-first, cost-controlled AI gateway.

> **Vitrin** is the product brand; `acip_*` packages / `REQ-M*` IDs are the
> internal codename. Authoritative spec: `docs/PRODUCT.md` +
> `docs/PRODUCT-STRATEGY.md` (the old `.docx` "blueprint" is historical input).

> **Status:** the search/RAG/analytics engine (phases 0–4) is **code-complete
> and statically verified**. The human-facing layer (Phase 5 **identity & auth**
> + the **marketing site, store-owner dashboard, and platform admin panel** in
> `apps/web`) is implemented and builds clean. Gates: `ruff` + `mypy` clean (84
> files), **91 unit tests pass**, both frontends `tsc` + `next build` clean.
> Runtime/DB acceptance is validated where Postgres/ES are live
> (`reports/deferred-validation.md`). Plan: `docs/generated/expansion-plan-phases-5-8.md`.

## Tech stack (latest, mutually compatible)

| Layer | Tech |
|---|---|
| Backend | Python 3.13 · FastAPI 0.138 · Celery 5.6 |
| Frontend | Next.js 16 · React 19 · TypeScript 6 |
| Search / vectors | Elasticsearch 9.4 (BM25 + dense_vector + RRF, DiskBBQ, ACORN) |
| Control plane | **PostgreSQL 18** · Cache/queue: **Redis 8** |
| Inference (self-hosted) | TEI (BGE‑M3 / reranker) · vLLM (Qwen3/Gemma) — Docker only |
| Observability | OpenTelemetry · structlog · Kibana |

## Run it

> **Elasticsearch, Kibana, PostgreSQL and Redis run inside Docker** — they are
> **not** started by the bare Python/Node commands. For anything beyond unit
> tests and the dashboard UI you need Docker.

### Method A — With Docker (full stack, recommended)

```bash
cp .env.example .env          # set ES_PASSWORD, PG_PASSWORD, ADMIN_TOKEN, …

# Core stack: Elasticsearch + Kibana + PostgreSQL 18 + Redis 8 + API + gateway + worker
docker compose -f infra/docker-compose.yml up -d
curl -s localhost:8000/readyz   # API readiness — reports ES/PG/Redis status

# (optional, heavy) self-hosted models for real search/chat:
docker compose -f infra/docker-compose.yml --profile inference up -d

# Web app (marketing site + signup/login + store dashboard + admin panel):
cd apps/web && npm install && npm run dev          # http://localhost:3000
```

> Set `AUTH_SECRET` in `.env` (e.g. `openssl rand -hex 32`) so login/signup can
> issue tokens — empty fails closed. The web app proxies `/api/*` to the backend
> (`API_ORIGIN`, default `http://localhost:8000`), so no CORS setup is needed.

You can then open:

| What | URL |
|---|---|
| Marketing site (landing / pricing) | http://localhost:3000 |
| Sign up / sign in | http://localhost:3000/signup · `/login` |
| Store-owner dashboard | http://localhost:3000/dashboard |
| Platform admin panel | http://localhost:3000/admin (`/admin/login`) |
| API + interactive Swagger docs | http://localhost:8000/docs |
| Kibana (runs in Docker) | http://localhost:5601 |

Create the first **platform admin** (operator token from `.env`), then sign in
at `/admin/login`:

```bash
curl -X POST http://localhost:8000/admin/auth/bootstrap \
  -H "x-admin-token: $ADMIN_TOKEN" -H "content-type: application/json" \
  -d '{"email":"admin@vitrin.ai","password":"ChangeMe-Str0ng!","full_name":"Admin"}'
```

Store owners self-serve via the **Sign up** page (provisions a tenant + trial).
A tenant + scoped API key can still be minted directly for automation:

```bash
curl -X POST http://localhost:8000/admin/tenants \
  -H "x-admin-token: $ADMIN_TOKEN" -H "content-type: application/json" \
  -d '{"slug":"shop1","name":"Test Shop","scope":"widget"}'   # returns api_key
```

Only `api` (8000), `gateway` (8080) and `kibana` (5601) publish host ports; the
datastores and model servers stay on the internal network.

### Method B — Without Docker (limited: code + UI only)

No Docker ⇒ no Elasticsearch/PostgreSQL/Redis/Kibana, so `/v1/*` and `/admin/*`
that hit datastores won’t return data. Useful for development/inspection:

```bash
# Backend: install, lint, type-check, unit tests (hermetic — no services needed)
pip install ".[dev]"
ruff check . && mypy packages services eval && pytest -q

# Run the API process (only /healthz works without datastores; /readyz reports "degraded")
PYTHONPATH=packages:services python -m uvicorn api.main:app --port 8000

# Frontend: the product web app (marketing + auth + dashboards + admin panel)
cd apps/web && npm install && npm run dev      # http://localhost:3000
npx tsc --noEmit
```

## Repository layout

```
docs/PRODUCT*.md      Authoritative product spec + strategy (Vitrin)
docs/generated/       Requirements, phase plans, traceability, expansion plan (5–8)
packages/             Domain libs: acip_core, acip_auth, acip_search, acip_sync,
                      acip_embedding, acip_cache, acip_gateway, acip_assistant,
                      acip_analytics, acip_billing
services/             api · gateway · worker (FastAPI + Celery) — incl. auth/admin/public routers
apps/web/             Next.js app: marketing site + auth + store dashboard + admin panel
apps/dashboard/       Legacy operator console + embeddable widget (widget/acip-widget.ts)
db/migrations/        PostgreSQL control-plane schema (0001–0009: identity/auth/plans/billing/kb)
eval/                 Golden-set metrics + evaluation harness
infra/                docker-compose.yml, Dockerfile, cluster verify script
tests/                Unit + PG/ES integration tests
reports/              Audits, compliance, gap-closure, dependency upgrade
```

## Notes

- API surface (§12): `/v1/search`, `/v1/suggest`, `/v1/chat` (+ `/chat/stream`),
  `/v1/sync/{webhook,bulk}`, `/admin/*`, `/healthz`, `/readyz`.
- Tenant isolation is a hard invariant (mandatory `tenant_id` filter + scoped
  keys + a release-blocking isolation test).
- Real Persian search and the AI assistant need the **inference profile**
  (self-hosted models) and a synced catalogue — part of the pending Validation
  phase.
