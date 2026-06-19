# ACIP — Requirements Catalog

> **Source of truth:** `ACIP-Blueprint.docx` (2026 reference architecture).
> Every requirement below is traceable to a blueprint section (`§N`) or
> Appendix (`App A–E`). This catalog is the input to the phase, task, and
> traceability documents in `docs/generated/`.

## Conventions

- **ID scheme:** `REQ-M<module>-<NNN>` — anchored to the owning module
  (Blueprint §15, M1–M12), so each requirement traces cleanly to a phase and
  task(s).
- **Category tags:** `[Functional] [Non-Functional] [Architecture]
  [Infrastructure] [Security] [Performance] [Multi-Tenancy] [AI] [Analytics]
  [Reliability] [Testing]`. A requirement may carry more than one tag.
- **Acceptance signal:** the measurable/observable condition that proves the
  requirement is met (numeric where the blueprint states a target).

| Module | Name | Target phase |
|---|---|---|
| M1 | Infrastructure & cluster | 0 |
| M2 | Data model + Persian analyzer | 1 |
| M3 | Sync service | 1 |
| M4 | Embedding service | 1 |
| M5 | Hybrid search engine | 1 |
| M6 | AI gateway + cost control | 1–2 |
| M7 | Assistant / RAG | 2 |
| M8 | Store widget + plugins | 2 |
| M9 | Admin & analytics dashboard | 2 |
| M10 | Analytics & insight engine | 2–3 |
| M11 | Multi-tenancy, security & billing | 3 |
| M12 | Reliability, observability & CI/CD | 0→3 |

---

## M1 — Infrastructure & Cluster

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M1-001 | Architecture, Infrastructure | Provision a secure, production-ready **Elasticsearch 9.2+** cluster as the single data spine for search, dense vectors, chat-memory, and analytics indices. | §3.4, §4, §5 | Cluster green; one engine hosts all four data roles. |
| REQ-M1-002 | Infrastructure | Container-first stack: Docker Compose for dev/first pilot, portable to Kubernetes with no architectural change. | §5, App D | `docker compose up` brings the full stack; same images target K8s. |
| REQ-M1-003 | Security, Infrastructure | Enable Elasticsearch security and **TLS everywhere** (cluster transport + HTTP). | §9.5, App D | `xpack.security.enabled=true`; TLS on all listeners. |
| REQ-M1-004 | Infrastructure | **PostgreSQL 16** control-plane datastore for tenants, API keys, plans, usage, billing ledger, config. | §3.4, §5, App D | Control-plane schema live; shopper-facing data stays in Elastic. |
| REQ-M1-005 | Infrastructure | **Redis 7** for caches (incl. semantic-cache index), task queue, rate limits, sessions. | §5, App D | Redis reachable by gateway/api/worker. |
| REQ-M1-006 | Infrastructure, AI | Self-hosted inference services (embeddings, reranker, LLM via vLLM/TEI), scaled independently from search; GPU when available with CPU fallback. | §8.6, App D | Three inference containers expose OpenAI-compatible APIs. |
| REQ-M1-007 | Infrastructure | **Relay/mirror pattern** to pull models and packages under constrained connectivity. | §17.2, §19.2, App D | Models/deps fetched without direct registry access. |
| REQ-M1-008 | Architecture | MVP runs entirely on the **free Elastic tier (Path A)**; no paid licence or external SaaS as a hard dependency. | §5, §16.7 | DiskBBQ, kNN, RRF, ACORN all function on free tier. |
| REQ-M1-009 | Security, Infrastructure | **Network segmentation:** cluster and model servers are not internet-exposed; only the gateway and APIs are. | §9.5, App D | Only gateway/API ports reachable externally. |
| REQ-M1-010 | Security | Secrets held in a secret store, never in code or images. | §9.5 | No secrets in repo/images; scan clean. |

---

## M2 — Data Model + Persian Analyzer

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M2-001 | Functional | Custom Persian analyzers `fa_text` (index-time) and `fa_search` (search-time) composing ZWNJ char_filter, lowercase, decimal_digit, arabic_normalization, persian_normalization, persian_stop. | §6.1, App A.1 | Analyzer produces normalized tokens per Appendix A. |
| REQ-M2-002 | Functional | **ZWNJ (U+200C / نیم‌فاصله) normalization** so "می‌روم" and "میروم" match. | §6.1, App A.1 | Variants resolve to identical tokens. |
| REQ-M2-003 | Functional | **Digit folding** (Persian ۰۱۲۳ and Arabic ٠١٢٣ → 0–9) via `decimal_digit`. | §6.1 | Model numbers/prices match across keyboards. |
| REQ-M2-004 | Functional | Character normalization (ي/ی, ك/ک), strip diacritics (tashkīl), fold presentation forms. | §6.1 | Arabic/Persian variants unify. |
| REQ-M2-005 | Functional | Curated Persian stop-word list + light stemming, tuned against the golden set (avoid over-stemming). | §6.1 | Stop/stem set validated on golden set. |
| REQ-M2-006 | Functional | Tenant-editable, **updateable synonym set** (`synonym_graph`) applied at search time without reindex. | §6.1, App A.1 | Synonym edits take effect without reindex. |
| REQ-M2-007 | Architecture | Explicit catalogue mapping (no dynamic mapping): `tenant_id`, `product_id`, `title`(+`kw`,+`suggest`), `description`, `brand`, `categories`, `attributes`(flattened), `price`(scaled_float), `in_stock`, `popularity`(rank_feature), `updated_at`, `embedding`. | App A.2 | Mapping applied via index template; no dynamic fields. |
| REQ-M2-008 | Functional | Suggestion field (`search_as_you_type` / edge-ngram) for instant autocomplete. | §6.1, §6.6, App A.2 | `title.suggest` queryable. |
| REQ-M2-009 | Architecture, Multi-Tenancy | Index shapes addressed via **aliases** for zero-downtime reindex: shared-index + `tenant_id` + routing for small tenants; index-per-tenant for large tenants. | §6.7 | Both shapes provisioned behind aliases. |
| REQ-M2-010 | Performance | Right-sized shard count (avoid over-sharding small catalogues); replicas for HA and read throughput. | §6.7, §13.2 | Shard/replica counts justified by data volume. |
| REQ-M2-011 | AI, Architecture | `dense_vector` field using **DiskBBQ** (`index_options: bbq_disk`), cosine similarity, `dims` matching the chosen model/MRL dimension. | App A.2, §6.3 | Vectors stored on disk at ~95% RAM reduction. |

---

## M3 — Sync Service

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M3-001 | Functional | **Event-driven fast path:** store webhook → Ingest API → queue → worker upsert (+ re-embed if text changed); only deltas move. | §10.1 | Product change appears in index via webhook. |
| REQ-M3-002 | Functional | **Delta reconciliation safety net:** periodic job compares store `updated_at` vs index (connector/JDBC) and repairs drift; also performs initial backfill. | §10.1 | Reconciliation repairs an injected drift; backfill loads full catalogue. |
| REQ-M3-003 | Reliability | **Idempotent upserts**; document version / `updated_at` guards against out-of-order writes. | §10.2, §3.7 | Re-delivered event causes no corruption. |
| REQ-M3-004 | Functional | **Tombstones for deletes** so removed products vanish from search promptly. | §10.2 | Deleted product no longer searchable. |
| REQ-M3-005 | Reliability | **Dead-letter queue** for repeatedly failing events; parked, never dropped, replayable after fix. | §10.2 | Poison event lands in DLQ and replays. |
| REQ-M3-006 | Reliability, Performance | **Backpressure:** queue absorbs bursts (bulk price update); embeddings batched. | §10.2 | Bulk update does not overwhelm cluster. |
| REQ-M3-007 | Functional | **OpenCart module** connector: full catalogue sync, inventory, order/event webhooks, widget install. | §10.3 | OpenCart store syncs end-to-end. |
| REQ-M3-008 | Functional | **WordPress/WooCommerce plugin:** widget install, product + order sync, change webhooks. | §10.3 | Woo store syncs end-to-end. |
| REQ-M3-009 | Functional | **Custom REST API connector:** REST endpoints, webhook intake, bulk import for non-standard carts. | §10.3 | Non-standard cart can ingest via REST. |
| REQ-M3-010 | Functional | Ingest the **seven data sources:** products, orders, customers, categories, pages, chat logs, events. | §10.4 | All seven sources flow to their consumers. |
| REQ-M3-011 | Performance | Sync freshness (event path): catalogue change reflected in **< 1 min typical**. | §18.4 | Measured propagation latency < 1 min. |
| REQ-M3-012 | Reliability | System is correct even if **every webhook is lost** (reconciliation catches up). | §10.3 | Disabling webhooks still converges via reconciliation. |

---

## M4 — Embedding Service

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M4-001 | AI | Self-hosted embedding service (**BGE-M3** primary / **Qwen3-Embedding** alt) behind an interface. | §5, §8.6 | Embedding API returns vectors for Persian text. |
| REQ-M4-002 | AI, Performance | **Batched** embedding generation during sync (off shopper path). | §8.5 | Bulk embed runs as batched queue job. |
| REQ-M4-003 | AI | **Matryoshka (MRL) dimension truncation** to the smallest dim that holds NDCG on the golden set. | §6.3, §8.4 | Chosen dim documented with NDCG evidence. |
| REQ-M4-004 | AI, Performance | Embedding/score cache for stable catalogues. | §6.4 | Repeated embeds served from cache. |
| REQ-M4-005 | Architecture | **Model-agnostic** serving: model swap is config + reindex, not re-architecture. | §5 | Swapping model needs no code change. |
| REQ-M4-006 | Reliability | CPU fallback path for degraded mode. | App D | Embeddings still produced (slower) without GPU. |

---

## M5 — Hybrid Search Engine

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M5-001 | Functional, AI | **Hybrid retrieval:** BM25 lexical leg + kNN dense-vector leg fused with the **RRF retriever**. | §6.2, App B | One request fuses both legs via `rrf`. |
| REQ-M5-002 | Functional | Field boosts: `title^3` > `brand^2` > `description`. | §6.2, App B | Boosts present in multi_match. |
| REQ-M5-003 | AI | Optional learned-sparse leg (BGE-M3) for rare-term recall. | §6.2 | Sparse leg toggleable. |
| REQ-M5-004 | Performance | **DiskBBQ with oversample + rescore** as the recall/latency dial, tuned on golden set. | §6.3, §13.2 | Oversample factor set with NDCG/latency evidence. |
| REQ-M5-005 | Performance, Multi-Tenancy | **ACORN filtered vector search** applies `tenant_id` + facet filters during traversal (no post-filter over-fetch). | §6.5 | Filtered kNN stays fast and correct. |
| REQ-M5-006 | AI | Optional, **eval-gated cross-encoder rerank** (BGE-reranker-v2-m3 / Qwen3-Reranker-0.6B) on top-k only (docs < 512 tokens), batched, score-cached. | §6.4, App B | Rerank enabled only if golden-set NDCG gain justifies latency. |
| REQ-M5-007 | Functional, Performance | `/v1/suggest` instant autocomplete with a tight latency budget; curated list fed by popular-query and zero-result data. | §6.6, §12 | Suggest endpoint live. |
| REQ-M5-008 | Functional, Analytics | **Zero-result loop:** every zero-result query logged → routed into synonym / analyzer-gap / catalogue-gap loops. | §6.8 | Zero-result queries captured and surfaced. |
| REQ-M5-009 | Reliability | **Graceful degradation:** missing embedding service → BM25 lexical; missing reranker → fused un-reranked results. | §6.2, §14.1 | Search still returns results with a leg disabled. |
| REQ-M5-010 | Performance | Search latency **p95 < 150 ms**, **p99 < 300 ms**; suggest **< 50 ms** (server-side, filtered, rerank on top-k only). | §18.2 | Load test meets budgets. |
| REQ-M5-011 | Performance | **Zero-result rate < 5%** of searches. | §18.1, §6.8 | Measured rate < 5%. |
| REQ-M5-012 | Functional | `/v1/search` with filters, facets, and cursor/keyset pagination. | §12, §12.1 | Endpoint supports filters + keyset paging. |
| REQ-M5-013 | Testing | **NDCG@10** beats native search by a clear margin, tracked toward **≥ 0.80** on the golden set. | §18.1 | Golden-set NDCG@10 ≥ 0.80 / beats native. |

---

## M6 — AI Gateway + Cost Control

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M6-001 | AI, Architecture | Thin, **stateless gateway** in front of all model calls: routing, caching, cost accounting, provider failover. | §4.2, §8 | All model calls traverse the gateway. |
| REQ-M6-002 | AI | **L1 exact cache:** hash normalized prompt + tenant + data version → instant stored answer. | §8.2, App C | Verbatim repeat served from L1 (~0 cost). |
| REQ-M6-003 | AI | **L2 semantic cache:** embed query + kNN over prior Q/A; return if similarity ≥ per-tenant tuned threshold. | §8.2, App C | Paraphrase served from L2; threshold validated on holdout. |
| REQ-M6-004 | AI, Performance | **L3 provider/prefix cache:** reuse stable prefix (system prompt, tenant instructions, reused context) via vLLM KV/prefix and hosted prompt caching. | §8.2 | Prefix reuse cuts cost/first-token on model calls. |
| REQ-M6-005 | Reliability, Security | **Cache hygiene:** TTLs; invalidate product answers on price/stock change; bust semantic cache on prompt/embedding-model change; never cache personalized/time-sensitive turns. | §8.2, §19.1 | Stale answers not served; hit-rate regression alerted. |
| REQ-M6-006 | AI | **Escalation ladder routing:** cache → rule/FAQ → search-only → local LLM (RAG) → frontier API (RAG); each turn stops at the cheapest rung that answers well. | §4.3, §8.3, App C | Most turns resolve below the model rungs. |
| REQ-M6-007 | AI, Testing | **Eval-driven router** validated on a labelled holdout; re-run whenever a model or threshold changes. | §8.3, §20.3 | Router escalates only when cheaper tiers measurably fail. |
| REQ-M6-008 | AI, Multi-Tenancy | **Budget-aware routing:** bias toward cheaper rungs as a tenant nears its plan ceiling; at the hard cap, stop escalating to paid models. | §8.3 | Spend cannot exceed tenant cap. |
| REQ-M6-009 | Reliability | **Multi-provider, health-checked failover** for the frontier tail, ending at a local model. | §8.3, §8.6, §14.2, App C | Provider outage falls over; never hard-depends on reachability. |
| REQ-M6-010 | AI, Performance | **COMPRESS:** prune context to reranked top passages; terse structured prompts; summarized memory; MRL-truncated embeddings. | §8.4 | 30–50% token reduction with held quality. |
| REQ-M6-011 | AI | **BATCH** heavy non-interactive work (embeddings, analytics, reports) asynchronously on the queue. | §8.5 | Heavy jobs never run on shopper path. |
| REQ-M6-012 | Analytics, Reliability | Emit a **usage record per model call:** tenant, route, rung, tokens in/out, cache outcome, latency, cost. | §8.7 | Every call produces a usage record. |
| REQ-M6-013 | AI | **FinOps governance:** per-tenant/per-feature attribution; soft budgets + alerts; hard caps; per-tenant and **global kill switch** to local-only. | §8.7 | Budgets enforced; kill switch forces local path. |
| REQ-M6-014 | Performance | Cache hit rate **> 60%** of assistant turns; **> 85%** of turns served without paid API; cost-per-turn trending to near-zero. | §18.3 | Dashboard meets cost-efficiency targets. |
| REQ-M6-015 | AI | Lightweight intent/difficulty **classifier** (rules + small model or embedding score) labels each turn for routing. | §8.3 | Classifier labels turns trivial/normal/hard. |

---

## M7 — Assistant / RAG

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M7-001 | AI, Functional | **RAG pipeline:** understand → cache check → retrieve (RRF, tenant-scoped) → rerank → compress → generate (local/frontier) → guardrail → stream + cache. | §7.1 | All 8 stages observable with budgets/fallbacks. |
| REQ-M7-002 | AI, Security | **Scope lock:** system prompt + retrieval constrained to the tenant's catalogue/pages; model answers only from supplied context, else says it does not know. | §7.2 | Off-context question gets a grounded refusal. |
| REQ-M7-003 | AI | **Citations/evidence:** answers reference source products/pages; widget renders them as cards. | §7.2 | Answers carry verifiable source references. |
| REQ-M7-004 | AI, Security | **Output guardrail** rejects answers introducing unsupported facts, leaking other tenants' data, or straying off-domain; falls back to ranked search. | §7.2 | Guardrail trips → search fallback. |
| REQ-M7-005 | Security, Testing | **Prompt-injection defence:** retrieved store content treated as untrusted data, delimited, never instructions; adversarial test suite in CI (Phase 3). | §7.2, §19.1, §20.2 | Injection suite passes; malicious product text cannot change behaviour. |
| REQ-M7-006 | Functional | **Conversational memory:** session memory in Redis; long-term memory in Elasticsearch; summarized/truncated to bound prompt + cost. | §7.3 | Both memory tiers operate; prompt stays bounded. |
| REQ-M7-007 | Performance | **Streaming (SSE)** with **first token < 1.5 s** via local model + prefix/KV cache + compression; speculative decoding optional. | §7.4, §18.2 | TTFT < 1.5 s on pilots. |
| REQ-M7-008 | AI | **Agent-action tool interface + audit log architected now**; money-moving tools disabled until post-GA, behind validation/permissions/idempotency/confirmation. | §7.5 | Tool interface + audit exist; money tools off. |
| REQ-M7-009 | Reliability | LLM unavailable → return **ranked search results + short templated message**. | §14.1 | Assistant degrades to search. |
| REQ-M7-010 | AI, Testing | **Assistant groundedness ≥ 95%** of answers attributable to store data (sampled and judged). | §18.1 | Sampled groundedness ≥ 95%. |
| REQ-M7-011 | Functional | `/v1/chat` streaming RAG endpoint. | §12 | Endpoint streams tokens. |

---

## M8 — Store Widget + Plugins

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M8-001 | Functional | Embeddable, lightweight **Next.js/React widget** consuming the search + assistant APIs. | §5, §4.1 | Widget embeds and calls `/v1/search` + `/v1/chat`. |
| REQ-M8-002 | Functional | **OpenCart module** install that replaces native search and installs the widget. | §10.3, §16.3 | Native search replaced on pilot. |
| REQ-M8-003 | Functional | **WordPress/Woo plugin** widget install. | §10.3 | Widget installs on WordPress/Woo. |
| REQ-M8-004 | Functional, Multi-Tenancy | **White-label:** custom logo/colours (presentation only); platform branding remains per policy; never weakens isolation. | §9.6 | Branding configurable; isolation intact. |
| REQ-M8-005 | Functional | Widget surfaces citation/product cards from assistant answers. | §7.2 | Cards rendered from evidence. |

---

## M9 — Admin & Analytics Dashboard

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M9-001 | Functional | Admin console for tenants, API keys, and plans (`/admin/tenants`). | §12, §4.2 | Operator can CRUD tenants/keys/plans. |
| REQ-M9-002 | Functional | **Synonym & curated-suggestion management** tools (`/admin/synonyms`). | §12, §6.1 | Operator edits synonyms/suggestions. |
| REQ-M9-003 | Functional, Analytics | **Zero-result view** feeding the relevance loop. | §6.8 | Zero-result queries listed and actionable. |
| REQ-M9-004 | Analytics | Analytics dashboards/endpoints: search, zero-result, funnel, conversion stats (`/admin/analytics`). | §12, §11.1 | Stats rendered per tenant. |
| REQ-M9-005 | Analytics | **One dashboard, four dimensions:** relevance, latency, cost, reliability shown side by side. | §18, §18.4 | Single view surfaces all four. |
| REQ-M9-006 | Analytics | **Chat analytics surface:** volume, engagement rate, top questions, deflection, satisfaction signals. | §11.1 | Chat metrics rendered. |
| REQ-M9-007 | Analytics | **Behaviour analytics:** search → click → cart funnels, drop-off points, returning-shopper patterns. | §11.1 | Funnels rendered. |

---

## M10 — Analytics & Insight Engine

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M10-001 | Analytics | **Sales insights:** most-wanted products, searched-but-out-of-stock items, purchase-behaviour patterns. | §11.1 | Insights computed from Elastic data. |
| REQ-M10-002 | Analytics | **Insight engine answers "why?"** (sales drop, abandonment, missing products) by mining Elastic data (zero-result clusters, OOS-but-searched, funnel drop-off, emerging themes). | §11.2 | "Why" answers backed by aggregations. |
| REQ-M10-003 | Analytics, AI | **AI Business Analyst:** NL Persian question → ES aggregations/ES\|QL → LLM **narrates returned numbers only** (same grounding discipline), linking to the breakdown. | §11.3 | Analyst reports figures, never invents. |
| REQ-M10-004 | Analytics | **Lead generation:** in-conversation email/phone capture, intent detection, abandoned-chat recovery. | §11.4 | Leads captured with intent. |
| REQ-M10-005 | Analytics | **Attribution:** AI-influenced sales, conversion impact, revenue generated through the assistant. | §11.4 | ROI/attribution reported. |
| REQ-M10-006 | Performance, Multi-Tenancy | All analytics run **async/batch, isolated from the shopper path**, and tenant-scoped through the mandatory filter. | §11.5 | Heavy aggregation never affects search/chat latency. |
| REQ-M10-007 | Analytics | **Customer-insight engine:** demand gaps, OOS-but-wanted, drop-off causes, returning-customer behaviour. | §2, §11 | Insight surfaces produced. |

---

## M11 — Multi-Tenancy, Security & Billing

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M11-001 | Multi-Tenancy, Security | **Mandatory `tenant_id` filter** applied in a single central query-builder that no endpoint bypasses (search, suggest, chat retrieval, analytics). | §9.1 | Every query carries the filter via one builder. |
| REQ-M11-002 | Security | **Scoped, least-privilege API keys** bound to a tenant and role (shopper-widget key cannot reach admin/analytics). | §9.2, §12.1 | Key scope enforced per request. |
| REQ-M11-003 | Multi-Tenancy, Performance | **Per-tenant rate limits & quotas** enforced at the gateway by plan. | §9.2 | Over-quota tenant throttled. |
| REQ-M11-004 | Security | **Operator/admin auth** separated from tenant APIs and protected independently. | §9.2 | Admin plane behind operator auth. |
| REQ-M11-005 | Multi-Tenancy, Security, Testing | **Automated tenant-isolation test:** asserts no query path returns data without a `tenant_id` filter and no key can read another tenant's data; runs in CI and **fails the build (100% pass, release blocker)**. | §9.3, §18.4, §20.2 | CI gate fails on any cross-tenant path. |
| REQ-M11-006 | Security | **GDPR-style per-tenant controls:** delete (index + memory + logs), export, disable tracking, PII minimisation, on-premise data residency. | §9.4 | Delete/export/disable verified per tenant. |
| REQ-M11-007 | Security | **Audit logging** of admin actions, key issuance, and money-moving agent tools. | §9.5 | Audited actions logged immutably. |
| REQ-M11-008 | Security | Regular **dependency & image scanning**; least-privilege service accounts. | §9.5 | Scans run in CI; least-privilege enforced. |
| REQ-M11-009 | Functional | **Credit-based billing:** credit ledger, credit→cost model multiplier per rung (0 / very-low / low / high), usage metering, plan enforcement. | §8.1, §4.2 | Credits metered per rung; plans enforced. |
| REQ-M11-010 | Multi-Tenancy | White-labelling is presentation-only and **never weakens tenant isolation or the control plane**. | §9.6 | Branding changes leave isolation intact. |

---

## M12 — Reliability, Observability & CI/CD

| ID | Tags | Requirement | Source | Acceptance signal |
|---|---|---|---|---|
| REQ-M12-001 | Reliability | Implement the **graceful-degradation matrix** for each dependency failure (frontier API, local LLM, reranker, embeddings, Redis, cluster). | §14.1 | Each row's fallback verified. |
| REQ-M12-002 | Reliability | **Resilience patterns:** circuit breakers; per-tenant + per-dependency bulkheads/concurrency limits; timeouts with bounded, jittered retries; end-to-end idempotency. | §14.2 | Failing dependency trips fast; one tenant cannot starve others. |
| REQ-M12-003 | Reliability, Infrastructure | **Health & readiness probes** (`/healthz`, `/readyz`) on every service. | §12, §14.3 | Probes drive LB/orchestrator. |
| REQ-M12-004 | Reliability, Non-Functional | **Tracing + structured logs** on every request; trace id in every response envelope; every AI call logs route/tokens/cost/cache outcome. | §3.8, §12.1, §14.3 | Requests traceable end to end. |
| REQ-M12-005 | Reliability | **Snapshots/backups** (Elasticsearch + PostgreSQL) with tested restore; documented **DR** with recovery objectives validated before GA. | §14.4 | Restore drill succeeds; RPO/RTO recorded. |
| REQ-M12-006 | Reliability | **Zero-downtime alias-swap reindex** with instant rollback for schema/analyzer changes. | §14.4, §6.7 | Reindex swaps alias atomically; rollback instant. |
| REQ-M12-007 | Reliability, Performance | **SLOs + error budgets** post-GA; alarms on latency tail (p95/p99), availability, cache-hit regression; **availability ≥ 99.9%**. | §14.5, §18.4 | SLOs tracked; alarms fire on burn. |
| REQ-M12-008 | Testing | **Test layers:** unit, integration, relevance (eval), load/performance, tenant-isolation, guardrail/safety, cost-regression. | §20.2 | All seven layers exist in CI. |
| REQ-M12-009 | Testing | **Golden query set** (~50 judged Persian queries) built in Phase 0, grown continuously; CI relevance gate (no NDCG regression). | §20.1, §3.5 | Golden set in repo; gate active. |
| REQ-M12-010 | Testing | **CI/CD gates in order:** unit+integration → relevance eval (no NDCG regression) → isolation (100%) → guardrail → cost-regression replay; perf budgets checked on staging; **automated, reversible deploys**. | §20.4 | Pipeline enforces ordered gates. |
| REQ-M12-011 | Non-Functional | **Observability stack:** Kibana + OpenTelemetry + per-call AI cost/latency/cache analytics. | §5 | Cluster + app traces + AI analytics visible. |
| REQ-M12-012 | Reliability | CI + observability **scaffolding stood up in Phase 0** (operability is part of the MVP, not a Phase-3 afterthought). | §16.2, §3.8 | Baseline pipeline + telemetry live in P0. |

---

## Cross-cutting principles (apply to all modules)

These tenets (§3) are non-negotiable design constraints that every requirement
must respect; they are the tie-breakers for any ambiguity:

1. **Local-first AI** — self-hosted embed/rerank/LLM default; frontier API is the tail (§3.1).
2. **Graceful degradation** — search never depends on AI (§3.2).
3. **Cost is a first-class constraint** — budgeted, attributed, capped (§3.3).
4. **Elasticsearch as the single spine** (§3.4).
5. **Eval-driven quality** — the golden set arbitrates relevance changes (§3.5).
6. **Tenant isolation is a security invariant** — enforced in code, release-blocking (§3.6).
7. **Idempotent, event-driven data flow** — self-healing via reconciliation (§3.7).
8. **Boring, observable infrastructure** — operability from day one (§3.8).

**Requirement count:** 119 (M1:10, M2:11, M3:12, M4:6, M5:13, M6:15, M7:11,
M8:5, M9:7, M10:7, M11:10, M12:12).
