# Phase 1 — Completion Report (MVP: Smart Persian Search)

## Scope delivered
M2 (Persian analyzer + catalogue mapping), M3 (event + reconciliation sync,
connectors, DLQ), M4 (self-hosted embedding client), M5 (hybrid RRF search,
ACORN tenant filter, suggest, rerank, zero-result, graceful degradation), M6
foundation (L1/L2 cache + data-version invalidation + usage metering), M8 subset
(pilot plugin scaffolds), the **M11-001 tenant-isolation invariant**, and M12
ongoing (alias-swap reindex, relevance CI gate, resilient fallbacks).

`/v1/chat` and all `/admin/*` remain `501` — scope held; no M7/M9/M10/M11-full
logic added.

## Implemented requirements
40+ requirements across M2–M6/M8/M11-001/M12 — see
`reports/phase-1-gap-analysis.md` for the line-by-line status (✅ done, ◑
partial, ❌ deferred, ⏳ runtime-gated).

## New code (domain packages, reusing `acip_core`)
- `packages/acip_embedding/` — embedding client (TEI, batch, MRL, cache).
- `packages/acip_search/` — `analyzer`, `mapping`, `index_admin` (alias swap),
  `query` (central tenant-scoped builder), `retrieval`, `suggest`, `reranker`,
  `zero_result`.
- `packages/acip_sync/` — `normalize`, `ingest` (idempotent), `reconcile`,
  `dlq`, `connectors/{base,opencart,woo,rest}`.
- `packages/acip_cache/` — `l1`, `l2`, `data_version`, `metering`.
- `services/api/` — real `/v1/search`, `/v1/suggest`, `/v1/sync/*` + `deps`
  (tenant resolution) + `runtime` (service wiring).
- `services/worker/tasks.py` — sync/embedding tasks + reconciliation beat.
- `db/migrations/0002_sync_state.sql`; `eval/es_provider.py`; `plugins/*`.

## Test results (this environment)
- **ruff**: clean.
- **mypy**: clean — 55 source files.
- **pytest**: **33 passed, 3 skipped** (the 3 skips are ES-gated integration
  tests — no Docker here).
- Unit coverage added: query-builder isolation invariant (7), connector
  normalization (3), ingest idempotency (3), cache keys/cosine (4), MRL +
  analyzer/mapping (4) — plus existing metrics (7) and API smoke (5).
- ES integration tests authored (ZWNJ/digit collapse, upsert→search,
  cross-tenant isolation) — run in CI's ES service job.
- Eval harness dry run executes; ES-backed provider wired for the live gate.

## Coverage status
- Static gates green. Relevance/latency gates are **runtime-gated** (live ES +
  real golden set) and wired into CI (`integration` job + relevance step).

## Risks / remaining issues
- **Runtime-gated exit criteria** (search p95/p99, suggest, zero-result, NDCG@10
  ≥ 0.80, one pilot live) need a Docker host + a pilot store (ASM-4). Not code
  defects; they are the human/runtime portion of the Phase-1 gate.
- **Deferred-in-phase:** learned-sparse leg (REQ-M5-003); DiskBBQ oversample
  tuning (REQ-M5-004); non-product source modelling (REQ-M3-010 → M10);
  webhook-signature *enforcement* at the endpoint (GAP-B6); true cursor
  pagination. All tracked in the gap analysis.
- **Resilience:** timeouts + bounded retries + graceful fallbacks in place;
  explicit circuit breakers are Phase-3 hardening (REQ-M12-002).
- **Tech debt:** stale local `pip install .` can shadow source; use
  `pip install -e .` locally (Docker image is correct).

## Open questions for the gate
1. Provide a pilot store + a real ~50-query judged golden set so the relevance/
   latency exit criteria can be measured (closes ASM-4, GAP-A1/A2).
2. Confirm whether webhook-signature enforcement should land now (security) or
   in Phase 3 hardening.

## Verification to run in a Docker/ES environment
```
docker compose -f infra/docker-compose.yml up -d elasticsearch postgres redis api worker
python infra/scripts/verify_cluster.py
# seed a tenant + api_key, create the index (acip_search.index_admin), bulk import,
curl -XPOST localhost:8000/v1/search -H 'x-api-key: <key>' -d '{"query":"کفش"}'
pytest -q tests/integration
python -m eval.run_eval --golden <real_golden_set>.jsonl --tenant <tenant_id>
```

**STATUS: Phase 1 code complete and statically green. STOP — awaiting approval
before Phase 2 (per the development rules).**
