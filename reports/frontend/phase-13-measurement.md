# Phase 13 — Measurement & localized emails (report)

## Accessibility measurement (axe-core)
New audit `scripts/fe-qa/a11y-check.cjs` (`npm run check:a11y`): loads key public
pages via Playwright, injects axe-core 4.12, and fails on serious/critical
violations.

**Finding (critical):** `/contact` form controls had no accessible name —
`label` rule. Root cause: the shared `Field` rendered a `<label>` that wasn't
associated with its input (login/signup only "passed" because their inputs had
placeholders, which is not proper labelling).

**Fix:** `Field` now wraps the control inside the `<label>` (implicit
association) — every form field across the app (auth, dashboard, admin) gets a
real accessible name.

**Result:**
> a11y-check: 0 serious/critical violation(s)
> (/, /en, /login, /signup, /pricing, /features, /docs, /contact)

## Performance signal
Next 16 SSG: 93 fully static pages; per-route lazy-scoped i18n bundles; fonts via
`next/font`; dependency-light client. (Full Lighthouse run is optional follow-up;
the static/light baseline is strong.)

## Localized transactional emails
`packages/acip_notify/templates.py`: `verification_email`, `reset_email` and
`invite_email` now take a `locale` and render **Persian or English**. The auth
endpoints (`/auth/signup`, `/auth/password/reset-request`, `/auth/verify-request`)
read the recipient's `NEXT_LOCALE` cookie (forwarded through the `/api` proxy)
and pass it through — so a Persian-UI user gets Persian emails.

Verified: `verification_email(.., "fa")` → «ایمیل Vitrin خود را تأیید کنید»;
English unchanged. Backend ruff/mypy clean; integration suite 7 passed/3 skipped.
