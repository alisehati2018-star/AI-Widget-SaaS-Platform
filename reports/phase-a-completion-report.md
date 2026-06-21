# Phase A — Product Completeness — Completion Report

> Plan ref: `reports/recovery-plan-80plus.md` (gaps PR-1..PR-6, GP-1). Date
> 2026-06-21. Validated at runtime on the local stack (PG16 + Redis + API).

## Delivered

### GP-1 fix (carried in from preflight)
- asyncpg json/jsonb codec registered on the pool → JSONB reads decode to
  dict/list, writes encode from objects. Verified live: `settings` is an object,
  `audit.detail` an object, `plans.features` a list, PATCH round-trips.

### Email system (`packages/acip_notify`)
- Dependency-free mailer: **console** provider (dev; logs) + **SMTP** provider
  (stdlib `smtplib`, async via `to_thread`). Best-effort — never raises into the
  request path. Templates: verification, reset, invite, contact (subject+text+HTML).

### Email verification flow
- Migration `0007`: `email_verifications` (hashed, single-use, 24h) + `contact_messages`.
- `signup` issues a verification token + sends the email; `POST /auth/verify-request`
  (resend, no enumeration); `POST /auth/verify-confirm` (single-use → `email_verified=true`).
- **Sensitive-action gate:** `POST /tenant/billing/checkout` returns **403
  email_unverified** until verified (toggle `EMAIL_VERIFICATION_REQUIRED`).
- `password/reset-request` and `team/invite` now also send real emails.

### Contact workflow
- `POST /contact` (public): validates, persists to `contact_messages`, emails the
  platform inbox. Web contact page wired to it (was a local `setTimeout`).

### Public pages (web, Next.js)
- `/docs` (getting-started, API, widget, security), `/legal/terms`,
  `/legal/privacy`, `/verify-email` (token confirm + resend). Nav/footer updated
  (Docs, Terms, Privacy); signup shows Terms/Privacy acceptance; dashboard shows
  an **unverified-email banner** with resend.

## Runtime validation (live)

| Check | Result |
|---|---|
| signup → `verify_token`, `email_verified=false` | ✅ |
| checkout before verify | **403 email_unverified** ✅ |
| `verify-confirm` | `verified` → `email_verified=true` ✅ |
| checkout after verify | `pending` (succeeds) ✅ |
| `verify-confirm` reuse | **400 invalid_token** ✅ |
| `POST /contact` | `received` + persisted + console email ✅ |
| console emails emitted (signup + contact) | ✅ |
| migration `0007` applies | ✅ |

## Gates
- `ruff` clean, `mypy` clean (90 files), **96 passed / 3 skipped** (+3 notify tests).
- Web: `tsc` clean, `next build` OK — **34 routes** (+docs, legal/terms,
  legal/privacy, verify-email).

## Score impact (per plan)
- **Product 6.5 → 8.0** (docs, legal, email/verification, working contact).
- Security nudge (verification gate on money actions). SaaS self-service +0.5.
- Projected overall: **47 → ~52/100**.

## Notes / deferred
- SMTP delivery validated only via the console provider here (no SMTP server in
  the sandbox); real SMTP send is config-only and covered by the provider path.
- Email-verification gate currently applies to checkout; extend to other
  sensitive actions in later phases if desired.
- ES-dependent surfaces remain unvalidated (Phase G, needs Elasticsearch).
