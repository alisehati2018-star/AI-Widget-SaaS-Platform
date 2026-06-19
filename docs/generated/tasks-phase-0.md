# Tasks — Phase 0 (Setup & Discovery)

> Task ID scheme: `T-P0-NNN`. Complexity: S / M / L / XL (informed by §17
> effort estimates). Validation ties to the requirement's acceptance signal and
> the §20 test layers.

| Task ID | Requirements | Description | Dependencies | Complexity | Validation |
|---|---|---|---|---|---|
| T-P0-001 | REQ-M1-001, REQ-M1-008 | Provision Elasticsearch 9.2+ single-node cluster on the free tier (DiskBBQ/kNN/RRF/ACORN available). | — | M | Cluster health green; vector + RRF features usable. |
| T-P0-002 | REQ-M1-003, REQ-M1-010 | Enable ES security + TLS (transport + HTTP); move secrets to a secret store. | T-P0-001 | M | `xpack.security.enabled=true`; TLS verified; no secrets in images. |
| T-P0-003 | REQ-M1-002 | Author Docker Compose topology (es, postgres, redis, embeddings, reranker, llm, gateway, api, worker) as a skeleton. | T-P0-001 | M | `docker compose up` starts the skeleton stack. |
| T-P0-004 | REQ-M1-004 | Stand up PostgreSQL 16 control-plane DB + base schema (tenants, api_keys, plans, usage). | T-P0-003 | S | Schema migrations apply; DB reachable. |
| T-P0-005 | REQ-M1-005 | Stand up Redis 7 (cache + queue + rate-limit namespaces). | T-P0-003 | S | Redis reachable by gateway/api/worker skeletons. |
| T-P0-006 | REQ-M1-006, REQ-M1-007 | Stand up inference-service hosts (embeddings/reranker/llm) with relay/mirror for model + package pulls; GPU/CPU profiles. | T-P0-003 | L | Inference containers serve OpenAI-compatible APIs via mirror. |
| T-P0-007 | REQ-M1-009 | Configure network segmentation so only gateway/API are externally reachable. | T-P0-003 | S | Cluster + model servers not internet-exposed. |
| T-P0-008 | REQ-M12-012, REQ-M12-011 | Stand up CI pipeline skeleton + baseline observability (Kibana + OpenTelemetry). | T-P0-001 | M | CI runs on commit; traces/metrics flow to Kibana. |
| T-P0-009 | REQ-M12-003, REQ-M12-004 | Add `/healthz` + `/readyz` and structured logging/trace-id scaffolding to skeleton services. | T-P0-008 | S | Probes respond; requests carry trace ids. |
| T-P0-010 | REQ-M12-009 | Build the ~50-query Persian golden set from a real store with human-judged relevance; commit reproducibly. | — | L | Golden set in repo; judgements documented. |
| T-P0-011 | REQ-M12-009 | Implement the golden-set evaluation harness (NDCG@10, precision@k, zero-result rate) + native-search baseline. | T-P0-010 | M | Harness outputs baseline NDCG@10 everyone agrees on. |
| T-P0-012 | REQ-M4-001, REQ-M4-003 | Evaluate embedding candidates (BGE-M3 vs Qwen3-Embedding, base vs larger, MRL dims) on the golden set; record decision. | T-P0-006, T-P0-011 | L | Model + dim chosen on golden-set NDCG/latency/memory evidence (gate §21.4). |
| T-P0-013 | (KPIs, §18) | Record the §18 KPI targets as the project contract (relevance, latency, cost, reliability). | T-P0-011 | S | KPI sheet committed; agreed by team. |

**Phase-0 exit gate:** healthy secured cluster (T-P0-001/002) + embedding model
selected (T-P0-012) + agreed baseline quality number (T-P0-011). Then STOP for
approval before Phase 1.
