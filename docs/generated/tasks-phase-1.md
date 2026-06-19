# Tasks — Phase 1 (MVP: Smart Persian Search)

> Task ID scheme: `T-P1-NNN`. Complexity: S / M / L / XL. Validation ties to
> acceptance signals + §20 test layers.

## M2 — Data model + Persian analyzer

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P1-001 | REQ-M2-001, REQ-M2-002, REQ-M2-003, REQ-M2-004 | Implement `fa_text`/`fa_search` analyzers (ZWNJ, decimal_digit, arabic/persian normalization). | Phase 0 | L | Unit tests: ZWNJ/digit/char variants tokenize identically (App A). |
| T-P1-002 | REQ-M2-005 | Curate Persian stop-words + light stemming; tune vs golden set. | T-P1-001, P0 golden set | M | No over-stemming regression on golden set. |
| T-P1-003 | REQ-M2-006 | Wire updateable `synonym_graph` (tenant-tunable, search-time, no reindex). | T-P1-001 | M | Synonym edit takes effect without reindex. |
| T-P1-004 | REQ-M2-007, REQ-M2-011 | Define explicit catalogue mapping incl. `embedding` dense_vector (bbq_disk, chosen dims). | T-P1-001, T-P0-012 | M | Mapping applied via template; no dynamic fields. |
| T-P1-005 | REQ-M2-008 | Add `search_as_you_type`/edge-ngram suggest field. | T-P1-004 | S | `title.suggest` returns prefixes. |
| T-P1-006 | REQ-M2-009, REQ-M12-006 | Provision index aliases + zero-downtime alias-swap reindex; shared-index+routing and index-per-tenant shapes. | T-P1-004 | M | Reindex swaps alias atomically; rollback works. |
| T-P1-007 | REQ-M2-010 | Size shards/replicas to data volume (avoid over-sharding). | T-P1-004 | S | Shard/replica counts justified. |

## M3 — Sync service

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P1-010 | REQ-M3-001, REQ-M3-003 | Ingest API + queue + worker idempotent upsert (version/`updated_at` guard); re-embed on text change. | T-P1-004 | L | Re-delivered event causes no corruption (integration test). |
| T-P1-011 | REQ-M3-002, REQ-M3-012 | Delta reconciliation job + initial backfill (connector/JDBC). | T-P1-010 | L | Injected drift healed; backfill loads full catalogue; correct with webhooks off. |
| T-P1-012 | REQ-M3-004 | Tombstone-based delete propagation. | T-P1-010 | S | Deleted product removed from search promptly. |
| T-P1-013 | REQ-M3-005, REQ-M3-006 | Dead-letter queue + backpressure + batched embeddings. | T-P1-010 | M | Poison event → DLQ + replay; burst does not overwhelm cluster. |
| T-P1-014 | REQ-M3-007 | OpenCart connector (catalogue/inventory/order webhooks, widget install). | T-P1-010 | L | OpenCart store syncs end to end. |
| T-P1-015 | REQ-M3-008 | WooCommerce plugin (product+order sync, change webhooks, widget install). | T-P1-010 | L | Woo store syncs end to end. |
| T-P1-016 | REQ-M3-009, REQ-M3-010 | Custom REST connector + bulk import; ensure all seven data sources flow. | T-P1-010 | M | Products/orders/customers/categories/pages/chat-logs/events ingest. |
| T-P1-017 | REQ-M3-011 | Verify event-path freshness < 1 min typical. | T-P1-014, T-P1-015 | S | Measured propagation < 1 min. |

## M4 — Embedding service

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P1-020 | REQ-M4-001, REQ-M4-005 | Deploy chosen embedding model behind a model-agnostic interface. | T-P0-012 | M | Embeds Persian text; swap is config-only. |
| T-P1-021 | REQ-M4-002, REQ-M4-006 | Batched embedding during sync + CPU fallback path. | T-P1-020, T-P1-013 | M | Bulk embed batched; CPU fallback produces vectors. |
| T-P1-022 | REQ-M4-003, REQ-M4-004 | Apply MRL dim truncation (golden-set validated); embedding/score cache. | T-P1-020, T-P0-011 | S | Chosen dim holds NDCG; repeated embeds cached. |

## M5 — Hybrid search engine

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P1-030 | REQ-M5-001, REQ-M5-002, REQ-M5-012 | `/v1/search`: RRF fusion of BM25 (boosts title^3/brand^2/desc) + kNN; filters/facets/keyset pagination. | T-P1-004, T-P1-020 | L | Hybrid query returns fused, filtered, paginated results (App B). |
| T-P1-031 | REQ-M5-004 | DiskBBQ oversample + rescore tuning (recall/latency dial) on golden set. | T-P1-030 | M | Oversample set with NDCG/latency evidence. |
| T-P1-032 | REQ-M5-005, REQ-M11-001 | ACORN filtered kNN applying mandatory `tenant_id` + facet filters in central query-builder. | T-P1-030 | M | Filtered search fast + correct; no query bypasses the filter. |
| T-P1-033 | REQ-M5-006 | Optional eval-gated cross-encoder rerank on top-k (<512 tokens), batched + score-cached. | T-P1-030 | M | Enabled only if golden-set NDCG gain justifies latency. |
| T-P1-034 | REQ-M5-003 | Optional learned-sparse leg (BGE-M3) toggle for rare terms. | T-P1-030 | M | Sparse leg toggleable; recall improvement measured. |
| T-P1-035 | REQ-M5-007 | `/v1/suggest` autocomplete fed by popular-query + zero-result curated list. | T-P1-005 | M | Suggest < 50 ms. |
| T-P1-036 | REQ-M5-008 | Zero-result logging → synonym/analyzer/catalogue-gap loops. | T-P1-030 | S | Zero-result queries captured + surfaced. |
| T-P1-037 | REQ-M5-009, REQ-M12-001 | Graceful degradation: embeddings down → BM25; reranker down → fused unreranked. | T-P1-030, T-P1-033 | M | Search returns with a leg disabled. |
| T-P1-038 | REQ-M5-010, REQ-M5-011, REQ-M5-013 | Meet search p95<150ms/p99<300ms, suggest<50ms, zero-result<5%, NDCG@10≥0.80. | T-P1-031…037 | L | Load + relevance tests pass budgets. |

## M6 — Gateway foundation (L1/L2 + metering)

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P1-040 | REQ-M6-002, REQ-M6-005 | L1 exact cache (hash normalized prompt+tenant+data_version) + invalidation on sync events. | T-P1-010 | M | Verbatim repeat served from L1; stale busted on price/stock change. |
| T-P1-041 | REQ-M6-003 | L2 semantic cache (embed + kNN over prior Q/A) with per-tenant threshold scaffold. | T-P1-020, T-P1-040 | M | Paraphrase served from L2 on holdout. |
| T-P1-042 | REQ-M6-012 | Per-call usage/metering record (tenant, route, tokens, cache outcome, latency, cost). | T-P1-040 | S | Every call emits a usage record. |

## M8 — Pilot plugin (subset)

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P1-050 | REQ-M8-002 | OpenCart plugin replaces native search with `/v1/search`. | T-P1-030, T-P1-014 | M | Native search replaced on pilot store. |
| T-P1-051 | REQ-M8-003 | WooCommerce plugin search integration. | T-P1-030, T-P1-015 | M | Woo store uses ACIP search. |

## Cross-cutting (ongoing M12)

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P1-060 | REQ-M12-009 | Wire golden-set relevance gate into CI (no NDCG regression). | T-P0-011 | S | Relevance regression fails the build. |
| T-P1-061 | REQ-M12-002 | Timeouts + bounded jittered retries + circuit breakers on external calls. | T-P1-030 | M | Failing dependency trips fast to fallback. |

**Phase-1 exit gate:** one pilot live; golden-set NDCG@10 ≥ 0.80 / beats
native; latency + zero-result budgets met (T-P1-038). Then STOP for approval.
