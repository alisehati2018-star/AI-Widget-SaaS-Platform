# Phase D — Security Hardening — Completion Report

> Plan ref: `reports/recovery-plan-80plus.md` (SE-1..SE-7). Date 2026-06-21.
> Validated at runtime on the local stack (PG16 + Redis + API).

## Phase A re-check (precondition)
Re-ran Phase A end-to-end before starting: **10/10 runtime checks pass**
(signup→verify_token, checkout 403 before verify, verify-confirm, already-verified
no-op, post-verify checkout, reset email, contact 422/accept) + files present +
gates green. Phase A confirmed complete; nothing missing or broken.

## Delivered (Phase D)

### Security headers (SE-2)
`SecurityHeadersMiddleware`: `X-Content-Type-Options: nosniff`, `X-Frame-Options:
DENY`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`
(`default-src 'none'; frame-ancestors 'none'`), and `Strict-Transport-Security`
when `HSTS_ENABLED` (behind HTTPS). Toggle: `SECURITY_HEADERS_ENABLED`.

### CORS allowlist (SE-6)
`CORSMiddleware` with an explicit origin allowlist (`CORS_ALLOW_ORIGINS`, falls
back to `APP_BASE_URL`), `allow_credentials=True`, exposes `x-request-id`.
Unblocks browser/widget cross-origin calls under a controlled policy.

### Dual-support cookie auth (SE-1)
- Login/signup/refresh now **also** set httpOnly+SameSite cookies
  (`vitrin_access`, `vitrin_refresh`) + a JS-readable `vitrin_csrf` token;
  `cookie_secure`/`cookie_samesite` configurable. Logout clears them.
- `current_principal` accepts **bearer header OR access cookie**; refresh/logout
  accept the refresh cookie. Threaded through tenant (15), admin (7), billing (2)
  handlers — the whole human API accepts either auth method.
- The existing **bearer + localStorage** flow is unchanged (validated), so the
  current frontend keeps working; localStorage removal is the Phase-C/G exit item.

### CSRF protection (SE-1)
`CsrfMiddleware`: double-submit token enforced **only** for cookie-authenticated
unsafe requests (POST/PATCH/DELETE). Bearer requests are exempt (not CSRF-able),
keeping the bearer flow frictionless during the dual-support window.

### Per-IP auth rate limiting (SE-4)
`_ip_rate_ok` (Redis fixed-window) on `login`, `signup`, `verify-request`,
`reset-request` → `429 rate_limited` (`AUTH_IP_RATE_PER_MIN`, fails open if Redis
down; per-account lockout remains the backstop).

## Runtime validation (live)

| Check | Result |
|---|---|
| Security headers on responses | ✅ (CSP, X-Frame-Options, nosniff, Referrer, Permissions) |
| CORS preflight allows configured origin | ✅ |
| signup sets `vitrin_access` + `vitrin_csrf` cookies | ✅ |
| cookie auth on GET `/auth/me` + `/tenant/profile` | ✅ |
| CSRF blocks cookie POST without token | **403** ✅ |
| CSRF allows cookie POST with matching token | **200** ✅ |
| bearer POST works without CSRF (exempt, regression) | **200** ✅ |
| IP rate limit on rapid logins | **429** ✅ |

## Gates
- `ruff` clean, `mypy` clean (90 files), **99 passed / 3 skipped** (+3 middleware
  tests). Web app unchanged (bearer path intact) — no rebuild needed.

## Score impact (per plan)
- **Security 5 → ~8.5** (headers/CSP, CORS, cookie+CSRF, IP throttle on top of the
  existing isolation, PBKDF2, rotating refresh, audit, lockout).
- Projected overall: **~52 → ~58/100** (Phase B/C drive Dashboard/UX next).

## Carried / not in this phase
- **SE-3 Pydantic request models** — endpoints still validate manually (required
  fields, email regex, length bounds) but are not yet schema-modelled. Tracked as
  a follow-up (low risk; current validation is present, not absent).
- **SE-5 MFA/TOTP** — P3, deferred.
- **SE-7 GDPR retention/consent records** — P2, deferred.
- Frontend cookie migration (drop localStorage) — Phase C/G per the dual-support plan.
