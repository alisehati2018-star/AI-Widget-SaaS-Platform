# Vitrin — Expansion Plan: Phases 5–8 (Human-Facing Platform)

> Adds the surfaces the strategy requires but the repo never had: **identity &
> auth**, the **platform admin panel**, the **marketing site + signup + buy
> plan**, and the **store-owner dashboard**. Phases 0–4 (search/RAG/analytics/
> widget/gateway) stay as the engine these surfaces drive.
>
> **Security is a first-class constraint throughout** (the owner's explicit
> priority). Every phase ships its security controls as part of "done", not as
> a later hardening pass.

## Guiding principles

1. **Two distinct authentications.** Machines (stores/widgets) use scoped API
   keys (`x-api-key`, existing). People (admins/owners) use the new
   email+password → JWT identity (`acip_auth`). They never mix.
2. **Three role surfaces, one backend.** `platform_admin` (no tenant),
   `store_owner` / `store_staff` (one tenant). The tenant-isolation invariant
   already enforced for data now also gates every human read/write.
3. **Payment-provider-agnostic billing.** The "buy plan" flow records orders
   with a `provider` field (`manual` now; Stripe / ZarinPal pluggable later) so
   branding/region decisions don't block the build.
4. **Modern, professional UI.** A single Next.js 16 app (App Router, React 19,
   Tailwind) with a shared design system serves marketing + auth + both
   dashboards; the existing operator console folds into the admin panel.

## Phase 5 — Identity, Auth & Security foundation ✅ (backend done)

**Goal:** a secure identity layer everything else builds on.

- DB: `users`, `auth_sessions` (rotating refresh), `password_resets`, plan
  pricing columns, `subscriptions`, `orders` — migration `0005_identity_auth.sql`.
- `packages/acip_auth/`: PBKDF2-HMAC-SHA256 passwords (stdlib, salted,
  constant-time, rehash-on-login); compact HS256 access + rotating refresh JWTs;
  `Role` model + `AuthPrincipal`.
- `services/api/routers/auth.py`: `signup` (provisions tenant + trial),
  `login` (failed-attempt lockout, no enumeration), `refresh` (rotation +
  reuse-detection revokes all sessions), `logout`, `me`, password reset
  request/confirm, operator-gated `bootstrap-admin`.
- Security controls shipped: salted KDF, fail-closed signing (empty secret →
  503), brute-force lockout, single-use rotating refresh tokens, generic
  auth errors, password strength policy, audit-logged auth events.
- **Status:** implemented + unit-tested (`tests/test_auth.py`), gates green.
  DB-backed flows validated when Postgres is live (deferred-validation).

## Phase 6 — Platform Admin Panel + admin login

**Goal:** the platform operator runs the business from a real UI.

- Frontend (`apps/web`, admin area): admin login → dashboard (tenants, MRR,
  usage, system health), tenant detail (plan, keys, credits, suspend/erase),
  plan management, global analytics, audit-log viewer.
- Backend: role-guarded admin endpoints (replace shared-token-only gating with
  `platform_admin` JWT **or** operator token for automation); list/search
  tenants, list users, plan CRUD, subscription/credit adjustments.
- Security: admin routes require `platform_admin`; every mutation audited; admin
  session idle timeout; optional IP allowlist + (later) TOTP 2FA hook.

## Phase 7 — Marketing site + Signup + Buy Plan (billing)

**Goal:** a visitor can discover Vitrin, sign up, and purchase a plan.

- Frontend: landing (hero, features, social proof), pricing (from public
  `plans`), signup, login, password reset — modern, responsive, RTL-ready.
- Backend: public `GET /plans`; `POST /billing/checkout` (creates an `order`,
  returns a provider redirect/instructions); `POST /billing/webhook` (provider
  callback → mark order paid → activate subscription → grant credits); manual
  invoice path for enterprise.
- Security: signup rate-limited + bot-resistant; webhook signature verified;
  prices authoritative server-side (never trust client amounts); orders audited.

## Phase 8 — Store-Owner Dashboard + onboarding

**Goal:** a store owner self-serves install, keys, content, analytics, billing.

- Frontend: owner login → dashboard (search/assistant KPIs, credit balance),
  install/connect store (OpenCart/WooCommerce), API-key management, synonyms &
  zero-result tuning, leads, plan & invoices, team (invite staff), white-label
  (logo/colors), GDPR (export/erase/tracking) — all **scoped to their tenant**.
- Backend: tenant-scoped wrappers over existing analytics/synonyms/governance,
  authorized by `AuthPrincipal.can_access_tenant`; staff invitations.
- Security: every endpoint filters by the caller's `tenant_id`; staff role has
  reduced privileges; self-serve GDPR actions audited.

## Cross-cutting (every phase)

- **Testing:** unit (hermetic) gates stay green here; DB/E2E flows run where
  Postgres + a browser exist (deferred-validation tracker).
- **Observability:** auth + billing events flow to the audit log and metrics.
- **Docs:** README "Run it" updated as each surface lands.

## Execution status

| Phase | Scope | State |
|---|---|---|
| 5 | Identity/auth/security backend | **Implemented, tested** |
| 6 | Admin panel + admin login | Next |
| 7 | Marketing site + signup + buy plan | Planned |
| 8 | Store-owner dashboard | Planned |
