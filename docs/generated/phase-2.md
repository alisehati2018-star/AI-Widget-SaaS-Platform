# Phase 2 — Beta / v1: Assistant & Dashboard (weeks 11–18)

> Source: Blueprint §16.4, §21.2. Modules: **M7** (Assistant/RAG), full **M6**
> (gateway), **M8** (widget), **M9** (dashboard), first cut of **M10**.

## Objective

Add a **grounded shopping assistant** and an **operator dashboard** on a
handful of pilots, served by the full cost-control gateway — turning the search
MVP into an intelligence product while keeping AI spend near zero.

## Included modules

- **M6** — full AI gateway: routing ladder, semantic cache, compression,
  metering, provider failover, budget-aware routing, kill switches.
- **M7** — Assistant/RAG with guardrails, memory, streaming.
- **M8** — embeddable widget (full), white-label, citation cards.
- **M9** — admin + analytics dashboard with synonym and zero-result tools.
- **M10** — *first cut:* insight engine and attribution.
- **M12** — ongoing degradation/observability for the new surfaces.

## Included requirements

- **M6 (remainder):** REQ-M6-001, REQ-M6-004, REQ-M6-006, REQ-M6-007,
  REQ-M6-008, REQ-M6-009, REQ-M6-010, REQ-M6-011, REQ-M6-013, REQ-M6-014,
  REQ-M6-015. *(L1/L2/hygiene/metering carried from Phase 1.)*
- **M7:** REQ-M7-001 … REQ-M7-011. *(Money-moving agent tools stay disabled —
  REQ-M7-008 is interface + audit only.)*
- **M8:** REQ-M8-001 (widget), REQ-M8-004 (white-label), REQ-M8-005 (cards).
  *(REQ-M8-002/003 plugin installs carried from Phase 1.)*
- **M9:** REQ-M9-001 … REQ-M9-007.
- **M10 (first cut):** REQ-M10-001, REQ-M10-004, REQ-M10-005, REQ-M10-006,
  REQ-M10-007. *(REQ-M10-002 insight-"why" and REQ-M10-003 NL analyst finalise
  in Phase 3.)*
- **M12 (ongoing):** REQ-M12-001/002/004 extended to assistant + gateway paths.

## Deliverables

1. Grounded RAG assistant (scope-locked, cited, guarded, streaming) on pilots.
2. Full gateway: escalation routing, L1/L2/L3 cache, compression, metering,
   multi-provider failover, budget caps + kill switches.
3. Embeddable widget with white-label and citation/product cards.
4. Admin + analytics dashboard (synonyms, zero-result, funnels, four-dimension
   view).
5. First insight-engine cut + attribution.
6. **3–5 pilot stores with an active, grounded assistant and a working
   dashboard.**

## Acceptance criteria

**Exit criterion (Beta, verbatim §16.4):** *assistant answers strictly from
store data on pilots; dashboard live; cost-per-turn and cache-hit metrics
visible and on target.*

Concretely:
- Assistant **first token < 1.5 s** (REQ-M7-007); **groundedness ≥ 95%**
  (REQ-M7-010).
- **Cache hit > 60%**; **> 85% of turns without paid API**; cost-per-turn
  trending to near-zero (REQ-M6-014).
- Guardrails reject ungrounded/off-domain answers and fall back to search.
- Dashboard shows relevance, latency, cost, reliability side by side.

## Risks (from §19)

- **LLM cost runs away** (High/Med) → cache→route→compress; budget-aware
  routing; per-tenant metering + hard ceilings.
- **Assistant hallucination** (High/Low-Med) → strict RAG grounding, refusal on
  thin context, groundedness KPI.
- **Prompt injection via product data** (High/Med) → untrusted-data handling;
  full adversarial suite hardens in Phase 3.
- **Cache staleness serves wrong answers** (Med) → semantic-cache threshold on
  holdout; invalidate on prompt/embedding-model change.
- **GPU/inference shortfall** (Med) → continuous batching, speculative
  decoding; offload tail to API at peak.

## Dependencies

- **Upstream:** Phase 1 search + L1/L2 cache + metering foundation; Phase 0
  golden set (now extended with a judged assistant Q&A set).
- **Parallelism:** dashboard develops alongside the assistant; gateway ceiling
  hardens now that there is real traffic to shape (§21.3).
- **Downstream:** Phase 3 hardens multi-tenancy/billing/reliability over this.
