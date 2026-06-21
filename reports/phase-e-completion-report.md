# Phase E — Billing & SaaS Operations (manual model) — Completion Report

> Plan ref: `reports/recovery-plan-80plus.md` (BI-2/BI-3/BI-4; BI-1 live gateway
> deferred to P3 by owner decision). Date 2026-06-21. Validated end-to-end at
> runtime on the local stack (PG16 + Redis + API).

## Delivered

### Data model (migration `0009`)
- `orders.kind` (subscription | topup) + `orders.credits`; `orders.plan_id`
  nullable (top-ups have no plan); `invoices` table with sequential `number`.

### Billing engine (`acip_billing.subscription`)
- **Proration**: `_proration_credit` + `proration_preview` (credit for the unused
  portion of the current paid plan when switching).
- **Orders**: `create_order` (now prorated) + `create_topup_order` (priced by
  `TOPUP_CREDITS_PER_UNIT`).
- **mark_order_paid** is now kind-aware: top-ups grant credits, subscriptions
  activate the plan; **both issue an invoice**. Idempotent.
- **Lifecycle**: `set_cancel` (cancel/resume at period end), `process_renewals`
  (period-end → downgrade cancelled subs to free; others → `past_due`),
  `list_past_due` (dunning feed).

### API
- Tenant: `GET /tenant/billing/preview`, `POST /tenant/billing/topup`,
  `POST /tenant/billing/cancel` + `/resume`, `GET /tenant/billing/invoices`.
- Admin: `POST /admin/billing/run-renewals`, `POST /admin/billing/run-dunning`;
  `mark-paid` now emails the invoice + reports kind/invoice number.
- Webhook: emails invoice on paid; reports kind.
- Emails: invoice receipt + dunning reminder (console provider in dev).

### Frontend
- **Dashboard billing:** proration confirm on upgrade, **buy-credits** top-up,
  **cancel/resume**, **invoices** table (+ orders).
- **Admin billing:** **Run renewals** + **Run dunning** buttons with result toast.

## Runtime E2E (live) — 20/20

| Step | Result |
|---|---|
| Checkout starter → server price $49 | ✅ |
| Admin mark-paid → active + invoice + 50k credits | ✅ |
| Proration preview: $149 base − $49 credit = $100 due | ✅ |
| Upgrade to pro via **signed webhook** (prorated amount) | ✅ |
| Credit top-up: 50k priced $50 → **+50,000 credits granted** | ✅ |
| Invoices list (starter + pro + topup = 3) | ✅ |
| Cancel (schedule) + resume | ✅ |
| Renewals → `past_due`; dunning emails the owner | ✅ |
| Cancel-at-period-end → **downgrade to Free** | ✅ |

Plus hermetic unit tests: proration math, top-up pricing, no-DB safety, webhook
signature (`tests/test_billing.py`).

## Gates & regression
- `ruff` clean, `mypy` clean (90 files), **101 passed / 3 skipped**.
- Web: `tsc` clean, `next build` OK — **47 routes**.
- No regressions: trial subs are not prorated (starter billed full $49); email-
  verification gate still blocks checkout/top-up; admin dual-auth intact.

## Score impact (per plan)
- **Billing ~5 → ~7.5** (full lifecycle on the manual model; live card capture
  intentionally deferred), **SaaS ~5 → ~7.5**.
- Projected overall: **~70 → ~74/100**.

## Carried
- BI-1 live PSP (Stripe/ZarinPal) — P3 by decision; drops into the existing
  signed `/billing/webhook` with no schema change.
- Invoice **PDF** artifact (currently emailed text/HTML receipt + on-screen list).
- Renewals/dunning are admin-triggered here; a scheduled worker beat lands with
  Phase F observability/reliability.
