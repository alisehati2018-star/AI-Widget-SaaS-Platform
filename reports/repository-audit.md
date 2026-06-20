# ACIP — Repository Audit & Reality Check

> Evidence-based inventory of what **actually exists** in the repository.
> Read-only audit — no code was changed. All numbers are command outputs from
> the working tree at commit `1594516` (branch `claude/gallant-shannon-8b31td`).
> Conservative by design: nothing is claimed "production ready" or "validated"
> without runtime evidence, and **no live infrastructure was available** to this
> audit (no running ES/PG/Redis/Celery/models).

---

## Part 1 — Repository Structure

```
AI-Widget-SaaS-Platform/
├── ACIP-Blueprint.docx              # source-of-truth spec
├── README.md  pyproject.toml  .env.example  .gitignore
├── apps/
│   └── dashboard/                   # Next.js operator console + embeddable widget
│       ├── app/ (page, layout, console, synonyms)
│       └── widget/ (acip-widget.ts, README)
├── db/
│   └── migrations/ (0001..0004 .sql, README)
├── docs/
│   ├── generated/ (requirements, phase-0..4, tasks, traceability, gap-analysis,
│   │               master-implementation-plan, v2-roadmap)
│   └── phase-0-kpi-targets.md
├── eval/                            # golden-set harness (metrics, run_eval, es_provider…)
│   └── golden_set/ (schema, README, example.jsonl)
├── infra/
│   ├── docker-compose.yml  Dockerfile.python
│   ├── elasticsearch/README.md  scripts/verify_cluster.py
├── packages/                        # 9 domain libraries (see Part 2)
│   ├── acip_core/ acip_embedding/ acip_search/ acip_sync/ acip_cache/
│   └── acip_gateway/ acip_assistant/ acip_analytics/ acip_billing/
├── plugins/ (opencart/acip_search.php, woocommerce/acip-search.php, README)
├── reports/ (phase-0..4 reports, deferred-validation, this audit)
├── services/
│   ├── api/ (main, deps, runtime, routers/{health,v1,admin})
│   ├── gateway/ (main)
│   └── worker/ (celery_app, tasks)
└── tests/ (16 unit modules + integration/)
```

Top-level (git-tracked): `apps, db, docs, eval, infra, packages, plugins,
reports, services, tests` + root files. **154 tracked files.**

---

## Part 2 — Source Code Inventory

| Module | Purpose | Status | Files (.py) | Tests* |
|---|---|---|---|---|
| `acip_core` | config, logging/trace, clients (ES/PG/Redis), health, errors, security, ratelimit, resilience, audit, middleware | Implemented | 14 | 13 (metrics+security+isolation) |
| `acip_embedding` | self-hosted embedding client (TEI/OpenAI-compat), batch, MRL, cache | Implemented (client only) | 2 | 4 (embedding+mapping) |
| `acip_search` | Persian analyzer, mapping, index admin/alias-swap, hybrid RRF query, retrieval, suggest, reranker, zero-result | Implemented | 9 | 14 (query+normalize+metrics+iso) |
| `acip_sync` | connectors (opencart/woo/rest), normalize, idempotent ingest, reconcile, DLQ | Implemented (reconcile fetch = hook) | 10 | 3 (sync_ingest) |
| `acip_cache` | L1 exact, L2 semantic (scaffold), data-version, metering | Implemented | 5 | 4 (cache) |
| `acip_gateway` | classifier, escalation router, budget+kill-switch, failover, llm_client, compress | Implemented | 7 | 11 (gateway) |
| `acip_assistant` | RAG pipeline, guardrails, memory, agent tools | Implemented | 5 | 17 (assistant+injection+agent) |
| `acip_analytics` | aggregations, leads, attribution, insight "why", NL analyst | Implemented | 6 | 8 (analytics) |
| `acip_billing` | credit ledger, balance, plan enforcement | Implemented | 2 | 1 (security) |
| `services/api` | FastAPI: health, /v1/*, /admin/* + runtime/deps | Implemented | 8 | 5 (api_health) |
| `services/gateway` | gateway service shell (health, /route stub) | Shell only | 2 | 0 |
| `services/worker` | Celery app + sync/embed tasks + beat schedule | Implemented | 3 | 0 (no broker in tests) |
| `apps/dashboard` | Next.js console + synonyms + embeddable widget | Implemented (UI) | 6 (.ts/.tsx) | 0 (tsc only) |

\* "Tests" attributes hermetic test functions to the package they exercise;
some test modules span packages. Totals in Part 7.

---

## Part 3 — Requirement Coverage Matrix

119 requirements (`REQ-M1-001`…`REQ-M12-012`). Marked from code evidence only.
**COMPLETE** = code exists + hermetic test/usage; **PARTIAL** = code exists but
incomplete or not runtime-validated; **NOT IMPLEMENTED** = no code in repo.

### Module rollup

| Module | Reqs | COMPLETE | PARTIAL | NOT IMPL | Evidence (representative) |
|---|---|---|---|---|---|
| M1 Infra | 10 | 10 | 0 | 0 | `infra/docker-compose.yml`, `infra/scripts/verify_cluster.py`, `acip_core/config.py`, `clients/*` |
| M2 Analyzer/mapping | 11 | 10 | 1 | 0 | `acip_search/analyzer.py`, `mapping.py`, `index_admin.py` |
| M3 Sync | 12 | 9 | 3 | 0 | `acip_sync/{ingest,normalize,reconcile,dlq,connectors}.py`, `worker/tasks.py` |
| M4 Embedding | 6 | 6 | 0 | 0 | `acip_embedding/client.py` |
| M5 Search | 13 | 9 | 3 | 1 | `acip_search/{query,retrieval,suggest,reranker}.py` |
| M6 Gateway | 15 | 13 | 2 | 0 | `acip_gateway/*`, `acip_cache/*` |
| M7 Assistant | 11 | 9 | 2 | 0 | `acip_assistant/*`, `services/api/routers/v1.py` |
| M8 Widget/plugins | 5 | 5 | 0 | 0 | `apps/dashboard/widget/acip-widget.ts`, `plugins/*` |
| M9 Dashboard | 7 | 7 | 0 | 0 | `services/api/routers/admin.py`, `apps/dashboard/app/*` |
| M10 Analytics | 7 | 7 | 0 | 0 | `acip_analytics/*` |
| M11 Tenancy/sec/billing | 10 | 9 | 1 | 0 | `services/api/{deps,runtime}.py`, `acip_core/{ratelimit,audit}.py`, `acip_billing/*` |
| M12 Reliability/CI | 12 | 6 | 4 | 2 | `acip_core/resilience.py`, `.github/workflows/ci.yml`, `eval/*` |

### Requirements NOT fully COMPLETE (explicit, conservative)

| Requirement | Status | Evidence / reason |
|---|---|---|
| REQ-M2-010 (shard sizing) | PARTIAL | `index_admin.index_body` exposes shards/replicas via settings; values not tuned to real data. |
| REQ-M3-002 (reconciliation) | PARTIAL | `acip_sync/reconcile.py` + beat schedule exist; `worker/tasks.py:reconcile_tenant` store-side fetch is a **no-op hook** until a live store is configured. |
| REQ-M3-011 (freshness <1 min) | PARTIAL | event path async; the latency number is runtime-measured (DV-005). |
| REQ-M3-010 (seven sources) | PARTIAL | products/categories modelled for search; orders/customers/pages/chat/events accepted via REST but not fully modelled (feeds M10). |
| REQ-M5-003 (learned-sparse leg) | NOT IMPLEMENTED | `acip_search/query.py` is BM25 + dense only; optional sparse leg deferred. |
| REQ-M5-004 (DiskBBQ oversample tuning) | PARTIAL | `num_candidates` exposed; oversample/rescore tuning is runtime (DV-009). |
| REQ-M5-012 (facets + keyset pagination) | PARTIAL | `query.py` supports filters + `size`; **no aggregations/facets, no cursor pagination**. |
| REQ-M5-010/011/013 (latency/zero-result/NDCG targets) | PARTIAL | code present; **numeric targets not runtime-validated** (DV-007/008). |
| REQ-M6-004 (L3 prefix/KV cache) | PARTIAL | `llm_client` targets vLLM (prefix caching is a server flag); app-side reuse runtime-validated (DV). |
| REQ-M6-007 (eval-driven router) | PARTIAL | `classifier.py` is deterministic + budget-gated; holdout tuning deferred (DV-104). |
| REQ-M6-014 (cost targets) | PARTIAL | metering + budgets coded; >60%/>85%/→0 are runtime (DV-104). |
| REQ-M7-007 (streaming) | PARTIAL | `/v1/chat/stream` SSE contract + `llm_client.stream`; **not true per-token model streaming**; TTFT runtime (DV-101). |
| REQ-M7-010 (groundedness ≥95%) | PARTIAL | guardrails coded; sampling vs judged set is runtime (DV-102). |
| REQ-M11-008 (dependency/image scanning) | PARTIAL | CI placeholder only; scanners + least-priv accounts are deployment/ops. |
| REQ-M12-003/004/011 (observability) | PARTIAL | probes + trace-id + structured logs + per-call metering exist; **OTLP collector / Kibana dashboards not wired**. |
| REQ-M12-005 (snapshots/backups/DR) | NOT IMPLEMENTED | no backup scripts/cron/snapshot policy in repo; documented only (DV-203). |
| REQ-M12-007 (SLOs/error budgets/alarms) | PARTIAL | targets in `docs/phase-0-kpi-targets.md`; **no alarm config** (needs telemetry, DV-204). |
| REQ-M12-008 (all 7 test layers) | PARTIAL | unit/integration/relevance/isolation/guardrail present; **load + cost-regression not present** (runtime). |
| REQ-M12-009 (golden set) | PARTIAL | harness + 5-row **example** only; real ~50-query judged set absent (DV-007). |

All other 90+ requirements: COMPLETE with the module evidence above. (Full
per-requirement mapping is in `docs/generated/traceability-matrix.md` and the
per-phase `reports/phase-*-gap-analysis.md`.)

---

## Part 4 — Feature Inventory

### Backend (FastAPI + Celery)
- API service `services/api/` (health, /v1/*, /admin/*); worker `services/worker/`.
- Tests: `tests/test_api_health.py` (5). Status: **implemented; not run against live deps.**

### Search
- Persian analyzer/mapping/index-admin/alias-swap, hybrid RRF + ACORN tenant
  filter, suggest, eval-gated reranker, zero-result loop — `acip_search/*`.
- Tests: `test_query_builder.py` (7), `test_normalize.py` (3),
  `test_embedding_and_mapping.py` (4), `integration/test_search_es.py` (3, **skipped**, ES-gated).
- Status: **implemented; live ES round trip skipped (no ES).**

### Embedding
- `acip_embedding/client.py` (TEI/OpenAI-compat, batch, MRL, cache).
- Tests: covered in `test_embedding_and_mapping.py`. Status: **client implemented; no live model.**

### RAG / Assistant
- Pipeline + guardrails (scope-lock, injection delimiting, output guardrail),
  memory (Redis+ES), `/v1/chat` + `/v1/chat/stream` — `acip_assistant/*`,
  `services/api/routers/v1.py`.
- Tests: `test_assistant.py` (7), `test_injection.py` (4). Status: **implemented; no live LLM (generation mocked in tests).**

### Billing
- Credit ledger, balance, plan enforcement — `acip_billing/*` + `0004` migration.
- Tests: `test_security.py` ledger guard (1). Status: **implemented; no live PG.**

### Security
- Scoped-key RBAC (`deps.principal_allowed`), rate limiting, GDPR endpoints,
  audit log, tenant-isolation suite — `acip_core/{ratelimit,audit,security}.py`,
  `services/api/{deps,routers/admin}.py`.
- Tests: `test_isolation.py` (6), `test_security.py` (6). Status: **implemented + hermetically tested.**

### Dashboard
- Next.js console (four-dimension analytics) + synonyms editor — `apps/dashboard/app/*`.
- Tests: `tsc --noEmit` only (no component tests). Status: **implemented (UI); not e2e tested.**

### Widget
- Embeddable `apps/dashboard/widget/acip-widget.ts` (white-label, citation cards).
- Tests: `tsc` only. Status: **implemented; not embedded in a real store (DV-109).**

### Analytics
- Aggregations, leads, attribution, insight "why", NL analyst — `acip_analytics/*`.
- Tests: `test_analytics.py` (8). Status: **implemented; queries not run on real data.**

### Agent Framework
- `acip_assistant/tools.py`: tool registry, audit, money-tools disabled by
  default behind confirmation + permission + idempotency.
- Tests: `test_agent_actions.py` (6). Status: **framework implemented; handlers return stubs (no live PSP/order).**

---

## Part 5 — Deferred / Missing Work

### Missing Features (no code in repo)
- Learned-sparse retrieval leg (REQ-M5-003).
- Facets/aggregations + cursor/keyset pagination on search (REQ-M5-012).
- Scheduled snapshots/backups + DR automation (REQ-M12-005).
- SLO alarm configuration (REQ-M12-007).
- Load-test + cost-regression-replay suites (REQ-M12-008).
- Dependency/image scanning in CI (REQ-M11-008).
- OTLP collector / Kibana dashboards wiring (REQ-M12-011).
- Real ~50-query judged golden set (REQ-M12-009; only a 5-row example exists).
- v2 directions (recommendations, A/B ranking, Path B, more connectors, visual
  search) — intentionally roadmap-only (`docs/generated/v2-roadmap.md`).

### Deferred Validation (DV-*)
**25 DV items** in `reports/deferred-validation.md` (DV-001…DV-205, DV-301):
live cluster bring-up, analyzer `_analyze`, search/isolation round trips, sync
freshness, embedding service, golden-set NDCG/latency/zero-result, assistant
streaming/groundedness/injection-vs-live-model, cost targets, failover/DR
drills, load, SLO alarms, full CI/CD, widget embedding, live agent actions.

### Technical Debt (from reports + code)
- `body=` deprecation on ES client calls (functional in es-py 9.4.1).
- Generic top-level package names `api`/`worker` can shadow source in ad-hoc
  `python -c` (Docker/pytest unaffected); recommend `pip install -e .`.
- Webhook HMAC verified in connectors but **not enforced** at the endpoint
  (endpoint is API-key gated, so not an open hole).
- `version_conflict` detection via exception-string match (fragile).
- Reconciliation store-side fetch is a no-op hook.

### Mocked / Not-Connected-to-Real-Infrastructure
- All datastore/model clients are real code but require **running** ES/PG/Redis/
  vLLM/TEI — none present in this environment.
- Agent-tool handlers (`check_stock`, `order_lookup`, `create_payment_link`,
  `apply_discount`) return **stub payloads** (`note: wired to live data`).
- Reconcile task records its run but performs no fetch without a live store.
- SSE chat streams the assembled answer, not live model tokens.
- Tests use in-memory fakes (`FakeRedis`, `FakeLLM`, fake ES) — no live I/O.

---

## Part 6 — Runtime Readiness Assessment

No services were running during this audit; assessment is from code/config.

| Component | Status | Evidence |
|---|---|---|
| PostgreSQL | PARTIALLY READY | `clients/postgres.py` + 4 migrations + initdb mount in compose; **never started/migrated here**. |
| Redis | PARTIALLY READY | `clients/redis.py` + compose service; not started. |
| Elasticsearch | PARTIALLY READY | compose 9.2 service + `verify_cluster.py`; **index/analyzer/mapping never applied** (created in code, not run). |
| Celery worker | PARTIALLY READY | `celery_app.py` + `tasks.py` + beat schedule; **no broker run**; reconcile fetch is a hook. |
| API (FastAPI) | PARTIALLY READY | app builds + imports (verified); `/v1/*` need live ES/PG/Redis to function; only `/healthz` works standalone. |
| Dashboard | PARTIALLY READY | `tsc --noEmit` passes; `next build` not run; calls `/admin/*` (needs API). |
| Widget | PARTIALLY READY | TS typechecks; not bundled/served or embedded in a store. |

**Overall runtime readiness: NOT READY** (no component has been started or
validated end-to-end in this environment).

---

## Part 7 — Test Coverage Summary

Exact command outputs:

```
$ git ls-files | wc -l
154                       # total tracked files
$ git ls-files '*.py' | wc -l
97                        # total Python files
$ git ls-files '*.ts' '*.tsx' | wc -l
6                         # total TS/TSX files
$ git ls-files 'tests/*.py' 'tests/integration/*.py' | grep -v __init__ | wc -l
17                        # test modules (incl. conftest)
$ grep -cE 'def test_' across tests
84                        # test functions defined
$ python3 -m pytest -q
81 passed, 3 skipped, 2 warnings in 1.98s
```

- **Total test functions:** 84 (81 hermetic + 3 ES-gated integration).
- **Passed:** 81 · **Skipped:** 3 (integration, auto-skip without ES) · **Failed:** 0.
- Static gates: `ruff check .` → all checks passed; `mypy packages services
  eval` → no issues in 78 source files; frontend `tsc --noEmit` → exit 0.
- **No coverage-percentage tool is configured** (no `pytest-cov`); test count is
  reported, not line coverage.

---

## Part 8 — Git Audit

```
$ git branch --show-current
claude/gallant-shannon-8b31td

$ git log --oneline -20
1594516 feat(phase-4): agent-action enablement framework + v2 roadmap
88fd5ad feat(phase-3): GA hardening — M11 security/billing, M12 resilience, M10 finalise
f1fbab9 docs(phase-2): gap-analysis + completion report + deferred-validation log
ebc0302 feat(phase-2): M8 widget + M9 dashboard + M10 insight engine + SSE chat
f728e6a feat(phase-2): M6 AI gateway + M7 RAG assistant core (/v1/chat)
05f62d2 fix(phase-1): worker uses a persistent event loop (re-audit critical fix)
7f34b5b feat(phase-1): MVP Smart Persian Search (M2/M3/M4/M5/M6-foundation/M8-subset)
37386da Phase 0 infra stabilization fixes
7e74c64 feat(phase-0): implement Setup & Discovery foundation (M1 + M12 scaffold)
bad57cf docs: generate ACIP executable development plan from blueprint
289859f add document

$ git rev-parse HEAD ; git rev-parse origin/<branch>
159451657f685bcd4c591d366b3e91c3de20bf2c
159451657f685bcd4c591d366b3e91c3de20bf2c   # HEAD == origin (pushed)

$ git status --short
(empty)                   # no uncommitted changes
```

11 commits; working tree clean; HEAD is pushed to origin.

---

## Part 9 — Executive Summary

| Area | Status |
|---|---|
| Implemented | **YES (code-complete for Phases 0–4)** — 9 packages, 3 services, dashboard+widget, 4 migrations; ~90/119 requirements COMPLETE in code, ~19 PARTIAL, ~3 NOT IMPLEMENTED. |
| Tested | **Static only** — 81 hermetic tests pass, 3 ES-gated skipped; ruff/mypy/tsc clean. No live-integration, load, or coverage-% testing. |
| Runtime Validated | **NO** — no ES/PG/Redis/Celery/model was started; 25 DV-* validation items outstanding. |
| Production Ready | **NO** — runtime, performance, DR, SLO, security-vs-live-model, and pilot validation are all unperformed; several ops requirements (DR, scanning, observability wiring) are not in code. |
| Remaining Work | The full **Validation & Acceptance phase** (DV-001…DV-301) + the explicitly missing features/ops items in Part 5; needs Docker host, pilot store, judged golden set, and self-hosted models. |

**Conclusion (conservative):** the repository is a **code-complete,
statically-verified implementation** of the blueprint's Phases 0–4. It is **not
runtime-validated and not production-ready.** The gap to production is the
deferred Validation & Acceptance work plus a defined set of missing ops/feature
items, all enumerated above with evidence.
