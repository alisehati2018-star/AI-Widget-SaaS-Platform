# Phase 0 Decision Log — Embedding Model Selection (T-P0-012 / GAP-A1)

> Records the embedding-model decision **on golden-set evidence** (blueprint
> §21.4). Fill in once the golden set is populated with a real store's judged
> queries and candidates are run via `eval/embedding_eval.py`. Until then this
> is the template; the decision is an explicit Phase-0 exit gate.

## Candidates evaluated

| Candidate | Dims (native / MRL) | NDCG@10 | p95 latency | Vector RAM/1M | Licence |
|---|---|---|---|---|---|
| BGE-M3 | 1024 / — | _TBD_ | _TBD_ | _TBD_ | MIT |
| Qwen3-Embedding | _/ MRL_ | _TBD_ | _TBD_ | _TBD_ | Apache-2.0 |

## Baseline

- Native store search NDCG@10: **_TBD_** (the number Phase 1 must beat).

## Decision

- **Chosen model:** _TBD_
- **Chosen dimension (MRL):** _TBD_ — smallest dim that holds NDCG (§6.3).
- **Rationale:** _TBD (NDCG vs latency vs vector memory)._
- **Decided by / date:** _TBD_

## Notes

- Re-confirm the exact model card + permissive licence at deploy time (§5).
- Serving stays model-agnostic so a swap is config + reindex, not a rewrite.
