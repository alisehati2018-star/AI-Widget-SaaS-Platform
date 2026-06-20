# ACIP — Gap Closure & Blueprint Completion Audit

> Inputs: `ACIP-Blueprint.docx`, `reports/blueprint-compliance-audit.md`,
> repository source, and the generated plans/reports. This is a **factual
> closure report** — no code was changed. Classifications use only **REQUIRED /
> OPTIONAL / DEFERRED**, anchored to the blueprint's own phasing (§16: MVP =
> Phase 1, Beta = Phase 2, GA = Phase 3, V2 = Phase 4). Repo at commit `bad0c68`.
>
> "Blueprint Criticality" = does the blueprint mandate the item at all.
> Per-milestone columns = is it needed **by** that milestone.

---

## Closure Classification Table

| Item | Current Status | Blueprint Criticality | MVP | Beta | GA | V2 | Recommendation |
|---|---|---|---|---|---|---|---|
| Cursor/keyset pagination (§12.1) | NO | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | Implement before GA |
| Search facets/aggregations (§6/§12) | NO | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | Implement before GA |
| Idempotency-key on sync/write endpoints (§12.1) | NO | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | Implement before GA (upserts already idempotent via version guard) |
| Dependency/image scanning (§9.5) | NO | REQUIRED | DEFERRED | OPTIONAL | REQUIRED | — | GA hardening |
| Scheduled snapshots/backups + DR (§14.4) | NO | REQUIRED | DEFERRED | DEFERRED | REQUIRED | — | GA blocker |
| SLOs / error-budget alarms (§14.5) | NO | REQUIRED | DEFERRED | DEFERRED | REQUIRED | — | GA (post-GA SLOs) |
| Load test suite (§20.2) | NO | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | GA gate |
| Cost-regression replay suite (§20.2/§20.4) | NO | REQUIRED | DEFERRED | REQUIRED | REQUIRED | — | Beta/GA gate |
| Learned-sparse retrieval leg (§6.2 "optionally") | NO | OPTIONAL | OPTIONAL | OPTIONAL | OPTIONAL | DEFERRED | Defer; enable only if recall eval demands |
| Embedding-model decision (P0 exit) | PLACEHOLDER | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP blocker (needs models + golden set) |
| Real ~50-query judged golden set (§20.1) | PLACEHOLDER | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP blocker (quality backbone) |
| SSE per-token streaming + TTFT (§7.4) | PARTIAL | REQUIRED | DEFERRED | REQUIRED | REQUIRED | — | Beta (assistant) |
| Delta reconciliation store-side fetch (§10.1) | PARTIAL/STUB | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP (sync correctness safety-net) |
| OpenCart/Woo connectors (full, not scaffold) (§10.3) | PARTIAL | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP needs ≥1 pilot connector |
| Seven data sources — orders/customers/pages/chat/events (§10.4) | PARTIAL | REQUIRED | OPTIONAL | REQUIRED | REQUIRED | — | products/categories done (MVP); rest Beta |
| L3 prefix/KV cache reuse (§8.2) | PARTIAL | OPTIONAL | DEFERRED | OPTIONAL | OPTIONAL | — | vLLM does it server-side; app-metric optional |
| TLS everywhere (cert-verified) (§9.5) | PARTIAL | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | GA blocker (dev uses http) |
| Secrets store (prod) (§9.5) | PARTIAL | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | GA blocker |
| OTLP collector / Kibana dashboards (§3.8/§5) | PARTIAL | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | GA (trace-id + logs + metering already emit) |
| Cluster-degraded → cached+FAQ fallback (§14.1) | PARTIAL | REQUIRED | OPTIONAL | REQUIRED | REQUIRED | — | Beta/GA reliability |
| Three analytics surfaces over live events (§11.1) | PARTIAL | REQUIRED | DEFERRED | REQUIRED | REQUIRED | — | Beta |
| Webhook-signature enforcement at endpoint (§10) | PARTIAL | REQUIRED | OPTIONAL | OPTIONAL | REQUIRED | — | GA (endpoint already API-key gated) |
| Agent-tool live handlers (PSP/order) (§7.5) | STUB | DEFERRED | DEFERRED | DEFERRED | DEFERRED | REQUIRED | V2 only (framework done) |
| Standalone gateway service `/route` stub | STUB | OPTIONAL | OPTIONAL | OPTIONAL | OPTIONAL | DEFERRED | In-process `GatewayRouter` is used; service stub optional |
| KPI: search p95<150 / suggest<50 / p99<300 | UNVALIDATED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP exit (runtime) |
| KPI: zero-result < 5% | UNVALIDATED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP exit (runtime) |
| KPI: NDCG@10 ≥ 0.80 / beats native | UNVALIDATED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP exit (runtime) |
| KPI: assistant first-token < 1.5 s | UNVALIDATED | REQUIRED | DEFERRED | REQUIRED | REQUIRED | — | Beta exit (runtime) |
| KPI: groundedness ≥ 95% | UNVALIDATED | REQUIRED | DEFERRED | REQUIRED | REQUIRED | — | Beta exit (runtime) |
| KPI: cache>60% / >85% no-paid / cost→0 | UNVALIDATED | REQUIRED | DEFERRED | REQUIRED | REQUIRED | — | Beta exit (runtime) |
| KPI: availability 99.9% | UNVALIDATED | REQUIRED | DEFERRED | DEFERRED | REQUIRED | — | GA exit (runtime) |
| KPI: tenant isolation 100% (live ES) | UNVALIDATED (hermetic ✓) | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | Hermetic pass exists; live cross-tenant test is GA blocker |
| Live cluster bring-up + index/analyzer applied | UNVALIDATED | REQUIRED | REQUIRED | REQUIRED | REQUIRED | — | MVP runtime prerequisite |
| V2 directions (recs, A/B, Path B, connectors, visual) | NOT BUILT (roadmap) | DEFERRED | DEFERRED | DEFERRED | DEFERRED | REQUIRED | V2 only (by design) |

---

## Mandatory Before Blueprint Can Be Considered Complete

Every item the blueprint **mandates** (Criticality = REQUIRED) that is not YES.
These must be implemented and/or validated for full blueprint compliance:

1. Cursor/keyset pagination on search (§12.1)
2. Search facets/aggregations (§6/§12)
3. Idempotency-key acceptance on sync/write endpoints (§12.1)
4. Dependency/image scanning in CI (§9.5)
5. Scheduled snapshots/backups + DR runbook with RPO/RTO (§14.4)
6. SLOs + error-budget alarms (§14.5)
7. Load test suite (§20.2)
8. Cost-regression replay suite (§20.2/§20.4)
9. Embedding-model decision on the real golden set (P0 / §21.4)
10. Real ~50-query judged golden set (§20.1)
11. SSE per-token streaming + first-token measurement (§7.4)
12. Delta reconciliation store-side fetch (currently a no-op hook) (§10.1)
13. Full OpenCart/WooCommerce connectors (currently scaffolds) (§10.3)
14. Remaining data sources: orders/customers/pages/chat-logs/events (§10.4)
15. CA-verified TLS everywhere + secrets store (§9.5)
16. OTLP collector / Kibana dashboards wiring (§3.8/§5)
17. Cluster-degraded → cached+FAQ graceful fallback (§14.1)
18. Three analytics surfaces over live behavioural events (§11.1)
19. Webhook-signature enforcement at the ingest endpoint (§10)
20. **All 8 headline KPIs validated** against a live cluster + real data (§1/§18)
21. Live cluster bring-up: index/analyzer/mapping applied; migrations run.

(Excluded as blueprint-OPTIONAL/DEFERRED: learned-sparse leg, L3 app-reuse
metric, standalone gateway `/route` stub, V2 directions, agent-tool live wiring.)

---

## Mandatory Before Production (GA)

All of the above are GA-blocking **except** the few that are MVP/Beta-stage and,
if reached, are already prerequisites. The GA-specific blockers are:

- Pagination + facets (§12.1/§6)
- Idempotency-key on sync/write (§12.1)
- Dependency/image scanning (§9.5)
- Snapshots/backups + validated DR (RPO/RTO) (§14.4)
- SLOs + error-budget alarms; availability 99.9% validated (§14.5/§18)
- Load + cost-regression suites in CI (§20.2/§20.4)
- CA-verified TLS + secrets store (§9.5)
- OTLP/Kibana observability wiring (§3.8/§5)
- Cluster-degraded fallback + full degradation matrix proven (§14.1)
- Webhook-signature enforcement (§10)
- **Live tenant-isolation test under a real cluster (100%)** (§9.3/§18.4)
- All KPIs validated (§1/§18)

## Safe To Defer

- Learned-sparse retrieval leg (§6.2 — blueprint says "optionally").
- L3 prefix-cache app-side reuse metric (vLLM handles server-side).
- Standalone gateway `/route` service stub (in-process router is used).
- Agent-tool **live** PSP/order handlers — V2 (framework already built & gated).
- All V2 directions: recommendations, A/B ranking, Path B (Elastic-managed),
  additional connectors (Magento/custom), visual/multimodal search (§16.6/§21.5).

---

## Revised Blueprint Compliance (mandatory-only denominator)

From the independent compliance audit: **106 blueprint items** total →
73 YES, 24 PARTIAL, 9 NO.

Remove blueprint-**OPTIONAL/DEFERRED** items from the denominator (learned-sparse
leg [NO], L3 app-reuse [PARTIAL], gateway `/route` stub [PARTIAL], agent-tool
live handlers [STUB, counted under Assistant]) ≈ **4 items removed** (1 NO, 3
PARTIAL/STUB) → **mandatory denominator ≈ 102**: **73 YES, 21 PARTIAL, 8 NO**.

| Metric | Value |
|---|---|
| **Current compliance (mandatory, PARTIAL=0.5)** | (73 + 21×0.5) / 102 = 83.5 / 102 ≈ **82%** (code) |
| **Current compliance (mandatory, strict YES)** | 73 / 102 ≈ **72%** (code) |
| **Current runtime/acceptance compliance** | **0%** — all 8 KPIs UNVALIDATED; no live run |
| **Compliance after gap closure (code)** | **100%** of blueprint-mandatory items, *by definition* once items 1–19 + 21 above are implemented |
| **Compliance after gap closure (acceptance)** | reaches the KPI targets only after item 20 (live validation) passes — still gated on real infra + data |

### Estimated Remaining Work (factual item count, not time)

- **Code-implementation gaps to close (mandatory):** ~19 discrete items
  (#1–#19 above) — feature/ops code: pagination, facets, idempotency header,
  reconciliation fetch, full connectors, remaining data sources, TLS/secrets,
  OTLP wiring, cluster-degraded fallback, signature enforcement, scanning, DR
  automation, SLO alarms, load + cost-regression suites, SSE token streaming.
- **Runtime / acceptance work (mandatory, infra-gated):** the full Validation &
  Acceptance phase — 25 `DV-*` items (`reports/deferred-validation.md`):
  live cluster bring-up, real golden set, embedding decision, and validation of
  all 8 KPIs + the live isolation test. **Requires** a Docker/K8s host, a pilot
  store, self-hosted models (BGE-M3/Qwen3/vLLM), and judged data — none present.
- **Deferred (not counted):** ~5 OPTIONAL/V2 items above.

The blueprint's own effort frame (§17) sizes the *whole* build at ~50–55
person-weeks to GA; the remaining mandatory work here is the **finishing +
validation slice**, not a rebuild — the architecture and ~72–82% of mandatory
code already exist.

---

## Summary

- **Current blueprint compliance (mandatory, code):** ~72% strict / ~82% weighted.
- **Current acceptance/runtime compliance:** **0% (unvalidated).**
- **To reach blueprint-complete:** close the ~19 mandatory code gaps **and**
  execute the Validation & Acceptance phase (live infra + real data) to prove the
  8 KPIs and the live isolation test.
- **Verdict carried from the compliance audit stands:** *Mostly Implemented With
  Gaps (code) — not production/acceptance compliant.* This report adds the
  prioritisation: what is REQUIRED vs OPTIONAL vs DEFERRED, and which gaps block
  MVP, Beta, and GA respectively.
