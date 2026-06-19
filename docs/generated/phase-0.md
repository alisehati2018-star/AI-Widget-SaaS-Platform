# Phase 0 — Setup & Discovery (weeks 1–2)

> Source: Blueprint §16.2, §21.2, §16.7. Modules: **M1** (Infrastructure &
> cluster), **M12** (Reliability/observability — scaffolding subset).

## Objective

Stand up a healthy, secure Elasticsearch cluster and establish a **measurable
definition of quality** before any feature is built. Nothing in this phase is
shopper-facing; it exists so that every later relevance and cost decision is
made against data, not opinion.

## Included modules

- **M1 — Infrastructure & cluster** (full).
- **M12 — Reliability, observability & CI/CD** (Phase-0 subset: scaffolding,
  baseline telemetry, the golden query set).

## Included requirements

- M1: REQ-M1-001 … REQ-M1-010 (cluster, containers, TLS/security, PostgreSQL,
  Redis, inference-service hosts, relay/mirror, free-tier Path A, network
  segmentation, secrets).
- M12: REQ-M12-009 (golden query set), REQ-M12-012 (CI + observability
  scaffolding), and the baseline of REQ-M12-003 (`/healthz`/`/readyz`),
  REQ-M12-004 (tracing/structured logs), REQ-M12-011 (Kibana + OpenTelemetry).
- Decision input from M4: candidate evaluation toward REQ-M4-001 (BGE-M3 vs
  Qwen3-Embedding) and REQ-M4-003 (MRL dimension) — the **build** of M4 is
  Phase 1; Phase 0 produces only the **selection decision**.

## Deliverables

1. Running, green, secured Elasticsearch 9.2+ cluster (TLS, security on).
2. Container topology (Docker Compose) reproducing the full stack skeleton.
3. PostgreSQL + Redis provisioned; inference-service hosts reachable.
4. CI pipeline skeleton + baseline observability (Kibana, OpenTelemetry).
5. A **~50-query Persian golden set** from a real store with judged relevance.
6. Embedding-candidate evaluation report → **chosen embedding model + dims**.
7. Baseline relevance metric (native-search NDCG@10) everyone agrees on.
8. Defined KPIs (the §18 targets recorded as the project's contract).

## Acceptance criteria

**Exit criterion (verbatim, §16.2):** *healthy cluster + embedding model
selected + a baseline quality number everyone agrees on.*

Concretely:
- Cluster health green; security + TLS verified; runs on free Elastic tier.
- Golden set committed and reproducible; baseline NDCG@10 recorded.
- Embedding model + MRL dimension chosen **on golden-set evidence** (decision
  gate §21.4).
- CI scaffolding runs; health probes and tracing emit on the skeleton services.

## Risks (from §19)

- **Weak Persian relevance from embeddings** (High/Med) → Phase-0 golden-set
  eval picks the best model; hybrid RRF (later) carries quality even if vectors
  underperform.
- **Connectivity to external providers/registries** (High/Med-High) →
  relay/mirror pattern for pulling models and packages (REQ-M1-007).
- **Key-person dependency on the search seat** (Med) → keep the golden set and
  eval reproducible and documented.
- **GPU/inference capacity shortfall** (Med) → right-size models; CPU fallback
  for degraded mode.

## Dependencies

- None upstream (this is the foundation).
- Downstream: **all** later phases depend on the cluster (M1) and the golden
  set (REQ-M12-009); the embedding-model decision unblocks M4/M5 in Phase 1.
