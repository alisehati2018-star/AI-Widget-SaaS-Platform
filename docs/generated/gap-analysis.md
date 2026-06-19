# ACIP — Gap Analysis

> Identifies where the blueprint is ambiguous, silent, or in tension, plus the
> technical risks and assumptions that must be resolved before or during
> implementation. Each item has an ID and a recommended resolution + the phase
> where it must be closed. This document does **not** invent features — it flags
> decisions the blueprint defers or omits.

## A. Ambiguous requirements (need a decision)

| ID | Ambiguity | Source | Recommended resolution | Resolve by |
|---|---|---|---|---|
| GAP-A1 | Exact embedding model and dimension are deliberately undecided ("BGE-M3 vs Qwen3-Embedding, base vs larger, MRL dim"). | §5, §6.3, §21.4 | Decide on golden-set NDCG/latency/memory evidence; record in a decision log. | Phase 0 |
| GAP-A2 | "Measurable improvement over native search" has no defined margin; NDCG@10 target is "track toward ≥ 0.80". | §16.3, §18.1 | Agree a concrete pass margin (e.g. NDCG@10 ≥ 0.80 **and** ≥ X points over native) at golden-set baseline time. | Phase 0 |
| GAP-A3 | Credit→currency mapping and the per-rung multipliers (0 / very-low / low / high) are qualitative. | §8.1 | Define numeric multipliers + credit-to-currency rate per plan. | Phase 3 (M11 billing) |
| GAP-A4 | Semantic-cache similarity threshold is "tuned per tenant" with no default. | §8.2, §20.3 | Set a conservative default + per-tenant override; validate on holdout to avoid wrong-answer collisions. | Phase 2 |
| GAP-A5 | Reranking "on by default?" is explicitly left to evaluation. | §6.4, §21.4 | Gate on golden-set NDCG gain vs added latency; default off until proven. | Phase 1–2 |
| GAP-A6 | "Light stemming" scope for Persian is unspecified (over-stemming hurts). | §6.1 | Choose minimal stemming set; validate against golden set. | Phase 1 |
| GAP-A7 | Shared-index vs index-per-tenant threshold ("small" vs "large") is qualitative. | §6.7, §21.4 | Define a tenant-size/RAM-budget threshold policy per onboarding. | Phase 3 (decided per onboarding) |
| GAP-A8 | "Satisfaction signals" for chat analytics are unspecified (no explicit CSAT/thumbs mechanism). | §11.1 | Choose a signal (thumbs, deflection proxy) during dashboard design. | Phase 2 |

## B. Missing requirements (blueprint is silent)

| ID | Gap | Impact | Recommended resolution | Resolve by |
|---|---|---|---|---|
| GAP-B1 | Concrete **SLO error-budget numbers** and alert thresholds are not given (only "99.9%" + "within budget"). | Cannot gate risky changes without numbers. | Define monthly error budgets per SLO + burn-rate alerts. | Phase 3 |
| GAP-B2 | **Operator/admin auth mechanism** is named ("separated", "operator auth") but not specified (SSO? MFA? key?). | Security design ambiguity. | Choose admin auth (e.g. OIDC/SSO + MFA) explicitly. | Phase 3 |
| GAP-B3 | **Backup cadence and RPO/RTO values** are not quantified ("scheduled", "validated"). | DR cannot be validated against targets. | Set snapshot cadence + numeric RPO/RTO; rehearse. | Phase 3 |
| GAP-B4 | **Data-retention periods** for chat logs, leads (PII), and events are unspecified ("retained only as policy allows"). | GDPR/PII compliance risk. | Define per-data-type retention + scrubbing schedule. | Phase 3 (M11) |
| GAP-B5 | **Frontier API provider(s)** for the hard tail are not named (kept provider-agnostic by design). | Procurement + failover config pending. | Select ≥ 2 providers behind the gateway interface; pin at deploy. | Phase 2 |
| GAP-B6 | **Authentication of store webhooks** (signing/secret) is implied by "idempotency key" but not stated. | Spoofed-webhook risk. | Require signed webhooks + per-tenant secret. | Phase 1 (M3) |
| GAP-B7 | **Golden-set ownership/refresh cadence** beyond "grown continuously" is undefined. | Relevance drift risk. | Assign product/relevance owner + refresh ritual. | Phase 0 |
| GAP-B8 | **Specific Elastic/model version pins** are intentionally "2026 baseline"; exact builds not fixed. | Reproducibility. | Pin permissive (Apache-2.0/MIT) builds; verify model cards at deploy. | Phase 0, re-checked each deploy |

## C. Contradictions / tensions

| ID | Tension | Source | Reconciliation |
|---|---|---|---|
| GAP-C1 | "Local-first / never hard-depend on external APIs" vs the frontier-API tail for hard questions. | §3.1, §8.6, §14.1 | Resolved by design: failover **ends at a local model**; frontier is overflow, not a dependency. Document and test the local-terminating failover (REQ-M6-009). |
| GAP-C2 | Aggressive caching (cost) vs freshness/correctness (stale answers). | §8.2, §19.1 | Resolved by cache hygiene: TTLs, event-driven invalidation, never cache personalised/time-sensitive (REQ-M6-005). Treat hit-rate collapse as a budget incident. |
| GAP-C3 | "26 weeks to GA" vs summed effort "~50–55 person-weeks" for 3–4 engineers. | §17 | Resolved by overlap/parallelism, not contradiction — but schedule risk is real; track critical path (search spine) tightly. |
| GAP-C4 | Tenant isolation invariant vs shared-index default for small tenants. | §6.7, §9.1 | Resolved by mandatory `tenant_id` filter + ACORN + routing + the automated isolation test as the guarantee (REQ-M11-001/005). |

## D. Technical risks (carried from §19, with IDs)

| ID | Risk | Impact / Likelihood | Built-in mitigation |
|---|---|---|---|
| RISK-T1 | Weak Persian relevance from embeddings | High / Med | Phase-0 golden-set eval; hybrid RRF carries quality; rerank lifts top-k. |
| RISK-T2 | Vector memory / RAM cost at scale | High / Med | DiskBBQ (~95% RAM cut) + MRL dims; index-per-tenant only for large. |
| RISK-T3 | LLM cost runs away | High / Med | Cache→route→compress; >85% turns off paid model; budget caps. |
| RISK-T4 | Cache staleness serves wrong answers | Med / Med | Tenant+data-version keys; event invalidation; threshold on holdout. |
| RISK-T5 | Prompt injection via product data | High / Med | Untrusted-data handling; instruction/data separation; CI injection suite. |
| RISK-T6 | Assistant hallucination | High / Low-Med | Strict RAG grounding; refusal on thin context; groundedness KPI. |
| RISK-T7 | Scope creep (recs, visual, agents) | Med / High | Explicit out-of-scope list fenced to Phase 4; product owner guards line. |
| RISK-O1 | GPU / inference capacity shortfall | Med / Med | Right-size models; continuous batching/speculative decoding; CPU fallback. |
| RISK-O2 | Model drift / version churn | Med / Med | Pin permissive licences; verify model card at deploy; model-agnostic serving. |
| RISK-O3 | Connectivity to external providers/registries | High / Med-High | Relay/mirror; local hosting; failover ending at local model. |
| RISK-O4 | Tenant data leakage | Critical / Low | Isolation invariant everywhere; scoped keys; release-blocking test. |
| RISK-O5 | Elastic licensing / Path-B cost | Low / Low | MVP on free tier (Path A); Path B opt-in only if eval justifies. |
| RISK-O6 | Sync gaps / drift from source store | Med / Med | Dual-track sync; reconciliation auto-heals drift. |
| RISK-O7 | Key-person dependency on search seat | Med / Med | Document analyzer/mapping; reproducible golden set + eval. |

## E. Assumptions

| ID | Assumption | Basis | If false… |
|---|---|---|---|
| ASM-1 | Self-hosted GPU capacity is available for embedding/rerank/LLM. | §8.6, App D | Lean harder on CPU fallback + frontier overflow; revisit cost model. |
| ASM-2 | A relay/mirror is available for pulling models/packages under constrained connectivity. | §17.2, §19.2 | Pre-stage all artifacts; air-gapped install procedure needed. |
| ASM-3 | Path A (free Elastic tier) carries the platform through and past GA. | §5, §16.7 | Trigger the Phase-3 Path-B decision earlier. |
| ASM-4 | A real pilot store + judged Persian queries are obtainable in Phase 0. | §16.2, §20.1 | Golden set quality (and thus all relevance gating) is at risk — top priority to secure. |
| ASM-5 | OpenCart + WooCommerce are the only v1 connectors; others are demand-driven. | §2, §10.3 | Re-scope M3; additional connectors are Phase 4. |
| ASM-6 | A compact 3–4 engineer team with the named skill seats is staffed. | §17.2 | Critical-path (search spine) timeline slips; re-sequence. |

## F. Untraceable items

None. Every requirement in `requirements.md` cites a blueprint section or
appendix. All gaps above are points where the blueprint **defers or omits** a
decision, not points that contradict it.
