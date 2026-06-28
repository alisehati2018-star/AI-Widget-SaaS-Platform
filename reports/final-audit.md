# Vitrin (ACIP) — Final Consolidated Audit (Phases A–G)

> Pre-Elasticsearch-validation audit. Scope: code, runtime, migrations, config,
> tests, deployment. Issues found during this audit were **fixed and
> re-validated** (see §"Fixes applied"). Date 2026-06-21. Branch
> `claude/gallant-shannon-8b31td`.
>
> Method: live stack (PostgreSQL 16 + Redis + uvicorn) + static gates + web
> build + automated integration suite. **Elasticsearch/inference intentionally
> not connected** (next phase).

## Verdict at a glance

| | |
|---|---|
| **Production readiness (control plane)** | **80 / 100** |
| **Go / No-Go for Elasticsearch validation phase** | **GO** ✅ |
| Static gates | ruff ✓ · mypy ✓ (92 files) |
| Tests | **110 passed, 3 skipped** (ES integration skips w/o ES) |
| Web | tsc ✓ · `next build` ✓ (47 routes) |
| Migrations | 9/9 apply cleanly on a real PG18-compatible server |

---

## Fixes applied during this audit (with re-validation)

| Fix | Type | Risk closed |
|---|---|---|
| Removed dead `auth._secret_or_503` | Dead code | Low |
| `.env.example`: added 11 missing keys (ES_INDEX_PREFIX, RERANK_WINDOW, LLM_MODEL, CHAT_MAX_TOKENS, BUDGET_DEFAULT_CAP, FRONTIER_*, AGENT_ACTIONS_ENABLED) | Config drift | **Medium** (ES/inference phase needs these) |
| README: `apps/dashboard`→`apps/web` (run cmd), migration range `0001–0009`, test desc | Doc drift | Low |
| Gateway app: added MetricsMiddleware + `/metrics` + security headers + OTel | Inconsistency (prometheus scraped a 404) | Medium |
| Added `/plans` + `/contact` integration tests | Test coverage gap | Low |

All gates re-run green after fixes (110 passed).

---

## PASS / WARNING / FAIL

### ✅ PASS
- **Identity & auth** — PBKDF2 (salted, rehash-on-login), HS256 access + rotating
  refresh w/ reuse-detection, lockout, no-enumeration; validated live.
- **Tenant isolation (control plane)** — `tenant_id` derived from the JWT
  principal, never client input; automated test proves two owners are isolated.
- **RBAC** — operator-token OR `platform_admin` dual-auth on `/admin/*`; owner
  JWT blocked (tested).
- **Billing lifecycle (manual model)** — checkout, server-priced orders,
  proration, signed-webhook activation, top-ups, invoices, cancel/resume,
  renewals, dunning, credit grants — **end-to-end automated (7/7 PG flows)**.
- **Security middleware** — CSP/headers, CORS allowlist, CSRF double-submit
  (cookie-auth only; public endpoints exempt), per-IP auth throttle.
- **Dashboards/Admin/UI/UX** — 47 routes; mobile drawer; RTL toggle; a11y
  (skip-link/focus/aria); onboarding wizard; consistent state primitives.
- **Observability** — `/metrics` (api + gateway), OTel instrumentation, readyz
  dependency gauges; validated.
- **DB schema** — 9 migrations apply cleanly; JSONB codec returns objects;
  asyncpg PG18-ready.
- **CI** — lint/type/unit + PG/Redis integration job (migrations + flows + load
  smoke) + dual frontend build.

### ⚠️ WARNING
- **Search / RAG / Analytics / Assistant streaming are unvalidated** — code-
  complete but require Elasticsearch + inference (deferred by decision). Scores
  for these areas are capped.
- ~~**Auth tokens still default to `localStorage`** in the web client~~ —
  **RESOLVED.** The web client now authenticates entirely via HttpOnly cookies
  (`vitrin_access`/`vitrin_refresh`) with a readable `vitrin_csrf` double-submit
  token; no token is stored in JS/`localStorage` and the bearer header is no
  longer sent, so `CsrfMiddleware` now actively enforces CSRF on unsafe
  cookie-auth requests. Validated end-to-end at runtime (signup→me→CSRF
  reject/accept→refresh→logout). For production set `COOKIE_SECURE=true` (HTTPS).
- **`/v1/*` (search/suggest/chat) return 500 when ES is absent** — acceptable
  pre-connection, but they are not "graceful 503" with a clear code; confirm
  graceful degradation (BM25-only when embeddings down) during ES bring-up.
- **CSRF exempts `/auth/*`** (incl. login) — standard, but login-CSRF is not
  mitigated; low severity given bearer default.
- **Billing is manual-only** — no live PSP, no invoice PDF (emailed HTML
  receipt + on-screen list only). By decision (BI-1 deferred to P3).
- **Admin API surface > UI** — `/admin/insight`, `/admin/analyst`,
  `/admin/zero-results` have no web UI (ES/LLM-dependent; intentional).
- **Renewals/dunning** run on a Celery beat **only if a worker+beat is running**;
  also exposed as admin-triggered endpoints. Ensure beat is deployed.

### ❌ FAIL
- None blocking. (No failing tests, no broken builds, no unapplied migrations,
  no orphaned/dead routes after fixes.)

---

## Domain review summaries

**Security** — Strong control-plane posture (isolation, hashing, rotation+reuse
detection, lockout, audit, headers, CORS, CSRF, IP throttle). Residual: token
storage cutover, MFA (P3), GDPR retention/consent records (P2). Risk: **Medium**
(localStorage), otherwise Low.

**Billing & SaaS ops** — Full lifecycle on the manual model, server-authoritative
pricing, idempotent activation, invoices, dunning, scheduled jobs. Missing: live
PSP, invoice PDF, proration on downgrade refunds. Risk: **Low** (functionally
complete for manual operation).

**Dashboard / Admin / UI/UX** — Complete surfaces (store + admin), responsive,
RTL-ready, accessible, onboarding. ES-dependent panels show correct empty states.
Risk: **Low**.

**Reliability / Observability** — Metrics (api+gateway), tracing, alerts,
backups + runbook, scheduled jobs, load harness; resilience primitives present.
Missing (deferred): load/SLO test on real ES, worker-level queue inspect, DR
drill. Risk: **Low–Medium**.

**API & Database** — 80 endpoints / 7 routers, consistent error envelope, dual
auth, tenant scoping. 9 migrations, all applied; INET coercion + JSONB codec
fixed earlier; PG18-ready. Risk: **Low**.

---

## Technical debt & known limitations
1. ~~Web auth still uses `localStorage`~~ — DONE: full HttpOnly-cookie + CSRF cutover.
2. Assistant SSE streaming is chunked post-hoc, not true per-token vLLM streaming.
3. `apps/dashboard` legacy app retained (hosts the embeddable widget) — kept in CI.
4. Invoice = emailed HTML/receipt + list; no PDF.
5. ES-dependent admin endpoints lack UI (by design until ES connects).
6. Starlette TestClient deprecation warning (test-only).

---

## Remaining items by priority
- **P1:** connect Elasticsearch + inference and run search/RAG/analytics
  validation; confirm `/v1/*` graceful degradation; true vLLM streaming.
  (Frontend cookie cutover + remove localStorage — **done**.)
- **P2:** invoice PDF; GDPR retention/consent; worker-level queue inspect; DR drill.
- **P3:** live payment gateway (Stripe/ZarinPal); MFA/TOTP; multi-region.

---

## Blockers to watch when connecting the final Elasticsearch
1. **Index bootstrap** — templates/analyzer/mapping must be created on the live
   cluster before search works (M2 `index_admin`); not auto-created at boot.
2. **Graceful degradation** — verify search returns BM25-only (not 500) when
   embeddings/ES partially unavailable; harden `/v1/*` error codes.
3. **ES auth/TLS** — for a secured cluster set `ES_HOST=https://…`,
   `ES_USERNAME`/`ES_PASSWORD`, `ES_VERIFY_CERTS=true` (client already honors these).
4. **Embedding/LLM endpoints** — set `EMBEDDINGS_URL`/`RERANKER_URL`/`LLM_URL`
   (+ `--profile inference`) or external providers; dimension match (`EMBEDDING_DIMS`).
5. **Tenant filter on both retriever legs** — re-confirm the isolation invariant
   on a live index (ES-gated test exists).

None of these block *starting* the ES validation phase; they are its checklist.

---

## Production readiness scorecard (strict)

| Area | Score/10 |
|---|---|
| Backend architecture | 8 |
| Search engine | 6 (unvalidated — ES deferred) |
| AI assistant | 5 (unvalidated; faked streaming) |
| Dashboard (user) | 8.5 |
| Admin panel | 8.5 |
| Security | 8.5 |
| Billing | 7.5 |
| Analytics | 6 (unvalidated — ES deferred) |
| UI/UX | 8.5 |
| Reliability/observability | 8 |
| **Overall (control plane)** | **80/100** |

## Recommendation

**GO** to the Elasticsearch-connected validation phase. The control plane is
production-grade and automatically validated; the ES phase is the correct next
step and faces no configuration/auth blockers — only the bring-up checklist
above. Treat the WARNING items (token cutover, `/v1/*` graceful degradation,
true streaming) as the ES-phase entry tasks.
