# Phase 1 — MVP: Smart Persian Search (weeks 3–10)

> Source: Blueprint §16.3, §21.2, §21.1. Modules: **M2, M3, M4, M5**, the
> **L1/L2 cache + metering foundation of M6**, the pilot plugin (subset of
> **M8**), and ongoing **M12**.

## Objective

Deliver a **single pilot store** whose Persian search is measurably better and
faster than its native engine — one complete vertical slice (catalogue synced
→ indexed with the Persian analyzer + vectors → searchable via hybrid RRF →
fronted by a plugin that replaces native search), per §21.1.

## Included modules

- **M2** — Data model + Persian analyzer (full).
- **M3** — Sync service (event + reconciliation; OpenCart + Woo connectors).
- **M4** — Embedding service (the model chosen in Phase 0).
- **M5** — Hybrid search engine (RRF, DiskBBQ, ACORN, optional rerank).
- **M6** — *foundation only:* L1/L2 cache + metering hooks (the cost **ceiling**
  — routing/compression/failover — hardens in Phase 2).
- **M8** — *subset:* a simple OpenCart/Woo plugin that replaces native search.
- **M12** — ongoing: degradation behaviour, isolation invariant asserted from
  the first multi-tenant line, relevance CI gate.

## Included requirements

- **M2:** REQ-M2-001 … REQ-M2-011.
- **M3:** REQ-M3-001 … REQ-M3-012.
- **M4:** REQ-M4-001 … REQ-M4-006.
- **M5:** REQ-M5-001 … REQ-M5-013.
- **M6 (foundation):** REQ-M6-002 (L1), REQ-M6-003 (L2), REQ-M6-005 (cache
  hygiene), REQ-M6-012 (usage/metering record). *(Deferred to Phase 2:
  REQ-M6-001/004/006/007/008/009/010/011/013/014/015.)*
- **M8 (subset):** REQ-M8-002 (OpenCart native-search replacement),
  REQ-M8-003 (Woo plugin install). *(Widget UI, white-label, cards → Phase 2.)*
- **M12 (ongoing):** REQ-M12-001/002 (degradation + resilience as features
  land), REQ-M12-006 (alias-swap reindex), REQ-M12-009 (golden-set CI gate),
  partial REQ-M12-003/004 on shipped services.
- **M11 (invariant only):** REQ-M11-001 (mandatory `tenant_id` filter) is
  asserted from the first query — full multi-tenancy/billing is Phase 3.

## Deliverables

1. Persian analyzer + explicit catalogue mapping behind aliases.
2. Dual-track sync (events + reconciliation) for OpenCart and WooCommerce.
3. Self-hosted embedding service producing DiskBBQ vectors.
4. Hybrid RRF `/v1/search` + `/v1/suggest` with ACORN tenant/facet filtering
   and optional eval-gated rerank.
5. L1/L2 cache + per-call usage metering foundation.
6. Pilot plugin replacing native search on one real store.
7. **One pilot store live on ACIP search.**

## Acceptance criteria

**Exit criterion (MVP, verbatim §16.3):** *fast, effective Persian hybrid
search on the pilot, with a measurable improvement over native search on the
golden set.*

Concretely:
- Search **p95 < 150 ms / p99 < 300 ms**; suggest **< 50 ms** (REQ-M5-010).
- **Zero-result rate < 5%** (REQ-M5-011).
- **NDCG@10 ≥ 0.80 / beats native by a clear margin** on the golden set
  (REQ-M5-013), enforced by the CI relevance gate.
- Sync freshness **< 1 min** on the event path; reconciliation heals drift.
- Every search/suggest query carries the mandatory `tenant_id` filter.
- Graceful degradation verified: embeddings down → BM25; reranker down → fused.

## Risks (from §19)

- **Weak Persian relevance** (High/Med) → hybrid RRF means BM25 carries quality
  even if vectors underperform; rerank lifts top-k; golden-set gate guards.
- **Vector memory/RAM cost at scale** (High/Med) → DiskBBQ + MRL dims.
- **Sync gaps/drift** (Med) → dual-track sync; drift auto-healed.
- **Cache staleness** (Med) → scope keys by tenant + data version; invalidate
  on sync events (REQ-M6-005).
- **Scope creep** (Med/High) → assistant, dashboard, analytics stay in Phase 2+.

## Dependencies

- **Upstream:** Phase 0 (cluster M1, golden set, embedding-model decision).
- **Critical path:** M1 → M2 → M4/M5 is the spine (§17.3); M3 runs in parallel
  (reconciliation track makes the system demoable before events are perfect).
- **Downstream:** Phase 2 assistant/gateway build on this search + cache
  foundation.
