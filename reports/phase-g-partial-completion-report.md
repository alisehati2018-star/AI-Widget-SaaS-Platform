# Phase G (partial) — Validation & Acceptance (ES deferred) — Completion Report

> Plan ref: `reports/recovery-plan-80plus.md` (VA-1..VA-5, IN-1/IN-3). Per owner
> instruction, **Elasticsearch-dependent validation is deferred** (golden set,
> NDCG, search/RAG KPIs, true vLLM streaming) until the real ES server is
> connected. This phase delivers the **ES-free** validation: an automated
> PG-backed integration suite, a CI integration job, and a load harness.

## Delivered

### Automated PG-backed integration suite (VA-4/IN-1/IN-3)
`tests/integration/test_pg_flows.py` — the manual curl validations are now
automated, executed **over HTTP against a real uvicorn subprocess** on a live
Postgres (own process/loop, exactly like production). Skips when PG is
unreachable (`live_client` fixture). Covers:
- signup → login → `/auth/me`;
- **tenant isolation** (two owners get distinct tenants, see only their own);
- **RBAC** (owner JWT blocked from `/admin`, operator token allowed);
- **email-verification gate** on checkout (403 → verify → 200);
- **full billing lifecycle** (checkout → admin mark-paid → active + invoice +
  50k credits; proration preview; signed-webhook upgrade; top-up +50k; invoices;
  cancel/resume);
- **webhook bad-signature → 401**.

### Two real bugs found + fixed by the suite
1. **`auth_sessions.ip` (INET) insert failure** — a non-IP client host (proxy /
   test client) raised `asyncpg.DataError`. Fixed: `_client_ip` validates with
   `ipaddress` and stores NULL when the host isn't a valid IP.
2. **CSRF over-blocking public endpoints** — a stale session cookie made
   unauthenticated POSTs (signup/login/webhook) fail CSRF. Fixed: CSRF now
   exempts `/auth/*`, `/billing/webhook`, `/contact` (their action is
   authenticated by body/credentials/signature, not the session cookie); the
   protected `/tenant/*` and `/admin/*` cookie surfaces remain enforced.

### CI integration job
`.github/workflows/ci.yml` integration job now also spins up **postgres:18** +
**redis:8** service containers, **applies all migrations** (asyncpg), runs the
PG flow tests, and a **load smoke** (`eval.load_test` on `/healthz`). ES service
+ relevance dry-run remain for when ES validation resumes.

### Load harness (RE-4, ES-free)
`eval/load_test.py` — async throughput/latency (p50/p95/p99) against cheap
endpoints. Local run: `/healthz` 3000 req @ 50 concurrency → **0 errors, ~550
rps, p95 ≈ 128 ms** (single dev worker). Full search/SLO load runs later on ES.

## Validation results (live)
- **PG integration suite: 6/6 pass** over real HTTP + live Postgres.
- Full suite: **109 passed, 3 skipped** (ES integration skipped, as expected).
- `ruff` clean, `mypy` clean (92 files).

## Score impact (per plan)
- Reliability/validation now have automated, repeatable evidence for the entire
  control plane (auth, isolation, RBAC, billing). Production Readiness rises;
  overall **~79 → ~80/100**.
- **Still capped (deferred):** Search, AI Assistant, and Analytics KPIs depend on
  Elasticsearch + inference and are intentionally **not** validated yet.

## Deferred (per owner instruction) — to run against the real ES server
- Persian golden set + NDCG@10; search p95 / first-token SLOs; cost-regression
  replay; ES-backed tenant-isolation integration test; true vLLM token streaming;
  ES snapshots. Tracked in `reports/deferred-validation.md`.
