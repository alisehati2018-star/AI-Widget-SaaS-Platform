# Deferred Runtime-Validation & Acceptance Log

> Per direction: runtime/infrastructure/data-dependent validation is **deferred
> to a final Validation & Acceptance phase** (no live Elasticsearch/Kibana,
> production-like data, pilot stores, or judged golden set yet). Development
> proceeds with static gates only (ruff, mypy, unit tests, code audits). This
> file is the running checklist to execute once that infrastructure exists.

## How to read this
Each item: ID · what to validate · requirement(s) · how to run it.

## Phase 0 / 1 (infrastructure + search)
- **DV-001** Bring up the full stack (`docker compose up`), run
  `infra/scripts/verify_cluster.py`; confirm ES green, security/TLS, Kibana. (M1)
- **DV-002** Create the catalogue index from `acip_search.index_admin`, confirm
  the Persian analyzer collapses ZWNJ/digit/char variants via `_analyze`. (M2)
- **DV-003** Seed a catalogue; exercise `/v1/search` + `/v1/suggest`; confirm
  hybrid RRF + ACORN tenant filter + DiskBBQ work end to end. (M5)
- **DV-004** Cross-tenant isolation integration test against live ES. (M11-001)
- **DV-005** Event + reconciliation sync round trip; idempotency; tombstone;
  DLQ replay; freshness < 1 min. (M3)
- **DV-006** Embedding service (TEI/BGE-M3) reachable; batch embed; MRL dims. (M4)
- **DV-007** Build the real ~50-query judged golden set; run `eval/run_eval`
  with `--tenant`; **NDCG@10 ≥ 0.80 / beats native**; zero-result < 5%. (M5/M12-009)
- **DV-008** Search latency p95 < 150 ms / p99 < 300 ms; suggest < 50 ms. (M5)
- **DV-009** DiskBBQ oversample/rescore tuning on the golden set (GAP-P1-2).
- **DV-010** Decide reranking on/off via golden-set NDCG gain (GAP-A5).

## Phase 2 (assistant, gateway, dashboard, insight)
- **DV-101** `/v1/chat` against a live local vLLM model: grounded answers,
  citations, streaming first-token < 1.5 s. (M7-007)
- **DV-102** Groundedness sampling ≥ 95% on a judged Q&A set. (M7-010)
- **DV-103** Prompt-injection adversarial suite against the live model. (M7-005)
- **DV-104** Cache hit > 60%; > 85% turns without paid API; cost/turn → 0 on a
  replayed traffic sample. (M6-014)
- **DV-105** Provider failover drill (kill frontier → local serves). (M6-009)
- **DV-106** Budget cap + kill switch end-to-end with real metering stream. (M6-013)
- **DV-107** L2 semantic-cache threshold tuning on a holdout. (M6-003 / GAP-A4)
- **DV-108** Analytics/insight aggregations against real behavioural data. (M10)
- **DV-109** Widget embeds in a real store page; white-label renders. (M8)

## Phase 3 (hardening — to be populated as Phase 3 lands)
- **DV-201** Tenant-isolation test suite as a release blocker (100%). (M11-005)
- **DV-202** Load tests meet latency budgets under concurrency. (M12)
- **DV-203** DR drill: snapshot/restore with validated RPO/RTO. (M12-005)
- **DV-204** SLOs + error-budget alarms; availability ≥ 99.9%. (M12-007)
- **DV-205** Full ordered CI/CD gate chain incl. cost-regression replay. (M12-010)

## Phase 4 (v2 / post-GA)
- **DV-301** Money-moving agent actions against live PSP/order systems with the
  confirmation UX in the widget; audit + idempotency under real traffic. (M7-008)

## Notes
- All items above are **not** code blockers for development; they validate
  behaviour/performance once real infrastructure + data exist.
- Static equivalents already run in CI (unit/lint/type) and the ES-gated
  integration job runs automatically when an ES service is present.
