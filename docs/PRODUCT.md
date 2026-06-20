# Vitrin — AI Commerce Intelligence Platform

> **Brand:** **Vitrin** (ویترین — "storefront window/display").
> **Internal platform codename:** ACIP (AI Commerce Intelligence Platform).
> **Document status:** this file + `docs/PRODUCT-STRATEGY.md` are the
> **authoritative product spec**. The older "blueprint" wording is retired —
> `ACIP-Blueprint.docx` is kept only as a historical input, not the source of
> truth.

## Why "Vitrin"

The product is not a chat widget — it is an **AI revenue & intelligence layer**
for online stores: Persian hybrid search, a grounded shopping assistant, and a
business-analytics/insight engine, delivered on-premise and multi-tenant for
OpenCart / WooCommerce.

"Vitrin" (the shop window) is short, brandable internationally, and instantly
meaningful in the Persian market the product targets. It is carried as a single
brand constant in the frontend, so renaming later is a one-line change. The
backend keeps the `acip_*` package names and `REQ-M*` requirement IDs as a
stable internal codename (common practice — the brand and the codename differ).

## Three audiences (from the consolidated strategy doc)

| Audience | Persian | Surface they need |
|---|---|---|
| Shopper | خریدار نهایی | Embeddable search + chat **widget** (exists) |
| Store owner | صاحب فروشگاه | **Marketing site → signup → buy plan → store dashboard** |
| Platform admin | ادمین پلتفرم | **Admin panel** (tenants, plans, billing, global analytics) |

The shopper widget + the entire search/RAG/analytics backend (Phases 0–4) are
code-complete. The **store-owner** and **platform-admin** human surfaces — and
the identity/auth/billing that sit under them — are the new work (Phases 5–8,
see `docs/generated/expansion-plan-phases-5-8.md`).

## Product pillars (unchanged from the strategy)

1. **AI Sales Assistant** — grounded RAG chat over the store's own catalogue.
2. **AI Business Analyst** — natural-language "why did sales drop?" answers.
3. **Customer Insight Engine** — demand gaps, zero-result mining, lead capture,
   AI-attributed revenue.

Backed by: Elasticsearch hybrid search (BM25 + dense_vector + RRF), a
local-first cost-controlled AI gateway (Cache → Route → Compress), strict
tenant isolation, credit-based billing, and GDPR controls.

## Tech stack (current)

Python 3.13 · FastAPI · Celery · PostgreSQL 18 · Redis 8 · Elasticsearch 9.4 ·
Next.js 16 / React 19 / TypeScript 6 · self-hosted TEI + vLLM · OpenTelemetry.
