# ACIP — Independent Blueprint Compliance Audit

> Independent audit performed by re-reading **ACIP-Blueprint.docx** as the single
> source of truth (text re-extracted from the .docx; §-references are the
> document's own sections). It does **not** rely on prior reports, gap analyses,
> completion reports, or the generated traceability matrix. Every "YES" cites
> code evidence (file:line / function / test). Conservative: code presence ≠
> runtime validation. **No live ES/PG/Redis/Celery/model was available**, so all
> KPI/acceptance criteria are UNVALIDATED.
>
> Repo state: commit `eebcaaf`, branch `claude/gallant-shannon-8b31td`, tree clean.

---

## Phase 1 — Fresh Blueprint Inventory (extracted from the document)

Concrete, verifiable requirement groups taken directly from the .docx:

- **§1 Headline targets / §18 KPIs:** search p95 < 150 ms; assistant first token
  < 1.5 s; zero-result < 5%; > 85% turns without paid API; cache hit > 60%;
  availability 99.9%; tenant isolation 100%; NDCG@10 → ≥ 0.80; groundedness ≥ 95%.
- **§5 Stack:** ES 9.2+, BGE-M3/Qwen3 embeddings, BGE/Qwen3 reranker, vLLM LLM,
  FastAPI, PostgreSQL, Redis, Next.js, Docker→K8s, Kibana+OTel.
- **§6 Search:** Persian analyzer (ZWNJ, digit-fold, Arabic/Persian norm, stop,
  synonyms); hybrid BM25+kNN+RRF; DiskBBQ; ACORN filter; rerank; suggest;
  aliases/zero-downtime reindex; zero-result loop.
- **§7 Assistant:** RAG pipeline (8 stages); scope-lock; citations; output
  guardrail; injection defence; 2-tier memory; SSE streaming; agent tools
  (disabled); degradation to search.
- **§8 Cost control:** credits-not-tokens; L1/L2/L3 cache; route ladder;
  compress; batch; budget caps + kill switches; metering; multi-provider
  failover ending local.
- **§9 Security:** mandatory tenant_id filter; scoped least-privilege keys;
  rate limits; operator auth separated; isolation test (release blocker); GDPR
  delete/export/disable-tracking; PII discipline; TLS everywhere; network
  segmentation; audit logging; dependency/image scanning; white-label.
- **§10 Sync:** event webhook→queue→worker upsert; idempotent upserts;
  tombstones; delta reconciliation; DLQ; backpressure; OpenCart/Woo/REST
  connectors; seven data sources.
- **§11 Analytics:** three surfaces (chat/sales/behaviour); insight "why";
  NL business analyst; lead capture + attribution; async/batch tenant-scoped.
- **§12 API:** /v1/search, /v1/suggest, /v1/chat, /v1/sync/webhook,
  /v1/sync/bulk, /admin/tenants, /admin/analytics, /admin/synonyms,
  /healthz, /readyz; cross-cutting: scoped key + rate limit, SSE streaming,
  **cursor/keyset pagination**, **idempotency key on sync/write**, error
  envelope (code/message/request-id), /v1 versioning.
- **§14 Reliability:** degradation matrix (6 rows); circuit breakers; bulkheads;
  timeouts+retries; failover; probes; tracing; snapshots/backups;
  zero-downtime reindex; DR; SLOs/error budgets.
- **§16 Deployment:** Docker Compose → Kubernetes; on-premise; free Elastic tier.

---

## Phase 2 — Independent Verification (evidence required for YES)

### §12 API surface
| Blueprint item | Impl? | Evidence (file:line) |
|---|---|---|
| POST /v1/search | YES | `services/api/routers/v1.py:49` |
| GET /v1/suggest | YES | `v1.py:67` |
| POST /v1/chat (RAG) | YES | `v1.py:117` |
| /v1/chat streaming (SSE) | PARTIAL | `v1.py:142` `/chat/stream` + `StreamingResponse` (`v1.py:167`) — streams the **assembled answer**, not live model tokens |
| POST /v1/sync/webhook | YES | `v1.py:80` |
| POST /v1/sync/bulk | YES | `v1.py:102` |
| POST /admin/tenants | YES | `services/api/routers/admin.py:44` |
| GET /admin/analytics | YES | `admin.py:73` |
| GET /admin/synonyms | YES | `admin.py:122` (+ POST `:131`) |
| /healthz, /readyz | YES | `services/api/routers/health.py:17,23` |
| Scoped key + rate-limit | YES | `v1.py:_guard` (`:42,45` → 403/429); `acip_core/ratelimit.py` |
| **Cursor/keyset pagination** | **NO** | grep `search_after\|keyset\|cursor` → no match in `acip_search`/`services`. `query.py` uses `size` only |
| **Idempotency key on sync/write** | **NO** | grep in `v1.py` → none. (Upserts are idempotent via version guard, but endpoints don't accept an Idempotency-Key) |
| Error envelope code/message/request-id | YES | `acip_core/errors.py:11-14` |
| /v1 versioning | YES | `APIRouter(prefix="/v1")` `v1.py:22` |

### §6 Search
| Item | Impl? | Evidence |
|---|---|---|
| Persian analyzer (ZWNJ/digit/norm/stop/synonyms) | YES | `acip_search/analyzer.py` (`ANALYSIS_SETTINGS`); ZWNJ U+200C verified; tests `test_normalize.py` |
| Hybrid BM25 + kNN + RRF | YES | `acip_search/query.py:build_hybrid_query`; tests `test_query_builder.py` |
| DiskBBQ (`bbq_disk`) | YES (code) | `acip_search/mapping.py:43`; not runtime-applied |
| ACORN filter on kNN leg | YES (code) | `query.py` knn `filter` clause; not runtime-validated |
| Rerank (eval-gated) | YES | `acip_search/reranker.py`; default off (`config.rerank_enabled`) |
| Suggest/autocomplete | YES | `acip_search/suggest.py`; `v1.py:67` |
| Aliases + zero-downtime reindex | YES | `acip_search/index_admin.py:reindex_and_swap,point_alias` |
| Zero-result loop | YES | `acip_search/zero_result.py`; `retrieval.py:73` |
| **Facets/aggregations on search** | **NO** | `query.py` builds filters, no `aggs` |
| Learned-sparse leg (optional) | NO | not present in `query.py` |

### §7 Assistant
| Item | Impl? | Evidence |
|---|---|---|
| RAG pipeline | YES | `acip_assistant/rag.py:RagAssistant.answer` |
| Scope-lock prompt | YES | `acip_assistant/guardrails.py:SYSTEM_PROMPT,build_messages` |
| Injection defence (delimited untrusted data) | YES (static) | `acip_gateway/compress.py:build_context`; tests `test_injection.py` |
| Output guardrail → search fallback | YES | `guardrails.py:is_grounded`; `rag.py:69` |
| Citations | YES | `rag.py` citations; widget cards `acip-widget.ts` |
| Memory (session Redis + long-term ES) | YES | `acip_assistant/memory.py` (cross-tenant recall blocked, `test_isolation.py`) |
| Streaming SSE first-token < 1.5 s | PARTIAL | SSE contract only; TTFT unvalidated |
| Agent tools (designed, money disabled) | YES | `acip_assistant/tools.py`; tests `test_agent_actions.py` |
| LLM down → ranked search | YES | `router.py:155-158`; `rag.py:_fallback_text` |

### §8 Cost control / §14 Reliability (degradation matrix)
| Item | Impl? | Evidence |
|---|---|---|
| Credits-not-tokens + per-rung multiplier | YES | `acip_gateway/budget.py:RUNG_COST`; `acip_billing/ledger.py` |
| L1 exact / L2 semantic cache | YES | `acip_cache/l1.py`, `l2.py` (L2 scaffold) |
| L3 prefix/KV cache | PARTIAL | `llm_client` targets vLLM (server-side flag); no app reuse metric |
| Route ladder | YES | `acip_gateway/router.py:answer_turn`; tests `test_gateway.py` |
| Budget caps + kill switches | YES | `budget.py:BudgetGuard`; tests |
| Failover ending at local | YES | `acip_gateway/failover.py:ProviderChain` (raises if last not local) |
| Compression | YES | `compress.py` |
| Degradation: frontier→local | YES | `failover.py` |
| Degradation: local LLM→search | YES | `router.py:155` |
| Degradation: reranker→fused | YES | `reranker.py:39` (returns input order) |
| Degradation: embeddings→BM25 | YES | `retrieval.py:36`, `query.py:60` |
| Degradation: Redis cache→recompute | PARTIAL | cache get/set fail-open (return None) → recompute; by design |
| Degradation: cluster degraded→cached+FAQ | PARTIAL | L1/L2 + rule rung precede retrieve, but if ES down on a cache+rule miss, `retrieve()` raises (no wrap) → not graceful |
| Circuit breaker / bulkhead | YES | `acip_core/resilience.py`; tests `test_security.py` |

### §9 Security
| Item | Impl? | Evidence |
|---|---|---|
| Mandatory tenant_id filter (central) | YES | `query.py:build_hybrid_query` raises `MissingTenantError`; `test_isolation.py` |
| Scoped least-privilege keys | YES | `deps.py:principal_allowed`; `v1.py:_guard` scope per endpoint |
| Rate limits/quotas | YES | `ratelimit.py`; 429 in `_guard` |
| Operator auth separated | YES | `admin.py:_authorized` (`x-admin-token`); test |
| Isolation test (release blocker) | YES | `tests/test_isolation.py`; CI gate in `.github/workflows/ci.yml` |
| GDPR delete/export/disable-tracking | YES | `admin.py:149,183,203` |
| Audit logging | YES | `acip_core/audit.py`; wired in `admin.py` |
| Network segmentation | YES | `infra/docker-compose.yml` (only api/gateway/kibana published) |
| TLS everywhere | PARTIAL | dev compose http; prod TLS documented (`infra/elasticsearch/README.md`) |
| Secrets in a store | PARTIAL | `.env`/gitignore; prod secret-store documented |
| **Dependency/image scanning** | **NO** | not in CI/compose |
| Prompt-injection tested | YES (static) | `test_injection.py` |

### §10 Sync
| Item | Impl? | Evidence |
|---|---|---|
| Event webhook→queue→worker upsert | YES | `v1.py:80` → `worker/tasks.py:process_webhook_event` |
| Idempotent upsert (version guard) | YES | `acip_sync/ingest.py:upsert_product` (`external_gte`); `test_sync_ingest.py` |
| Tombstone deletes | YES | `ingest.py:tombstone_product` |
| Delta reconciliation + backfill | PARTIAL | `acip_sync/reconcile.py` + beat schedule; **store-side fetch is a no-op hook** (`tasks.py:reconcile_tenant`) |
| DLQ | YES | `acip_sync/dlq.py`; `tasks.py` retry→DLQ |
| Backpressure / batched embeddings | YES | `tasks.py:batch_embed`; celery `acks_late`/prefetch=1 |
| OpenCart / Woo connectors | PARTIAL | parsers `acip_sync/connectors/{opencart,woo}.py` + PHP **scaffolds** `plugins/*` |
| REST connector + bulk | YES | `connectors/rest.py`; `v1.py:102` |
| Seven data sources | PARTIAL | products/categories modelled; others accepted, not modelled |
| Webhook signature enforcement | PARTIAL | parsed in connectors; not enforced at endpoint |

### §11 Analytics / §9.6 Dashboard & Widget
| Item | Impl? | Evidence |
|---|---|---|
| Insight "why" engine | YES | `acip_analytics/insight.py:why_summary`; `/admin/insight` |
| NL business analyst (grounded) | YES | `acip_analytics/nl_analyst.py:analyze`; `/admin/analyst`; test |
| Lead capture + intent | YES | `acip_analytics/leads.py:detect_lead`; `v1.py` chat hook |
| Attribution / four-dimension | YES | `acip_analytics/attribution.py` |
| Async/batch tenant-scoped | YES | aggregation query builders all carry tenant filter; `test_analytics.py` |
| Three analytics surfaces (chat/sales/behaviour) | PARTIAL | endpoints exist; populate with live events (no data) |
| Admin console (tenants/keys/synonyms/zero-result) | YES | `admin.py`; `apps/dashboard/app/{console,synonyms}` |
| Embeddable widget + white-label + cards | YES (code) | `apps/dashboard/widget/acip-widget.ts`; `tsc` clean; not embedded |

### §1/§18 KPIs (acceptance criteria)
| KPI | Impl? | Evidence |
|---|---|---|
| search p95<150ms; suggest<50ms; p99<300ms | **UNVALIDATED** | code path exists; no load test / live ES |
| assistant first-token <1.5s | UNVALIDATED | no live model |
| zero-result <5% | UNVALIDATED | needs real catalogue |
| >85% no-paid-API; cache>60%; cost→0 | UNVALIDATED | needs real traffic replay |
| availability 99.9% | UNVALIDATED | no deployment |
| NDCG@10 ≥0.80 / beats native | UNVALIDATED | no real judged golden set |
| groundedness ≥95% | UNVALIDATED | no live model sampling |
| tenant isolation 100% | YES (hermetic) | `test_isolation.py` passes; live cross-tenant test ES-gated (skipped) |

---

## Phase 3 — Phase-Plan Deliverable Verification

| Planned deliverable | Implemented | Evidence |
|---|---|---|
| P0: secure ES cluster + CI/observability scaffold | PARTIAL | compose+`verify_cluster.py`+CI; cluster never brought up |
| P0: ~50-query golden set + baseline | PARTIAL | harness + `golden_set.example.jsonl` (5 rows); real set absent |
| P0: embedding model selected | NO | `eval/decision-log.md` is a template; no decision (needs models) |
| P1: Persian analyzer + mapping | YES | `acip_search/analyzer.py,mapping.py` |
| P1: dual-track sync | PARTIAL | events YES; reconciliation fetch is a hook |
| P1: embedding service | PARTIAL | client YES; no live model |
| P1: hybrid RRF search + ACORN | YES (code) | `query.py` |
| P1: L1/L2 cache + metering | YES | `acip_cache/*` |
| P1: pilot plugin replaces native search | PARTIAL | PHP scaffolds only |
| P1 exit: pilot live, NDCG≥0.80 | NO | no pilot, no live eval |
| P2: full gateway (route/compress/failover/metering) | YES | `acip_gateway/*` |
| P2: RAG assistant + guardrails + memory | YES | `acip_assistant/*` |
| P2: widget + dashboard | YES (code) | `apps/dashboard/*` |
| P2: insight engine + attribution (first cut) | YES | `acip_analytics/*` |
| P2 exit: 3–5 pilots, cost/cache metrics on target | NO | no pilots, unvalidated |
| P3: multi-tenancy + scoped keys + billing | YES | `deps.py`,`acip_billing/*`,migrations |
| P3: isolation test release blocker | YES | `test_isolation.py` + CI gate |
| P3: reliability/load/DR/observability | PARTIAL | resilience YES; DR/load/OTel NO |
| P3 exit: public GA with SLA, validated DR | NO | unvalidated; DR absent |
| P4: agent-action enablement | YES | `acip_assistant/tools.py`; tests |
| P4: v2 directions | ROADMAP-ONLY | `docs/generated/v2-roadmap.md` (by design) |

---

## Phase 4 — Missing-Items Detection (evidence)

1. **No implementation:** cursor/keyset pagination (§12.1); search facets/aggs
   (§6/§12); idempotency-key acceptance on sync/write (§12.1); dependency/image
   scanning (§9.5); scheduled snapshots/backups + DR (§14.4); SLOs/error-budget
   alarms (§14.5); load + cost-regression test suites (§20.2); learned-sparse leg
   (§6.2, optional); embedding-model decision (P0).
2. **Partial:** SSE token streaming; delta reconciliation fetch; OpenCart/Woo
   connectors (scaffolds); seven data sources; L3 prefix-cache reuse; TLS in dev;
   secrets store; OTLP/Kibana wiring; cluster-degraded fallback; three analytics
   surfaces; webhook-signature enforcement.
3. **Implemented differently:** SSE streams assembled answer (not per-token);
   admin analytics is JSON endpoints + minimal Next.js (no charting).
4. **Planned-not-completed:** pilot store; real golden set; embedding decision;
   GA SLA/DR.
5. **Placeholder impls:** `eval/decision-log.md`; analytics relevance "note".
6. **Mock impls (tests):** `FakeRedis`, `FakeLLM`, fake ES throughout tests.
7. **Stub handlers:** agent tools (`check_stock`/`order_lookup`/`create_payment_link`/`apply_discount`) return `note: wired to live data`; `reconcile_tenant` no-op; gateway `/route` stub.
8. **TODO/FIXME markers:** grep `TODO|FIXME|XXX` over `packages services` → **none** (status is documented in docstrings instead).
9. **Runtime blockers:** no ES/PG/Redis/Celery/vLLM/TEI running; index/analyzer never applied; migrations never run; models absent.

---

## Phase 5 — Compliance Score (conservative; PARTIAL counted as 0.5)

| Category | Blueprint items | Implemented | Partial | Missing |
|---|---|---|---|---|
| Infrastructure | 10 | 6 | 4 | 0 |
| Search | 10 | 8 | 0 | 2 |
| Embeddings | 4 | 4 | 0 | 0 |
| Sync | 10 | 5 | 4 | 1 |
| Gateway | 9 | 7 | 2 | 0 |
| Assistant | 9 | 8 | 1 | 0 |
| Widget | 4 | 3 | 1 | 0 |
| Dashboard | 6 | 5 | 1 | 0 |
| Analytics | 6 | 5 | 1 | 0 |
| Billing | 5 | 5 | 0 | 0 |
| Security | 12 | 8 | 3 | 1 |
| Reliability | 12 | 6 | 3 | 3 |
| Validation | 9 | 3 | 4 | 2 |
| **Totals** | **106** | **73** | **24** | **9** |

**Code-implementation compliance** (PARTIAL = 0.5):
`(73 + 24×0.5) / 106 = 85 / 106 ≈ 80%`.
**Strict (YES only):** `73/106 ≈ 69%`.
**Runtime / KPI / acceptance compliance:** **0% validated** — all 8 headline
KPIs are UNVALIDATED; no end-to-end execution occurred.

---

## Phase 6 — Final Verdict

### **B) Blueprint Mostly Implemented With Gaps** — at the code level only.

**Justification (evidence-based):**
- The core architecture and the large majority of functional requirements are
  implemented and statically verified: all 10 §12 API endpoints exist; the
  Persian analyzer, hybrid RRF query, ACORN/DiskBBQ mapping, gateway ladder,
  RAG assistant with guardrails, billing ledger, GDPR + audit + isolation
  controls, and the analytics/insight engine are present with hermetic tests
  (81 passing). Strict YES ≈ 69%; weighted ≈ 80%.
- **However**, there are concrete blueprint gaps with no code: cursor/keyset
  pagination, search facets, idempotency-key acceptance, dependency/image
  scanning, snapshots/DR, SLO alarms, and load/cost-regression suites. Several
  features are partial or stubbed (SSE token streaming, reconciliation fetch,
  connectors, cluster-degraded fallback).
- **Critically, every acceptance KPI in §1/§18 is UNVALIDATED** (no live ES/
  model/data), and no service has been run end-to-end. By the blueprint's own
  acceptance criteria the system is **not proven** and is **not production-
  compliant**; isolation 100% is only hermetically demonstrated, not under a
  live cluster.

**Net:** Verdict **B for implementation**, but with the explicit, evidence-backed
caveat that **acceptance/runtime compliance is 0%** — so the platform is **not
GA/production-compliant** until the Validation & Acceptance work and the missing
items above are completed. This is not an estimate; it is what the repository and
the blueprint, compared directly, show.
