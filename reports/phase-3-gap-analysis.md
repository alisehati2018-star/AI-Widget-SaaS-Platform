# Phase 3 — Gap Analysis (GA Hardening)

> Implementation vs `docs/generated/phase-3.md` + `tasks-phase-3.md`. Static
> gates green (ruff, mypy 78 files, 75 unit passed / 3 ES-gated skipped, frontend
> `tsc` clean). Ops/runtime validation (DR drill, load, SLO alarms, image
> scanning, Path-B eval) deferred to the Validation & Acceptance phase.

## Requirement coverage

| Req | Status | Notes |
|---|---|---|
| REQ-M11-001 (central tenant filter) | ✅ | `acip_search.query` chokepoint; isolation suite asserts it. |
| REQ-M11-002 (scoped least-privilege keys) | ✅ | `principal_allowed` + per-endpoint scope guards (`_guard`); widget≠sync. |
| REQ-M11-003 (rate limits/quotas) | ✅ | `RateLimiter` (per-tenant, fail-open) enforced at `/v1/*`; plan limits in `plans`. |
| REQ-M11-004 (operator auth separated) | ✅ | `/admin/*` behind `x-admin-token`, distinct from tenant keys. |
| REQ-M11-005 (isolation test = release blocker) | ✅ | `tests/test_isolation.py` + dedicated CI gate step. |
| REQ-M11-006 (GDPR controls) | ✅ | erase (index+memory+logs), export, disable-tracking endpoints + audit. |
| REQ-M11-007 (audit logging) | ✅ | `audit_log` table + `audit()`; wired to tenant create/erase/tracking + money tools. |
| REQ-M11-008 (dependency/image scanning) | ◑ | CI gate placeholder; actual scanners + least-privilege accounts are ops (deferred). |
| REQ-M11-009 (credit ledger + plan enforcement) | ✅ | `acip_billing.ledger` (per-rung charge, balance, plan cap) wired into metering. |
| REQ-M11-010 (white-label presentation-only) | ✅ | branding is widget config only; isolation/control-plane untouched (covered by isolation suite). |
| REQ-M7-005 (injection suite in CI) | ✅ | `tests/test_injection.py` + CI gate; live-model behaviour is DV-103. |
| REQ-M12-001 (degradation matrix) | ✅ | search→BM25, assistant→search, paid→local already wired; documented. |
| REQ-M12-002 (circuit breakers/bulkheads) | ✅ | `acip_core.resilience` (CircuitBreaker, Bulkhead); unit-tested. |
| REQ-M12-003/004/011 (probes/tracing/observability) | ◑ | probes + trace-id + structured logs + metering live; OTLP collector wiring is ops (deferred). |
| REQ-M12-005 (snapshots/DR) | ⏳ | scripts/runbook + RPO/RTO are a Validation-phase drill (DV-203). |
| REQ-M12-006 (alias-swap reindex) | ✅ | `index_admin.reindex_and_swap` (Phase 1). |
| REQ-M12-007 (SLOs/error budgets) | ⏳ | targets recorded (KPI doc); alarms need live telemetry (DV-204). |
| REQ-M12-008 (all 7 test layers) | ✅ / ⏳ | unit/integration/relevance/isolation/guardrail present; load + cost-regression are runtime (DV-104/202). |
| REQ-M12-010 (ordered CI/CD gates) | ✅ | CI runs lint→type→unit→isolation→guardrail→security→(cost-regression placeholder). |
| REQ-M10-002 (insight "why") | ✅ | `acip_analytics.insight.why_summary` + `/admin/insight`. |
| REQ-M10-003 (NL business analyst) | ✅ | `acip_analytics.nl_analyst.analyze` (grounded; numbers-only) + `/admin/analyst`. |
| Path-B decision (§16.7) | ⏳ | requires golden-set eval (deferred); Path A remains the default. |

Legend: ✅ done · ◑ partial (code done, ops remainder deferred) · ⏳ runtime/data-gated.

## New gaps / tech debt
- **GAP-P3-1 (REQ-M11-008):** dependency/image scanners + least-privilege
  service accounts are deployment/ops config (deferred to Validation).
- **GAP-P3-2 (REQ-M12-003/004/011):** OTLP collector + Kibana dashboards need a
  running stack; trace-id + structured logs + metering already emit.
- **GAP-P3-3 (DR/SLO):** snapshot/restore drill + error-budget alarms are
  Validation-phase activities (DV-203/204).
- Carried: `body=` deprecation; keyset pagination; webhook-signature enforcement.

## Deferred to Validation & Acceptance
DV-201..205 (isolation under live ES, load/latency, DR RPO/RTO, SLO alarms,
full CI/CD incl. cost-regression replay) — see `reports/deferred-validation.md`.
None are code blockers.
