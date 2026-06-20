# ACIP — AI Commerce Intelligence Platform

On-premise, multi-tenant **Persian hybrid search + grounded RAG shopping
assistant + analytics** for OpenCart / WooCommerce stores, built on
**Elasticsearch** with a local-first, cost-controlled AI gateway.

> **Status:** all development phases (0–4) are **code-complete and statically
> verified** — `ruff` + `mypy` clean (78 files), **81 unit tests pass**, frontend
> `tsc` clean. Runtime/performance **acceptance is not yet validated** (needs a
> live cluster + real catalogue + self-hosted models). See
> `reports/blueprint-compliance-audit.md` and `reports/deferred-validation.md`.

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

# Operator dashboard (Next.js):
cd apps/dashboard && npm install && npm run dev
```

You can then open:

| What | URL |
|---|---|
| API + interactive Swagger docs | http://localhost:8000/docs |
| Operator dashboard (console / synonyms) | http://localhost:3000/console |
| Kibana (runs in Docker) | http://localhost:5601 |

Create a tenant + API key (operator token from `.env`):

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

# Frontend: dashboard UI dev server + typecheck (API calls will fail without the backend)
cd apps/dashboard && npm install && npm run dev      # http://localhost:3000
npx tsc --noEmit
```

## Repository layout

```
ACIP-Blueprint.docx   Authoritative spec (source of truth)
docs/generated/       Requirements, phase plans, traceability, gap analysis, v2 roadmap
packages/             Domain libs: acip_core, acip_search, acip_sync, acip_embedding,
                      acip_cache, acip_gateway, acip_assistant, acip_analytics, acip_billing
services/             api · gateway · worker (FastAPI + Celery)
apps/dashboard/       Next.js operator console + embeddable widget (widget/acip-widget.ts)
db/migrations/        PostgreSQL control-plane schema (0001–0004)
eval/                 Golden-set metrics + evaluation harness
infra/                docker-compose.yml, Dockerfile, cluster verify script
tests/                Unit + ES-gated integration tests
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
