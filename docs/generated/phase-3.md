# Phase 3 — GA / v1.0: Hardening & Release (weeks 19–26)

> Source: Blueprint §16.5, §21.2, §16.7. Modules: full **M11** (multi-tenancy,
> security, billing), remainder of **M12** (reliability/DR/CI-CD), finalise
> **M10**.

## Objective

Ship a **public, multi-tenant general-availability release** with proven tenant
isolation, billing, an SLA, automated deployment, and validated disaster
recovery.

## Included modules

- **M11** — full multi-tenancy, scoped keys, billing hooks, isolation test as a
  release blocker.
- **M12** — remainder: reliability, load testing, DR, observability, CI/CD
  gates, security hardening.
- **M10** — finalise insight engine + NL business analyst.
- **Path B decision:** decide whether to enable the Elastic-managed path based
  on measured quality need (§16.7, §21.4).

## Included requirements

- **M11:** REQ-M11-001 … REQ-M11-010 (REQ-M11-001 carried/owned here in full;
  invariant was asserted from Phase 1).
- **M12 (remainder):** REQ-M12-003 (all services), REQ-M12-004 (full),
  REQ-M12-005 (DR), REQ-M12-007 (SLOs/error budgets), REQ-M12-008 (all test
  layers), REQ-M12-010 (ordered CI/CD gates + reversible deploys),
  REQ-M12-011 (full observability). REQ-M12-001/002/006 finalised.
- **M10 (finalise):** REQ-M10-002 (insight "why"), REQ-M10-003 (NL business
  analyst).
- **M7 hardening:** REQ-M7-005 prompt-injection adversarial suite in CI.

## Deliverables

1. Full multi-tenancy: mandatory filter everywhere, scoped least-privilege
   keys, per-tenant rate limits/quotas, operator auth, GDPR controls,
   white-label, audit logging.
2. Credit-based billing ledger + plan enforcement.
3. **Automated tenant-isolation test as a release blocker** (100% pass).
4. Reliability hardening: degradation matrix complete, circuit
   breakers/bulkheads, load tests meeting budgets, DR drill with validated
   RPO/RTO, zero-downtime alias-swap reindex.
5. Full CI/CD gate chain + reversible automated deploys.
6. Finalised insight engine + NL business analyst.
7. Path-B decision recorded.
8. **General availability.**

## Acceptance criteria

**Exit criterion (GA, verbatim §16.5):** *public release with SLA, passing
tenant-isolation test, automated deployment, and validated DR.*

Concretely:
- **Tenant-isolation test 100% pass** — release blocker (REQ-M11-005).
- **Availability ≥ 99.9%** with SLOs + error budgets (REQ-M12-007).
- CI/CD enforces ordered gates: unit+integration → relevance (no NDCG
  regression) → isolation (100%) → guardrail → cost-regression replay; perf
  budgets on staging (REQ-M12-010).
- DR restore drill succeeds; RPO/RTO recorded (REQ-M12-005).
- Prompt-injection suite passes in CI (REQ-M7-005).

## Risks (from §19)

- **Tenant data leakage** (Critical/Low) → isolation invariant everywhere +
  scoped keys + automated release-blocking test.
- **Elastic licensing / Path-B cost** (Low/Low) → MVP on free tier; Path B is
  opt-in only if eval justifies it.
- **Error-budget / SLO definition gaps** (see gap-analysis) → concrete numbers
  must be finalised here before GA.
- **Model drift / version churn** (Med) → pin permissive licences; verify model
  card at deploy; model-agnostic serving.

## Dependencies

- **Upstream:** Phases 1–2 (search, assistant, gateway, dashboard, first
  insight cut). Isolation invariant and degradation behaviour were built as
  features landed, not retrofitted here (§21.3).
- **Downstream:** Phase 4 (post-GA) builds on a stable, instrumented core.
