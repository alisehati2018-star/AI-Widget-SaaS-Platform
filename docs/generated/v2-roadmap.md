# ACIP — v2 / Post-GA Roadmap

> These capabilities are **deliberately deferred** to after GA (blueprint §2
> "Deferred", §16.6, §21.5). They depend on the stable, instrumented core that
> Phases 0–3 built. Each gets its own requirement IDs, eval, and approval gate
> when scoped — they are **not** implemented during the development phases
> (scope discipline). Order is rough value priority (§21.2).

| # | Direction | Gate (§21.4) | Notes |
|---|---|---|---|
| 1 | **Agent actions (money-moving) — enablement** | "behind explicit confirmation + per-action authorisation" | **Framework built** (Phase 4): disabled by default; confirmation + permission + idempotency. Live PSP/order wiring is post-GA. |
| 2 | Personalised recommendations | post-GA | Per-shopper models / collaborative filtering over the behavioural data. |
| 3 | A/B ranking experiments | post-GA | Experiment framework over ranking; uses the golden set + live metrics. |
| 4 | Native rerank / Elastic-managed inference (Path B) | Phase-3 decision, "only if eval justifies" | Path A carries GA; Path B is an opt-in upgrade. |
| 5 | More connectors (Magento, custom carts) | by demand | Reuse the M3 connector interface + reconciliation. |
| 6 | Visual / multimodal (image-to-product) search | post-GA | Image embeddings + a new vector field; new eval set. |

## Discipline
Holding this line is the single highest-leverage decision in the plan (§21.5).
Nothing here ships until GA is delivered and the item is scoped with its own
requirements, eval, and approval. The architecture already accommodates them
(model-agnostic serving, the tool interface, the connector interface, the vector
mapping), so each is an additive change, not a re-architecture.
