# ACIP — Master Implementation Plan

> The single execution view across all phases. Source: Blueprint §16, §17, §21,
> plus `phase-*.md`, `tasks-phase-*.md`, `traceability-matrix.md`. This plan is
> the conductor; the per-phase docs are the score.

## 1. Guiding strategy (§21.1)

Build **one thin vertical slice** end-to-end for a single pilot store as early
as possible — catalogue synced → indexed with the Persian analyzer + vectors →
searchable via hybrid RRF → fronted by a plugin replacing native search — then
**widen and harden** it. Do not build modules in isolation and integrate at the
end.

## 2. Execution order (phase gates)

```
Phase 0  Setup & Discovery        wk 1–2     M1, M12(scaffold)        → GATE
Phase 1  MVP Persian Search       wk 3–10    M2,M3,M4,M5,M6(L1/L2),M8* → GATE
Phase 2  Beta Assistant+Dashboard wk 11–18   M6(full),M7,M8,M9,M10*    → GATE
Phase 3  GA Hardening & Release   wk 19–26   M11,M12(rest),M10(final)  → GATE
Phase 4  v2 / Post-GA             after GA   agent enable + v2 dirs
```

Each `GATE` is a hard STOP for explicit human approval (see §7).

## 3. Critical path (§17.3, §21.2)

The critical path runs through **search**:

```
M1 (cluster, P0)
  └─> M2 (Persian analyzer + mapping, P1)
        └─> M4 (embeddings, P1)  ─┐
        └─> M5 (hybrid RRF search, P1) ─> PILOT SEARCH LIVE (Phase 1 exit)
                                          └─> M7 (assistant, P2)
                                                └─> M11 + M12 hardening (P3) ─> GA
```

- Anything not unblocking the spine waits.
- **M3 (sync)** runs in **parallel** with search: the reconciliation track makes
  the system demoable before the event track is perfect, so connectors never
  block relevance work.
- **M6 gateway** is split: L1/L2 cache + metering **foundation in Phase 1**
  alongside search; routing/compression/failover **ceiling in Phase 2** once
  there is real traffic to shape.
- **M12 reliability + isolation invariant** are built **as features land**, not
  retrofitted in Phase 3.

## 4. Cross-module dependency map

| Module | Depends on | Unblocks |
|---|---|---|
| M1 | — | everything |
| M2 | M1, P0 embedding decision | M3, M4, M5 |
| M3 | M2 (mapping) | M8 plugins, M10 analytics |
| M4 | P0 model decision, M1 | M5, M6 semantic cache, M7 |
| M5 | M2, M4 | M7, M8, M9 |
| M6 | M4 (embeddings), M5 (search), M1 (Redis) | M7, M11 billing, FinOps |
| M7 | M5, M6 | M8 widget chat, M10 NL analyst |
| M8 | M5 (search), M7 (chat) | pilots |
| M9 | M5, M10, M6 metrics | operator visibility |
| M10 | M3 (data), M6/M7 | insight + attribution |
| M11 | all query paths (M5/M7/analytics), M6 metering | GA |
| M12 | all services | GA reliability/CI gates |

## 5. Milestones

| Milestone | Phase exit | Hard criterion |
|---|---|---|
| **M-0 Foundations** | P0 | Healthy secured cluster + embedding model selected + agreed baseline NDCG@10. |
| **M-1 MVP Search** | P1 | Pilot live; NDCG@10 ≥ 0.80 / beats native; p95<150ms/p99<300ms; suggest<50ms; zero-result<5%. |
| **M-2 Beta** | P2 | 3–5 pilots; grounded assistant (groundedness ≥95%, TTFT<1.5s); dashboard live; cache>60%, >85% no-paid-API. |
| **M-3 GA** | P3 | Public SLA release; isolation test 100% pass; availability ≥99.9%; automated deploy + validated DR. |
| **M-4 Post-GA** | P4 | v2 capabilities shipped behind their own gates without regressing GA SLOs. |

## 6. Validation strategy (§20)

Quality is a number, not an opinion. The following are enforced in CI, in this
order (§20.4):

1. **Unit** — analyzer/normalization/ZWNJ, sync transforms, routing/cache logic, credit math.
2. **Integration** — sync→index→search→assistant end to end; webhook idempotency; reconciliation healing.
3. **Relevance (eval)** — golden-set NDCG@10 (no regression gate); assistant groundedness on judged Q&A.
4. **Tenant isolation** — 100% pass, **release blocker**.
5. **Guardrail / safety** — adversarial prompt-injection, refusal on thin context, no off-domain.
6. **Cost regression** — cache-hit + cost-per-turn on a fixed traffic replay vs baseline.
7. **Load / performance** — p95/p99 search, TTFT, suggest under concurrency (staging budgets).

Deployments are automated and reversible; **alias-swap reindexing** ensures a
rebuild never causes downtime and a bad release rolls back to the previous
alias target immediately (§14.4).

The **golden query set** (built P0, grown continuously) is the backbone of
relevance, model-selection, and rerank decisions.

## 7. Decision gates (§21.4)

| Decision | When | Decided by |
|---|---|---|
| Embedding model + dims | End of Phase 0 | Golden-set NDCG + latency/memory cost |
| Reranking on by default? | Phase 1–2 | NDCG lift vs added latency on golden set |
| Shared index vs index-per-tenant | Per onboarding | Tenant size, isolation need, RAM budget |
| Local vs paid API per query class | Phase 2, continuous | Routing holdout eval + budget policy |
| Enable Elastic-managed Path B? | Phase 3 | Eval shows quality gain worth licence cost |
| Enable money-moving agent actions | Phase 4 | Explicit confirmation + per-action authorisation |

## 8. Architecture path: A now, B if needed (§16.7)

MVP and GA run on **Path A** — free Elastic tier + self-hosted embeddings
(dense_vector + kNN), DiskBBQ for memory, self-hosted rerank and LLM. **Path B**
(Elastic-managed inference / semantic_text / native rerank) is a **Phase-3
opt-in** taken only if the golden-set eval justifies the cost. Path A is
expected to carry the platform well past GA.

## 9. Per-phase execution discipline (development rules)

Before starting **any** phase: re-read `ACIP-Blueprint.docx`, `requirements.md`,
`traceability-matrix.md`, and that phase's doc; verify scope boundaries. During
a phase: implement **only** that phase's requirements; do not pull from future
phases; invent nothing; change architecture only where the blueprint requires.

After each phase: full audit (requirements/architecture/security/performance/
multi-tenancy/API/data-model/AI/testing coverage) → gap check vs blueprint
(`reports/phase-X-gap-analysis.md`) → run all tests/static-analysis/lint/types/
security → fix failures → completion report (`reports/phase-X-completion-
report.md`) → **STOP for explicit approval** before the next phase.

## 10. Open items to resolve (from gap-analysis.md)

Carry GAP-A1..A8, GAP-B1..B8, GAP-C1..C4 into their resolution phases; close
each at or before the phase named in `gap-analysis.md`. None block writing
code in Phase 0; GAP-A1/A2/B7/B8 and ASM-4 are the **first** to close because
they gate every downstream relevance decision.
