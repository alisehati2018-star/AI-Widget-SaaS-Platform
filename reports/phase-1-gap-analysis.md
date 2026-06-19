# Phase 1 — Gap Analysis

> Implementation vs `docs/generated/phase-1.md` + `tasks-phase-1.md`. Honest
> accounting of what is complete, partial, or deferred-within-scope, plus
> runtime/data-gated exit criteria. Static gates (ruff/mypy/pytest) are green;
> live ES checks run in a Docker/CI-service environment (no Docker in this
> container).

## Requirement coverage

| Req | Status | Notes |
|---|---|---|
| REQ-M2-001..006 (analyzer) | ✅ | `acip_search/analyzer.py` per Appendix A.1; unit-tested; ZWNJ/digit collapse asserted in ES integration test. |
| REQ-M2-007/008/011 (mapping) | ✅ | `mapping.py` per Appendix A.2; `dynamic: strict`, DiskBBQ, suggest sub-field. |
| REQ-M2-009 / M12-006 (aliases, reindex) | ✅ | `index_admin.reindex_and_swap` + `point_alias`. |
| REQ-M2-010 (shards) | ✅ | configurable via settings; default 1/1 for small catalogues. |
| REQ-M3-001/003/004 (upsert/idempotency/tombstone) | ✅ | `ingest.py` deterministic id + external-version guard; unit-tested. |
| REQ-M3-002/012 (reconciliation/backfill) | ◑ | engine (`reconcile.py`) + watermark schema + beat schedule present; store-side `fetch_changed_since` is a connector hook to wire per live store. |
| REQ-M3-005/006 (DLQ/backpressure) | ✅ | `dlq.py` + Celery `acks_late`/prefetch=1 + retry→DLQ. |
| REQ-M3-007/008/009 (connectors) | ✅ | OpenCart/Woo/REST parsers + signature verification. |
| REQ-M3-010 (seven sources) | ◑ | products + categories fully modelled for search; orders/customers/pages/chat-logs/events are accepted via REST but their dedicated stores/analytics land in M10 (Phase 2). |
| REQ-M3-011 (freshness <1 min) | ⏳ | event path is async + fast; the latency number is measured on a live store. |
| REQ-M4-001..006 (embeddings) | ✅ | `acip_embedding` TEI client, batch, MRL truncation, Redis cache, model-agnostic, CPU-fallback tolerant. |
| REQ-M5-001/002/012 (hybrid RRF + boosts + pagination) | ✅ / ◑ | RRF + boosts + filters/facets done; **keyset pagination is size-based for RRF** (cursor pagination refined when needed). |
| REQ-M5-003 (learned-sparse leg) | ❌ deferred | optional BGE-M3 sparse leg not implemented this phase; query builder is BM25+dense. Toggle to be added if recall eval calls for it. |
| REQ-M5-004 (DiskBBQ oversample/rescore) | ◑ | `num_candidates` exposed; explicit `rescore_vector`/oversample tuning to be set against the golden set on live ES. |
| REQ-M5-005 / M11-001 (ACORN + tenant filter) | ✅ | central `build_hybrid_query`; filter on both legs; unit + ES isolation tests. |
| REQ-M5-006 (rerank, eval-gated) | ✅ | ES `text_similarity_reranker` wrapper + app-side `Reranker` client; default OFF. |
| REQ-M5-007 (suggest) | ✅ | `suggest.py` bool_prefix over `title.suggest`; `/v1/suggest`. |
| REQ-M5-008 (zero-result loop) | ✅ | `zero_result.py` captures to Redis; surfaced to dashboard in Phase 2. |
| REQ-M5-009 / M12-001 (degradation) | ✅ | embeddings down → BM25-only (in `retrieval`); reranker down → identity order. |
| REQ-M5-010/011/013 (latency/zero-result/NDCG targets) | ⏳ | require live ES + the real ~50-query judged golden set; harness + CI step ready. |
| REQ-M6-002/003/005/012 (cache foundation + metering) | ✅ | L1 exact, L2 semantic scaffold, data-version invalidation, `usage_events` metering. |
| REQ-M8-002/003 (pilot plugins) | ◑ | OpenCart PHP + WooCommerce plugin scaffolds that call `/v1/search` and post webhooks; full platform packaging is pilot-onboarding work. |
| REQ-M12-002 (resilience) | ◑ | timeouts + bounded Celery retries + graceful fallbacks; explicit circuit breakers deferred to Phase 3 hardening. |
| REQ-M12-009 (relevance CI gate) | ✅ | `eval/run_eval.py` + ES provider + CI relevance step (NDCG threshold enforced once the real golden set lands). |

Legend: ✅ done · ◑ partial · ❌ deferred · ⏳ runtime/data-gated.

## New / carried gaps

- **GAP-P1-1 (REQ-M5-003):** learned-sparse leg not implemented — optional;
  revisit if dense+lexical recall is insufficient on the golden set.
- **GAP-P1-2 (REQ-M5-004):** DiskBBQ oversample/rescore not yet tuned — needs
  live ES + golden set (decision gate §21.4 "rerank/oversample").
- **GAP-P1-3 (REQ-M3-010):** non-product sources (orders/customers/pages/chat/
  events) accepted but not fully ingested/modelled — they feed M10 in Phase 2.
- **GAP-P1-4 (GAP-B6):** webhook signature verification implemented in the
  connectors + `tenants.webhook_secret` column added, but the webhook endpoint
  does not yet *enforce* it (per-tenant secret lookup) — enforce in Phase 1
  completion or early Phase 3 security hardening.
- **GAP-P1-5 (keyset pagination):** RRF pagination is size-based; true cursor
  pagination to be added when result-set depth requires it.
- **Tech debt (audit item 5):** local `pip install .` can leave a stale
  top-level `api`/`worker` package in site-packages; tests use source via
  `pythonpath` (authoritative). Recommend `pip install -e .` for local dev; the
  Docker image already copies source before install.

## Runtime/data exit criteria still open (the Phase-1 gate)
- Live cluster: create index, seed catalogue, measure search p95<150ms /
  p99<300ms, suggest<50ms (REQ-M5-010), zero-result<5% (REQ-M5-011).
- Real ~50-query judged golden set (ASM-4) → NDCG@10 ≥ 0.80 / beats native
  (REQ-M5-013) via the CI relevance gate.
- One pilot store live on ACIP search (Phase-1 exit, §16.3).
These require a Docker host + a pilot store and are the human/runtime portion of
the gate, not code defects.
