# Tasks — Phase 2 (Beta: Assistant & Dashboard)

> Task ID scheme: `T-P2-NNN`. Complexity: S / M / L / XL.

## M6 — Full AI gateway

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P2-001 | REQ-M6-001 | Build the thin stateless gateway in front of all model calls (routing/cache/metering/failover). | Phase 1 cache foundation | L | All model calls traverse the gateway. |
| T-P2-002 | REQ-M6-006, REQ-M6-015 | Escalation ladder router + intent/difficulty classifier (cache→rule→search→local→frontier). | T-P2-001 | L | Turns stop at cheapest rung that answers well. |
| T-P2-003 | REQ-M6-007 | Eval-driven router tuning on labelled holdout; re-run on model/threshold change. | T-P2-002 | M | Escalation only when cheaper tiers measurably fail. |
| T-P2-004 | REQ-M6-004 | L3 provider/prefix (KV) caching via vLLM + hosted prompt caching. | T-P2-001 | M | Prefix reuse cuts cost/first-token. |
| T-P2-005 | REQ-M6-010 | COMPRESS: context pruning to reranked top passages, terse structured prompts, summarized memory. | T-P2-002 | M | 30–50% token reduction, quality held. |
| T-P2-006 | REQ-M6-009 | Multi-provider health-checked failover ending at local model. | T-P2-002 | M | Provider outage falls over to local. |
| T-P2-007 | REQ-M6-008, REQ-M6-013 | Budget-aware routing + FinOps: per-tenant/feature attribution, soft budgets/alerts, hard caps, kill switches. | T-P2-002, Phase 1 metering | L | Spend cannot exceed cap; kill switch forces local-only. |
| T-P2-008 | REQ-M6-011 | Batch heavy non-interactive work (embeddings, analytics, reports) on the queue. | T-P2-001 | S | Heavy jobs off shopper path. |
| T-P2-009 | REQ-M6-014 | Verify cost-efficiency targets (cache>60%, >85% no-paid-API, cost/turn→0). | T-P2-002…008 | M | Dashboard meets §18.3 targets. |

## M7 — Assistant / RAG

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P2-020 | REQ-M7-001, REQ-M7-011 | Build `/v1/chat` RAG pipeline (understand→cache→retrieve→rerank→compress→generate→guardrail→stream+cache). | T-P2-002, Phase 1 search | XL | All 8 stages observable with budgets/fallbacks. |
| T-P2-021 | REQ-M7-002, REQ-M7-004 | Scope lock + output guardrail (reject ungrounded/cross-tenant/off-domain → search fallback). | T-P2-020 | L | Off-context question → grounded refusal/fallback. |
| T-P2-022 | REQ-M7-003, REQ-M8-005 | Citations/evidence cards in answers and widget. | T-P2-020 | M | Answers carry verifiable references. |
| T-P2-023 | REQ-M7-006 | Conversational memory: session (Redis) + long-term (Elastic), summarized/truncated. | T-P2-020 | M | Both tiers work; prompt bounded. |
| T-P2-024 | REQ-M7-007 | Streaming (SSE) + prefix/KV cache + compression → first token < 1.5 s; optional speculative decoding. | T-P2-020, T-P2-004 | L | TTFT < 1.5 s on pilots. |
| T-P2-025 | REQ-M7-008 | Agent-action tool interface + audit log (money-moving tools disabled). | T-P2-020 | M | Interface + audit exist; money tools off. |
| T-P2-026 | REQ-M7-009 | Degradation: LLM down → ranked search + templated message. | T-P2-020 | S | Assistant degrades to search. |
| T-P2-027 | REQ-M7-010 | Groundedness sampling/judging harness → ≥95%. | T-P2-021 | M | Sampled groundedness ≥ 95%. |

## M8 — Widget

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P2-030 | REQ-M8-001 | Embeddable Next.js/React widget consuming search + chat APIs. | T-P2-020 | L | Widget embeds + streams chat. |
| T-P2-031 | REQ-M8-004 | White-label (logo/colours, presentation-only; isolation intact). | T-P2-030 | S | Branding configurable; isolation unaffected. |

## M9 — Admin & analytics dashboard

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P2-040 | REQ-M9-001 | Admin console: tenants, keys, plans (`/admin/tenants`). | T-P2-001 | M | CRUD tenants/keys/plans. |
| T-P2-041 | REQ-M9-002, REQ-M9-003 | Synonym/curated-suggestion tools + zero-result view (`/admin/synonyms`). | Phase 1 M5 | M | Operator edits synonyms; zero-results actionable. |
| T-P2-042 | REQ-M9-004, REQ-M9-006, REQ-M9-007 | Analytics dashboards: search/zero-result/funnel/conversion + chat + behaviour. | T-P2-040, T-P2-050 | L | Stats render per tenant. |
| T-P2-043 | REQ-M9-005 | One dashboard, four dimensions (relevance/latency/cost/reliability). | T-P2-042, T-P2-009 | M | Single view surfaces all four. |

## M10 — Insight engine (first cut)

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P2-050 | REQ-M10-001, REQ-M10-007, REQ-M10-006 | Sales/customer-insight aggregations (most-wanted, OOS-but-wanted, drop-off), async/batch + tenant-scoped. | Phase 1 sync | L | Insights computed off shopper path. |
| T-P2-051 | REQ-M10-004, REQ-M10-005 | Lead capture + intent + abandoned-chat recovery; AI-attribution (influenced sales/conversion/revenue). | T-P2-020, T-P2-050 | L | Leads captured; attribution reported. |

**Phase-2 exit gate:** 3–5 pilots with grounded assistant + dashboard;
first-token < 1.5 s; groundedness ≥ 95%; cache > 60% / > 85% no-paid-API; cost
metrics on target. Then STOP for approval.
