# Vitrin — Full System Architecture & Product Strategy (authoritative)

> Consolidated from the two source analyses provided by the product owner:
> **Part 1** the control/business/AI layer (ACIP) and **Part 2** the
> Elasticsearch search/assistant engine. This is the retained source of truth;
> the legacy `.docx` "blueprint" is historical input only.

## Part 1 — Control / Business / AI layer

### Vision & market positioning
A SaaS platform for online stores that is **not** a chat widget but an
**AI Revenue & Intelligence Layer for E-Commerce** combining three roles in one
system: **AI Sales Assistant**, **AI Business Analyst**, **Customer Insight
Engine**. Goals: increase sales, analyze customer behaviour, discover sales
opportunities, make store data intelligent, automate sales operations.

### Core product modules
1. **AI Chat Widget** — answer questions, recommend products, multilingual
   (FA/EN/DE/AR), lead collection (email, phone, message).
2. **Product Intelligence** — sync products / prices / inventory / orders;
   smart product suggestions.
3. **Customer Memory System** — behaviour storage, returning-user detection,
   session + long-term memory.
4. **AI Analytics Engine** — chat analytics, sales insights (most-wanted,
   out-of-stock-but-searched, buying behaviour), opportunity discovery (market
   gaps, exit behaviour), AI Business Analyst (NL questions).
5. **Agent Actions** (future) — place orders, create payment links, check
   orders, apply discounts, call store APIs.

### Data sources (7)
Products · Orders · Customers · Categories · Pages · Chat Logs · Events.

### Multi-tenant architecture
Each store is an independent **Tenant**: separate data, settings, analytics,
and consumption.

### Integration layer
WordPress/WooCommerce plugin · OpenCart module · Custom CMS REST/Webhook/Bulk
APIs. **Event-driven sync** with incremental indexing (only changes, not full
data).

### AI architecture
- **AI Gateway** — central layer managing all models.
- **Model Router** — OpenRouter / OpenAI / Anthropic / Gemini / **Local models**.
- **Hybrid AI strategy (ladder):** L1 No-AI (cache/FAQ/rules) → L2 Search
  (Elastic retrieval) → L3 small models → L4 large models (only when needed).

### Cost control
AI Gateway + Cost Router: choose model by cost & question type. **Credit-based
billing** with model multipliers (FAQ = 0 cost, Search = low-cost model,
Reasoning = high-cost model). Multi-provider distribution + failover; future:
local inference for ~70% of traffic, edge caching, regional routing.

### Value engines
- **Analytics engine** (core value): chat/sales/behaviour analytics; key
  insight engine ("why customers leave?", "what products are missing?", "what
  causes conversion drop?").
- **Lead generation:** email/phone capture, intent detection, abandoned-chat
  recovery.
- **Attribution:** AI-influenced sales, conversion impact, AI-generated revenue.

### Governance & policy
- **White-label:** custom logo & colors allowed; platform branding stays visible.
- **GDPR & data control:** delete data, export data, disable tracking, per-tenant
  privacy controls.
- **Service segmentation:** Chat · Sync · Analytics · **Billing** services.

### Critical risks → mitigations
AI cost explosion → hybrid routing + cache + local models · provider rate
limits → multi-provider + queue · high concurrency → horizontal scaling + LB ·
sync complexity → event-driven · analytics overload → async/batching · data
inconsistency → incremental indexing.

## Part 2 — Search & Assistant engine (Elasticsearch)

On-premise, multi-tenant, Elastic 9.x. Solves two chronic problems of Persian
stores: weak internal search (raw keyword match, ZWNJ/spelling sensitivity) and
the absence of a shopping assistant.

### Modules M1–M10
M1 infra/cluster (P0) · M2 data model + Persian analyzer (P1) · M3 sync (P1) ·
M4 embedding service (P1) · M5 hybrid search engine (P1) · M6 assistant/RAG
(P2) · M7 widget + plugin (P2) · M8 admin & analytics dashboard (P2) · M9
multi-tenancy & security + billing hook (P3) · M10 observability/CI/CD/hardening
(P3).

### Data model & tenancy
Small tenant: shared index + `tenant_id` field + **mandatory filter on every
query** + scoped API key. Large tenant: index-per-tenant. Metadata in
PostgreSQL (`tenants`, `api_keys`, `plans`, `usage`). **Isolation test: any
query without `tenant_id` must be rejected** (critical security test).

### API surface
`POST /v1/search` · `GET /v1/suggest` · `POST /v1/chat` (RAG, stream) ·
`POST /v1/sync/webhook` · `POST /admin/tenants` · `GET /admin/analytics`.

### Roadmap (6 months, team of 3–4)
- **Phase 0** (wk 1–2) setup & discovery — cluster, embedding-model choice,
  golden query set.
- **Phase 1** (wk 3–10) MVP smart Persian search.
- **Phase 2** (wk 11–18) Beta — assistant + dashboard.
- **Phase 3** (wk 19–26) GA — multi-tenancy + security + billing hook +
  observability/CI/hardening.
- **Phase 4** (post-GA) native rerank, personalized recommender, A/B ranking,
  more connectors, visual search.

### KPIs
Search p95 < 150 ms · assistant first token < 1.5 s · zero-result < 5% · rising
CTR & search→add-to-cart · 99.9% availability (post-GA).

### Quality & test strategy
Relevance eval (Persian golden set, NDCG/precision) · unit + integration tests
(sync, search, assistant) · load test (p95 under concurrency) · **tenant
isolation test** · assistant guardrail test (no answers outside store data).

## Mapping to this repository

Phases 0–4 (M1–M8 search/RAG/analytics/widget + the gateway, billing ledger,
isolation, governance) are **code-complete and statically verified**. The
human-facing control surfaces the strategy calls for — the **platform admin
panel**, the **store-owner marketing site + signup + buy-plan + dashboard**, and
the **identity/auth/billing-purchase** beneath them — are delivered in the new
Phases 5–8 (`docs/generated/expansion-plan-phases-5-8.md`).
