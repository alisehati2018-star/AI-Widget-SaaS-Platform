# Phase 4 — Completion Report (v2 / Post-GA)

> Phase 4 is "designed now, enabled later" (blueprint §16.6, §21.5). Per scope
> discipline, the only item built is the **agent-action enablement framework**
> (REQ-M7-008); the other v2 directions are documented as a roadmap, not
> implemented (no feature invention before they are scoped post-GA).

## Delivered
- **Agent-action enablement framework (T-P4-001, REQ-M7-008):**
  - Money-moving tools (`create_payment_link`, `apply_discount`) remain
    **disabled by default**; turning them on requires `AGENT_ACTIONS_ENABLED`.
  - When enabled, every money-moving call is gated by: **per-tenant permission**,
    an **explicit confirmation** step, and an **idempotency key** (re-invocation
    returns the original result, never re-runs). Read-only tools
    (`check_stock`, `order_lookup`) are always safe/enabled.
  - All invocations are audited (`ToolRegistry.audit`).
- Config: `AGENT_ACTIONS_ENABLED` (default false).
- Tests: `tests/test_agent_actions.py` — disabled-by-default, confirmation,
  permission, execution, idempotency, read-only-always-on.

## Roadmap-only (not built — `docs/generated/v2-roadmap.md`)
Per §21.4 decision gates and §2 deferral, these spawn their own requirement IDs
when scoped after GA: personalised recommendations, A/B ranking experiments,
native rerank / Elastic-managed inference (Path B), more connectors (Magento,
custom carts), visual/multimodal search.

## Test results (static)
- `ruff` ✅ · `mypy` ✅ (78 files) · `pytest` ✅ **81 passed, 3 ES-gated skipped**.

## Notes / deferred
- Live PSP/order integrations for money-moving tools, and the agent-action
  confirmation UX in the widget, are Validation-phase items (DV-301, added to
  `reports/deferred-validation.md`).
- No GA SLO regressions: Phase 4 changes are additive and off by default.
