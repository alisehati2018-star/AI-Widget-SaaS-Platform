# Phase 4 — v2 / Post-GA (after GA)

> Source: Blueprint §16.6, §21.4, §21.5, §2 (Deferred v2+), §7.5.

## Objective

Extend the stable, well-instrumented GA core with higher-value capabilities
that were **deliberately deferred** so they could not jeopardise the 26-week
GA. Order roughly follows value (§21.2).

## Included modules / directions

All items here are **explicitly out of scope before GA** (§2 Deferred, §21.5).
They depend on the stable core that Phases 0–3 exist to build.

| Direction | Notes | Source |
|---|---|---|
| Personalised recommendations | Per-shopper models, collaborative filtering | §2, §16.6 |
| A/B ranking experiments | Experiment framework over ranking | §16.6, §21.4 |
| Native rerank / managed-inference (Path B) upgrade | Only if golden-set eval justifies it | §16.7, §21.4 |
| More connectors | Magento, custom carts — added by demand | §2, §16.6 |
| **Agent actions (money-moving) enabled** | Order lookup, payment links, permitted discounts, stock checks — behind strict input validation, per-tenant permissions, idempotency, and explicit shopper/operator confirmation | §7.5, §16.6, §21.4 |
| Visual / multimodal search | Image-to-product | §2, §16.6 |

## Included requirements

- **Enablement (not new build) of:** REQ-M7-008 — the agent-action tool
  interface + audit log were architected in Phase 2; Phase 4 **enables** the
  money-moving tools behind confirmation + per-action authorisation.
- No other catalog requirements are assigned to Phase 4. New v2 capabilities
  (recommenders, visual search, A/B ranking, additional connectors) will spawn
  their own requirement IDs (`REQ-M*` extensions) when scoped post-GA.

## Deliverables

- Post-GA roadmap items delivered incrementally, each behind its own scoping,
  eval, and approval gate. None bundled into GA.

## Acceptance criteria

- Each v2 capability ships only after: (a) the GA core SLOs remain green, and
  (b) for agent actions, the **money-moving confirmation + per-action
  authorisation** controls pass their guardrail/audit tests (§7.5).

## Risks (from §19)

- **Scope creep (recs, visual, agents)** (Med/High) — the dominant risk this
  phase exists to contain. The explicit out-of-scope list and the product
  owner guard the line until GA is delivered (§19.1, §21.5).

## Dependencies

- **Upstream:** GA (Phase 3) complete — stable multi-tenancy, billing,
  reliability, and instrumentation. Decision gates §21.4 govern enablement
  (e.g. agent money-moving actions decided in Phase 4; Path B decided Phase 3).
