# Phase 10 — Functional Frontend Completion (audit + report)

Goal: no page left "display-only" unless intentionally read-only. Every
available backend API connected; every mutation updates the UI.

## Method
Cross-referenced the backend route surface (`services/api/routers/{tenant,admin,
billing}.py`) against every API call the frontend makes (`authFetch`/`apiFetch`
paths). Classified each page.

## Audit — owner dashboard
| Page | Intended action | Status |
|---|---|---|
| Overview | summary + verify-email resend | ✅ functional |
| Catalogue & sync | save connection (platform/url) | ✅ CRUD |
| Search tuning | save synonyms; view zero-results | ✅ CRUD |
| Assistant | save greeting | ✅ CRUD |
| Knowledge base | add / delete articles | ✅ CRUD (no *edit* — backend has no PATCH) |
| Widget & brand | save logo/colour; copy snippet | ✅ CRUD |
| Search/Chat analytics, Conversion | metrics dashboards | ✅ read-only **by design** |
| Leads | view + export JSON | ✅ functional |
| API keys | create / revoke | ✅ CRUD |
| Team | invite / change role / remove | ✅ CRUD |
| Credits | balance + ledger | ✅ read-only **by design** |
| Plan & billing | checkout / topup / cancel / resume / invoices | ✅ full lifecycle |
| Activity log | audit list | ✅ read-only **by design** |
| Settings | tracking toggle / export / erase | ✅ functional |
| Onboarding | guided steps + resend verify | ✅ functional |

## Audit — admin
| Page | Intended action | Status |
|---|---|---|
| Overview | platform KPIs | ✅ read-only by design |
| Tenants | list **+ create tenant** | ✅ **fixed this phase** (create-tenant) |
| Tenant detail | suspend/activate, tracking, **export**, erase | ✅ **fixed this phase** (export) |
| Users | suspend / activate | ✅ CRUD |
| Plans | pricing catalogue | ⚠️ read-only — **no backend edit endpoint** (honest note kept) |
| Billing | mark-paid / refund / run renewals + dunning | ✅ CRUD |
| Usage / Analytics / Models / Queue / Health / Security / Audit | monitoring | ✅ read-only by design |
| Synonyms | per-tenant edit/save | ✅ CRUD |
| Feature flags | toggle | ✅ CRUD |
| Settings | account/security info | ✅ informational by design |

## Connected this phase (backend existed, UI did not)
- **`POST /admin/tenants`** → admin "Create a tenant" form (slug/name/scope);
  returns the one-time API key; the new row appears immediately (UI updated).
- **`GET /admin/tenants/{id}/export`** → "Export data (JSON)" on tenant detail.

## Verified E2E (`npm run check:functional`)
> functional-check: 0 failure(s) — admin login · create-tenant returns one-time
> key · **new tenant row appears in the list (UI updated)** · detail page exposes
> Export.

## Honest gaps that need a *backend* endpoint first (not frontend-only)
- Knowledge **edit** (only add/delete; no `PATCH /tenant/kb/{id}`).
- Admin **plan editing** (no `POST/PATCH /admin/plans`).
- Authenticated **change-password / change-email** (only the reset flow exists).
- Leads **status/notes** (no endpoint).
These are tracked for the backend; the frontend is complete for the current API.

## Deferred by decision (ES/LLM)
`/admin/insight`, `/admin/analyst`, `/admin/zero-results` panels — require
Elasticsearch + inference (the ES phase).

## Outcome
The dashboards were already substantially functional (the "display-only" pages
are analytics/monitoring/logs, which are correctly read-only). The two genuine
unconnected admin endpoints are now wired and E2E-verified. No placeholder/
non-functional buttons remain (the Plans note is an honest "no backend yet").
