# Phase 2 — Gap Analysis

> Implementation vs `docs/generated/phase-2.md` + `tasks-phase-2.md`. Static
> gates green (ruff, mypy 71 files, 57 unit passed / 3 ES-gated skipped, frontend
> `tsc` clean). Runtime/data validation is deferred to the final Validation &
> Acceptance phase (`reports/deferred-validation.md`).

## Requirement coverage

| Req | Status | Notes |
|---|---|---|
| REQ-M6-001 (gateway) | ✅ | `acip_gateway.router.GatewayRouter` fronts all model calls. |
| REQ-M6-002/003 (L1/L2 cache) | ✅ | reused from Phase 1; wired into the ladder. |
| REQ-M6-004 (L3 prefix cache) | ◑ | `LLMClient` targets vLLM (prefix/KV caching is a server flag, enabled in compose); app-side reuse validated at runtime. |
| REQ-M6-005 (cache hygiene) | ✅ | data-version keys + sync-driven invalidation (Phase 1). |
| REQ-M6-006/015 (ladder + classifier) | ✅ | `classifier.classify` + router rungs; unit-tested. |
| REQ-M6-007 (eval-driven router) | ◑ | router is deterministic + budget-gated; holdout tuning is a validation task (DV-104). |
| REQ-M6-008/013 (budget + kill switch) | ✅ | `BudgetGuard`: per-tenant/global kill switch, hard cap → local-only; unit-tested. |
| REQ-M6-009 (failover ends local) | ✅ | `ProviderChain` enforces a local terminal endpoint; failover unit-tested. |
| REQ-M6-010 (compress) | ✅ | `compress.build_context` (delimited) + `compress_messages`. |
| REQ-M6-011 (batch) | ✅ | heavy work on the Celery queue (Phase 1 worker). |
| REQ-M6-012 (metering) | ✅ | per-call `usage_events` via `_meter`. |
| REQ-M6-014 (cost targets) | ⏳ | cache>60% / >85% no-paid-API / cost→0 measured at runtime (DV-104). |
| REQ-M7-001/011 (RAG pipeline + /v1/chat) | ✅ | `RagAssistant` 8-stage pipeline; `/v1/chat` live. |
| REQ-M7-002/004 (scope lock + guardrail) | ✅ | scope-locked prompt + output guardrail with search fallback; unit-tested. |
| REQ-M7-003 (citations) | ✅ | citations carried in the turn result + widget cards. |
| REQ-M7-005 (injection defence) | ✅ (static) | untrusted-data delimiting; adversarial suite vs a live model is Phase 3 (DV-103). |
| REQ-M7-006 (memory) | ✅ | Redis session + ES long-term (tenant-scoped recall). |
| REQ-M7-007 (streaming) | ◑ | `/v1/chat/stream` SSE contract + `LLMClient.stream`; per-token vLLM streaming + TTFT wired at validation (DV-101). |
| REQ-M7-008 (agent tools) | ✅ | tool registry + audit; money-moving tools force-disabled; unit-tested. |
| REQ-M7-009 (degradation) | ✅ | generation-down → ranked search fallback in router + assistant. |
| REQ-M7-010 (groundedness ≥95%) | ⏳ | sampling harness vs judged Q&A at runtime (DV-102). |
| REQ-M8-001/004/005 (widget) | ✅ | embeddable widget + white-label + citation cards; `tsc` clean. |
| REQ-M9-001 (tenants/keys) | ✅ | `/admin/tenants` provisions tenant + hashed scoped key. |
| REQ-M9-002/003 (synonyms + zero-result) | ✅ | `/admin/synonyms` + `/admin/zero-results` + console pages. |
| REQ-M9-004/005/006/007 (analytics) | ✅ / ◑ | endpoints + four-dimension console; chat/behaviour surfaces populate with live events (DV-108). |
| REQ-M10-001/002/006/007 (insight) | ✅ | tenant-scoped aggregations, async/batch; "why" deep-dive finalises in Phase 3. |
| REQ-M10-003 (NL business analyst) | ❌ deferred | Phase 3 (M10 finalise) per the plan. |
| REQ-M10-004/005 (leads + attribution) | ✅ | lead capture + intent + attribution/four-dimension summary. |

Legend: ✅ done · ◑ partial · ❌ deferred-in-scope · ⏳ runtime/data-gated.

## New gaps / tech debt
- **GAP-P2-1 (REQ-M6-007):** router holdout tuning is a validation task, not code.
- **GAP-P2-2 (REQ-M7-007):** SSE endpoint streams the assembled answer; true
  per-token model streaming + TTFT measurement deferred (DV-101).
- **GAP-P2-3 (REQ-M10-003):** NL business analyst (ES|QL narration) is Phase 3.
- **GAP-P2-4:** operator console pages are functional but minimal (no charts);
  sufficient for the four-dimension view; richer UX post-GA.
- Carried: `body=` deprecation on ES calls; webhook-signature enforcement;
  keyset pagination (from Phase 1) — all tracked, non-blocking.

## Deferred to Validation & Acceptance
DV-101..109 in `reports/deferred-validation.md` cover live model streaming,
groundedness, injection suite, cost targets, failover drill, insight over real
data, and widget embedding. None are code blockers.
