# ACIP — AI Commerce Intelligence Platform

An on-premise, multi-tenant **Persian hybrid search + grounded RAG shopping
assistant + analytics** layer for OpenCart / WooCommerce stores, engineered on
**Elasticsearch 9.2+** with a local-first, cost-controlled AI gateway.

> **Status: Phase 0 (Setup & Discovery) foundation.** This repository currently
> contains the planning suite (`docs/generated/`) and the Phase-0 infrastructure
> + scaffolding. No feature logic (search, RAG, sync) is implemented yet — those
> belong to Phases 1–3. See `docs/generated/master-implementation-plan.md`.

## Repository layout

```
ACIP-Blueprint.docx        Authoritative spec (source of truth)
docs/generated/            Requirements, phases, tasks, traceability, gap analysis, master plan
docs/phase-0-kpi-targets.md  The §18 KPI contract
packages/acip_core/        Shared lib: config, logging, tracing, health, security, datastore clients
services/api/              Public API (FastAPI): /healthz, /readyz, /v1/*, /admin/* (skeletons)
services/gateway/          AI gateway shell (FastAPI)
services/worker/           Celery worker bootstrap
apps/dashboard/            Next.js operator dashboard (foundation only)
db/migrations/             PostgreSQL control-plane schema (tenants, keys, plans, usage)
eval/                      Golden-set metrics + evaluation harness (quality backbone)
infra/                     Docker Compose topology, Dockerfile, cluster verify script
tests/                     Unit + smoke tests
.github/workflows/ci.yml   CI baseline gate
reports/                   Per-phase audits & completion reports
```

## Tech stack (Phase 0 decisions)

- **Backend:** Python 3.12 + FastAPI (async); Celery worker.
- **Frontend:** Next.js + React + TypeScript.
- **Data spine:** Elasticsearch 9.2+ (DiskBBQ, kNN, RRF, ACORN — used from Phase 1).
- **Control plane:** PostgreSQL 16. **Cache/queue:** Redis 7.
- **Inference (compose-only in P0):** TEI embeddings/reranker, vLLM LLM.
- **Observability:** OpenTelemetry + structlog + Kibana.

## Quick start (development)

```bash
cp .env.example .env                 # set passwords; never commit .env
pip install ".[dev]"                 # backend deps
pytest -q                            # run unit + smoke tests

# Bring up the core stack (inference services are opt-in via --profile inference):
docker compose -f infra/docker-compose.yml up -d elasticsearch kibana postgres redis api gateway
python infra/scripts/verify_cluster.py   # validate the cluster (T-P0-001)
curl -s localhost:8000/healthz           # API liveness
curl -s localhost:8000/readyz            # API readiness (checks ES/PG/Redis)
```

Only `api` (8000), `gateway` (8080), and `kibana` (5601) publish host ports;
the datastores and model servers stay on the internal network (REQ-M1-009).

## Development discipline

One phase at a time, behind approval gates. Before each phase: re-read the
blueprint + `requirements.md` + `traceability-matrix.md` + the phase doc, and
verify scope boundaries. See `docs/generated/` for the full plan.
