# Phase 0 — Self-Audit

> Audit of the Phase-0 (Setup & Discovery) implementation against
> `docs/generated/phase-0.md` and `docs/generated/tasks-phase-0.md`. Honest
> status: artifacts are authored, statically validated (ruff clean, 11 unit/
> smoke tests passing, compose + eval harness run), but **live infra bring-up
> was not executed** — this container has no Docker daemon. Live verification
> (cluster health, migrations applied, probes against real dependencies) runs
> in an environment with Docker.

## Verification performed in this environment
- `ruff check .` → all checks passed.
- `python -m pytest -q` → **11 passed** (metrics unit tests + API smoke tests).
- `python -m eval.run_eval --golden …` → harness runs, emits NDCG/precision/
  zero-result (0.0 with the Phase-0 `EmptyProvider`, as expected — no search
  backend until M5).
- `python eval/embedding_eval.py` → candidate matrix renders.
- `docker-compose.yml` parses; 10 services present.
- Service imports (`api.main`, `gateway.main`, `worker.celery_app`) succeed.

## Task-by-task status

| Task | Requirement(s) | Status | Evidence / Notes |
|---|---|---|---|
| T-P0-001 ES cluster (free tier) | REQ-M1-001/008 | ◑ Scaffolded | `infra/docker-compose.yml` (es 9.2, single-node, free tier) + `infra/scripts/verify_cluster.py`. Needs Docker to bring up + verify health. |
| T-P0-002 ES security + TLS + secrets | REQ-M1-003/010 | ◑ Partial | `xpack.security.enabled=true`, `ELASTIC_PASSWORD` from env; `.env.example` + `.gitignore` keep secrets out. **CA-verified TLS certs are documented for prod, not wired into the dev compose.** |
| T-P0-003 Compose topology | REQ-M1-002 | ✅ Done | 10-service compose; shared `infra/Dockerfile.python`. |
| T-P0-004 PostgreSQL + base schema | REQ-M1-004 | ✅ Done | `db/migrations/0001_init_control_plane.sql` (tenants, plans, api_keys, usage_events). Auto-applied via initdb mount. |
| T-P0-005 Redis | REQ-M1-005 | ✅ Done | compose service + `acip_core.clients.redis`. |
| T-P0-006 Inference hosts + relay/mirror | REQ-M1-006/007 | ◑ Partial | embeddings/reranker/llm services behind `inference` profile; **relay/mirror is documented, not implemented.** |
| T-P0-007 Network segmentation | REQ-M1-009 | ✅ Done | only api/gateway/kibana publish ports; datastores + model servers internal-only. |
| T-P0-008 CI + observability | REQ-M12-008/011/012 | ◑ Partial | `.github/workflows/ci.yml` (lint→type→test) + Kibana service + OTel deps + structlog. **OTel exporter endpoint not yet wired to a collector.** |
| T-P0-009 Probes + logging/trace | REQ-M12-003/004 | ✅ Done | `/healthz` + `/readyz` (ES/PG/Redis checks) + trace-id middleware + JSON logs; covered by smoke tests. |
| T-P0-010 Golden set (~50 judged) | REQ-M12-009 | ◑ Partial | Format (`schema.json`), 5-row example, and docs present. **The real ~50-query judged set is not in the repo** (needs a real pilot store — ASM-4, GAP-B7). |
| T-P0-011 Eval harness | REQ-M12-009 | ✅ Done | `eval/metrics.py` (NDCG@k, precision@k, zero-result) + `eval/run_eval.py` + unit tests. |
| T-P0-012 Embedding decision | REQ-M4-001/003 | ◑ Partial | `eval/embedding_eval.py` candidate matrix + `eval/decision-log.md` template. **Decision pending** live models + golden set (GAP-A1). |
| T-P0-013 KPI sheet | §18 | ✅ Done | `docs/phase-0-kpi-targets.md`. |

Legend: ✅ done · ◑ partial (scaffolded, needs runtime/data to complete).

## Completed items
- Monorepo structure (services / packages / apps / infra / db / eval / tests / CI).
- Shared `acip_core` lib: config, JSON logging + trace id, readiness registry,
  error envelope, security key-shape, ES/PG/Redis client factories.
- FastAPI **api** (health + `/v1/*` + `/admin/*` skeletons returning 501) and
  **gateway** shell; **Celery** worker bootstrap with health task.
- PostgreSQL control-plane schema (tenants, plans, api_keys, usage_events).
- Docker Compose topology with network segmentation; shared Python image.
- Golden-set format + evaluation harness + metrics (unit-tested).
- Next.js dashboard foundation; CI baseline gate; KPI contract; README.

## Missing / not-yet-complete items
1. **Live cluster bring-up + verification** — requires a Docker runtime
   (unavailable here). Run `docker compose … up` + `verify_cluster.py`.
2. **Real golden set (~50 judged Persian queries)** — blocked on a real pilot
   store (ASM-4); owner + refresh cadence undefined (GAP-B7).
3. **Embedding-model decision** — needs candidates run against the real golden
   set on the inference services (GAP-A1); decision-log is a template.
4. **Production TLS certificates** — dev compose uses bundled security only;
   CA-verified transport+HTTP TLS to be wired (REQ-M1-003).
5. **Relay/mirror** for models/packages under constrained connectivity —
   documented, not implemented (REQ-M1-007, ASM-2).
6. **OpenTelemetry export pipeline** — deps + service names in place; collector
   endpoint not yet connected (REQ-M12-004/011).

## Architectural risks / notes
- **Scope discipline held:** no Persian analyzer/mapping (M2), no search/RAG/
  sync logic — those are Phase 1+. `/v1/*` and `/admin/*` are 501 skeletons.
- **RISK-O1/O3 (inference + connectivity):** inference services are
  `--profile inference` opt-in and heavy; relay/mirror still needed before they
  can be pulled reliably in the target network.
- **RISK-O4 (isolation):** the `tenant_id` filter / isolation invariant is
  **not** active yet (correctly — M11/Phase 3, asserted from first multi-tenant
  query in Phase 1). API-key handling is a non-enforcing stub by design.
- **Runtime parity:** local interpreter is Python 3.11; Docker/CI use 3.12.
  `requires-python = >=3.11` keeps both valid; code uses no >3.11 features.
- **DB migration tooling:** ordered SQL now; introduce Alembic at the first
  programmatic schema change (Phase 1/3).

## Conclusion
Phase 0 **foundation is in place and statically green**. The remaining items
are runtime/data-dependent (live cluster, real golden set, model decision) and
are explicitly the Phase-0 exit-gate activities that require a Docker host and a
pilot store. Recommend completing those in a Docker-enabled environment, then
proceeding to the Phase-0 approval gate before Phase 1.

**STOP — awaiting approval before Phase 1 (per the development rules).**
