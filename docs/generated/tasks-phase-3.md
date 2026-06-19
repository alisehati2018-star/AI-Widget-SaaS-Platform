# Tasks — Phase 3 (GA: Hardening & Release)

> Task ID scheme: `T-P3-NNN`. Complexity: S / M / L / XL.

## M11 — Multi-tenancy, security & billing

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P3-001 | REQ-M11-001 | Harden the single central query-builder so every path (search/suggest/chat/analytics) carries the mandatory `tenant_id` filter. | Phases 1–2 | M | No endpoint can bypass the filter. |
| T-P3-002 | REQ-M11-002, REQ-M11-004 | Scoped least-privilege API keys + separated operator/admin auth. | T-P3-001 | L | Widget key cannot reach admin; operator plane isolated. |
| T-P3-003 | REQ-M11-003 | Per-tenant rate limits & quotas at the gateway by plan. | Phase 2 gateway | M | Over-quota tenant throttled. |
| T-P3-004 | REQ-M11-005 | Automated tenant-isolation test suite as a CI **release blocker** (100% pass). | T-P3-001, T-P3-002 | L | Any cross-tenant path fails the build. |
| T-P3-005 | REQ-M11-006 | GDPR-style controls: delete (index+memory+logs), export, disable tracking, PII minimisation, on-prem residency. | T-P3-001 | L | Delete/export/disable verified per tenant. |
| T-P3-006 | REQ-M11-007, REQ-M11-008 | Audit logging (admin/key/money-tools) + dependency/image scanning + least-privilege accounts. | T-P3-002 | M | Audited actions logged; scans clean in CI. |
| T-P3-007 | REQ-M11-009 | Credit ledger + credit→cost multipliers per rung + plan enforcement. | Phase 2 metering | L | Credits metered per rung; plans enforced. |
| T-P3-008 | REQ-M11-010 | Confirm white-label remains presentation-only (no isolation/control-plane weakening). | T-P3-002 | S | Branding changes leave isolation intact. |

## M7 — Security hardening

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P3-010 | REQ-M7-005 | Adversarial prompt-injection suite (untrusted product data, refusal on thin context, no off-domain) in CI. | Phase 2 assistant | M | Injection suite passes; behaviour unchanged by malicious product text. |

## M12 — Reliability, DR, CI/CD (remainder)

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P3-020 | REQ-M12-001, REQ-M12-002 | Complete graceful-degradation matrix + bulkheads/concurrency limits per tenant+dependency. | Phases 1–2 | L | Each §14.1 row's fallback verified; one tenant cannot starve others. |
| T-P3-021 | REQ-M12-003, REQ-M12-004, REQ-M12-011 | Full probes + tracing/structured logs + AI-call logging across all services; complete observability stack. | Phase 0 scaffolding | M | End-to-end traceability; per-call AI analytics visible. |
| T-P3-022 | REQ-M12-005 | Scheduled ES + PostgreSQL snapshots/backups + documented DR drill with validated RPO/RTO. | T-P3-021 | L | Restore drill succeeds; objectives recorded. |
| T-P3-023 | REQ-M12-007 | Define + wire SLOs + error budgets; alarms on latency tail, availability, cache-hit regression; availability ≥ 99.9%. | T-P3-021 | M | SLOs tracked; alarms fire on budget burn. |
| T-P3-024 | REQ-M12-008 | Complete all seven test layers (unit/integration/relevance/load/isolation/guardrail/cost-regression). | T-P3-004, T-P3-010 | L | All layers present and green. |
| T-P3-025 | REQ-M12-010 | Wire ordered CI/CD gates (unit+int → relevance → isolation → guardrail → cost-regression) + staging perf budgets + automated reversible deploys. | T-P3-024 | L | Pipeline enforces ordered gates; rollback works. |
| T-P3-026 | REQ-M12-006 | Finalise zero-downtime alias-swap reindex + instant rollback under load. | Phase 1 aliases | M | Reindex atomic; rollback instant. |

## M10 — Insight engine (finalise)

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P3-030 | REQ-M10-002 | Finalise insight "why" engine (zero-result clusters, OOS-but-searched, funnel drop-off, emerging themes). | Phase 2 insight cut | L | "Why" answers backed by aggregations. |
| T-P3-031 | REQ-M10-003 | AI Business Analyst: NL Persian → ES aggregations/ES\|QL → LLM narrates numbers only, links to breakdown. | T-P3-030, Phase 2 gateway | L | Reports figures, never invents; grounded. |

## Decision gate

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P3-040 | §16.7, §21.4 | Decide whether to enable Elastic-managed Path B based on golden-set eval. | T-P3-024 | S | Decision recorded with evidence. |

**Phase-3 exit gate (GA):** public release with SLA; isolation test 100% pass
(T-P3-004); availability ≥ 99.9% (T-P3-023); automated deploy + validated DR
(T-P3-022/025). Then STOP for approval before Phase 4.
