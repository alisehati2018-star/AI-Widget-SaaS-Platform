# Tasks — Phase 4 (v2 / Post-GA)

> Task ID scheme: `T-P4-NNN`. All items are **deferred until after GA** (§2,
> §21.5). Only **enablement** of the already-architected agent-action interface
> maps to an existing requirement; other directions spawn new requirement IDs
> when scoped post-GA.

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P4-001 | REQ-M7-008 (enable) | Enable money-moving agent actions (order lookup, payment link, permitted discount, stock check) behind input validation, per-tenant permissions, idempotency, and explicit shopper/operator confirmation. | GA complete; decision gate §21.4 | L | Confirmation + per-action authorisation pass guardrail/audit tests; GA SLOs stay green. |
| T-P4-002 | *new (post-GA scope)* | Personalised recommendations (per-shopper models, collaborative filtering). | GA core stable | XL | Scoped + eval-gated before build. |
| T-P4-003 | *new (post-GA scope)* | A/B ranking experiment framework. | GA core stable | L | Experiment framework validated on golden set. |
| T-P4-004 | *new (post-GA scope)* | Native rerank / Elastic-managed inference (Path B) upgrade. | T-P3-040 decision | M | Enabled only if eval shows worth-the-cost gain. |
| T-P4-005 | *new (post-GA scope)* | Additional connectors (Magento, custom carts) by demand. | Sync core (M3) | M | New connector passes sync integration tests. |
| T-P4-006 | *new (post-GA scope)* | Visual / multimodal (image-to-product) search. | GA core stable | XL | Scoped + eval-gated before build. |

**Note:** This phase has no fixed exit gate; each capability ships behind its
own scoping, eval, and approval gate, and must not regress GA SLOs.
