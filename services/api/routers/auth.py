"""Human authentication surface (Phase 5, M9/M11) — session lifecycle.

People (platform admins + store owners/staff) authenticate here — distinct from
the machine scoped API keys in ``/v1/*``. Security posture:
- Passwords hashed with PBKDF2 (``acip_auth.passwords``); only hashes stored.
- Short-lived access JWTs + single-use rotating refresh tokens; refresh jtis are
  stored hashed and revocable (logout / breach).
- Brute-force defence: per-account failed-login counter + timed lockout.
- Generic error messages (no account enumeration) on login/reset.
- Self-serve signup provisions a tenant + a trial subscription + a one-time
  signup credit grant (`signup_credit_policy`) atomically.

Password reset / email verification / change-password / change-email live in
``auth_password.py``; shared cookie/token/rate-limit helpers live in
``auth_common.py``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from acip_auth import hash_password, needs_rehash, validate_password_strength, verify_password
from acip_auth.tokens import TokenError
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from acip_notify import send_email, verification_email
from fastapi import APIRouter, Request, Response

from .auth_common import (
    _ACCESS_COOKIE,
    _AUTHZ,
    _EMAIL_RE,
    _LOCALE_COOKIE,
    _RATE_LIMITED,
    _REFRESH_COOKIE,
    _clear_auth_cookies,
    _create_verification,
    _hash_token,
    _ip_rate_ok,
    _issue_tokens,
    _now,
    _set_auth_cookies,
    _slugify,
    _token_response,
    current_principal,
)
from .auth_common import decode_token as _decode_token  # re-exported for /refresh

router = APIRouter(prefix="/auth", tags=["auth"])


async def _grant_signup_credit(conn, tenant_id) -> None:
    """One-time credit grant for a brand-new signup, per the admin-editable
    `signup_credit_policy` (separate from a plan's monthly allowance, which is
    only granted on plan activation/renewal — trialing signups never hit
    that path). Runs inside the caller's signup transaction."""
    policy = await conn.fetchrow(
        "SELECT auto_grant_enabled, signup_credits FROM signup_credit_policy WHERE id"
    )
    if policy is not None and not policy["auto_grant_enabled"]:
        return
    amount = float(policy["signup_credits"]) if policy is not None else 0.0
    if amount <= 0:
        return
    await conn.execute(
        "INSERT INTO credit_ledger (tenant_id, delta, rung, reason) "
        "VALUES ($1, $2, 'grant', 'signup_bonus')",
        tenant_id,
        amount,
    )


# --------------------------------------------------------------------------- #
# Signup (self-serve store owner)                                             #
# --------------------------------------------------------------------------- #
@router.post("/signup")
async def signup(
    payload: dict[str, Any],
    request: Request,
    response: Response,
    next_locale: str | None = _LOCALE_COOKIE,
):
    s = get_settings()
    if not s.signup_enabled:
        return error_response(403, "signup_disabled", "Self-serve signup is disabled.")
    if not s.auth_secret:
        return error_response(503, "auth_unconfigured", "Authentication is not configured.")
    if not await _ip_rate_ok(request):
        return error_response(429, *_RATE_LIMITED)

    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    full_name = str(payload.get("full_name", "")).strip() or None
    store_name = str(payload.get("store_name", "")).strip()
    if not _EMAIL_RE.match(email):
        return error_response(422, "invalid_email", "A valid email is required.")
    if not store_name:
        return error_response(422, "invalid_request", "Field 'store_name' is required.")
    pw_problems = validate_password_strength(password)
    if pw_problems:
        return error_response(422, "weak_password", " ".join(pw_problems))

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM users WHERE lower(email) = $1", email):
            return error_response(409, "email_taken", "An account with this email already exists.")
        async with conn.transaction():
            plan_id = await conn.fetchval("SELECT id FROM plans WHERE code = $1", s.trial_plan_code)
            tenant_id = await conn.fetchval(
                "INSERT INTO tenants (slug, name, plan_id) VALUES ($1, $2, $3) RETURNING id",
                _slugify(store_name),
                store_name,
                plan_id,
            )
            user = await conn.fetchrow(
                "INSERT INTO users (email, password_hash, full_name, role, tenant_id, "
                "email_verified) VALUES ($1, $2, $3, 'store_owner', $4, FALSE) "
                "RETURNING id, email, full_name, role, tenant_id",
                email,
                hash_password(password),
                full_name,
                tenant_id,
            )
            if plan_id is not None:
                await conn.execute(
                    "INSERT INTO subscriptions (tenant_id, plan_id, status, current_period_end) "
                    "VALUES ($1, $2, 'trialing', $3)",
                    tenant_id,
                    plan_id,
                    _now() + timedelta(days=14),
                )
            await _grant_signup_credit(conn, tenant_id)
            tokens = _issue_tokens(conn, dict(user), request=request)
            await conn.execute(
                "INSERT INTO auth_sessions (user_id, jti_hash, user_agent, ip, expires_at) "
                "VALUES ($1, $2, $3, $4, $5)",
                user["id"],
                tokens["jti_hash"],
                tokens["ua"],
                tokens["ip"],
                tokens["expires_at"],
            )
            verify_token = await _create_verification(conn, user["id"])
        await audit(
            pool,
            actor=email,
            action="auth.signup",
            tenant_id=str(tenant_id),
            detail={"store_name": store_name},
        )
    # Send the verification email (best-effort, outside the txn).
    subject, text, html = verification_email(
        f"{s.app_base_url}/verify-email?token={verify_token}", next_locale
    )
    await send_email(email, subject, text, html)
    _set_auth_cookies(response, tokens["access"], tokens["refresh"])
    resp = _token_response(dict(user), tokens)
    if s.env != "production":
        resp["verify_token"] = verify_token  # dev convenience for testing
    return resp


# --------------------------------------------------------------------------- #
# Login                                                                       #
# --------------------------------------------------------------------------- #
@router.post("/login")
async def login(payload: dict[str, Any], request: Request, response: Response):
    s = get_settings()
    if not s.auth_secret:
        return error_response(503, "auth_unconfigured", "Authentication is not configured.")
    if not await _ip_rate_ok(request):
        return error_response(429, *_RATE_LIMITED)
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    generic = error_response(401, "invalid_credentials", "Invalid email or password.")

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash, full_name, role, tenant_id, status, "
            "failed_logins, locked_until FROM users WHERE lower(email) = $1",
            email,
        )
        if user is None:
            return generic
        if user["status"] != "active":
            return error_response(403, "account_disabled", "This account is not active.")
        if user["locked_until"] and user["locked_until"] > _now():
            return error_response(
                429,
                "account_locked",
                "Too many failed attempts. Try again later.",
            )
        if not verify_password(password, user["password_hash"]):
            attempts = int(user["failed_logins"]) + 1
            lock = (
                _now() + timedelta(minutes=s.login_lockout_minutes)
                if attempts >= s.login_max_attempts
                else None
            )
            await conn.execute(
                "UPDATE users SET failed_logins = $1, locked_until = $2 WHERE id = $3",
                attempts,
                lock,
                user["id"],
            )
            return generic

        # Success: reset counters, transparently upgrade weak hashes, issue tokens.
        async with conn.transaction():
            new_hash = hash_password(password) if needs_rehash(user["password_hash"]) else None
            await conn.execute(
                "UPDATE users SET failed_logins = 0, locked_until = NULL, "
                "last_login_at = now(), password_hash = COALESCE($1, password_hash) "
                "WHERE id = $2",
                new_hash,
                user["id"],
            )
            tokens = _issue_tokens(conn, dict(user), request=request)
            await conn.execute(
                "INSERT INTO auth_sessions (user_id, jti_hash, user_agent, ip, expires_at) "
                "VALUES ($1, $2, $3, $4, $5)",
                user["id"],
                tokens["jti_hash"],
                tokens["ua"],
                tokens["ip"],
                tokens["expires_at"],
            )
        await audit(
            pool,
            actor=email,
            action="auth.login",
            tenant_id=str(user["tenant_id"]) if user["tenant_id"] else None,
            detail={},
        )
    _set_auth_cookies(response, tokens["access"], tokens["refresh"])
    return _token_response(dict(user), tokens)


# --------------------------------------------------------------------------- #
# Refresh (rotation: old jti is revoked, new one issued)                      #
# --------------------------------------------------------------------------- #
@router.post("/refresh")
async def refresh(
    payload: dict[str, Any],
    request: Request,
    response: Response,
    vitrin_refresh: str | None = _REFRESH_COOKIE,
):
    s = get_settings()
    if not s.auth_secret:
        return error_response(503, "auth_unconfigured", "Authentication is not configured.")
    raw = str(payload.get("refresh_token", "") or vitrin_refresh or "")
    invalid = error_response(401, "invalid_token", "Invalid or expired refresh token.")
    try:
        claims = _decode_token(raw, s.auth_secret)
    except TokenError:
        return invalid
    if claims.get("typ") != "refresh":
        return invalid
    jti_hash = _hash_token(str(claims.get("jti", "")))

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            "SELECT s.id, s.revoked, u.id AS uid, u.email, u.full_name, u.role, "
            "u.tenant_id, u.status FROM auth_sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.jti_hash = $1",
            jti_hash,
        )
        # Reuse of a rotated/revoked token is a breach signal: revoke all sessions.
        if session is None or session["revoked"]:
            if session is not None:
                await conn.execute(
                    "UPDATE auth_sessions SET revoked = TRUE WHERE user_id = $1", session["uid"]
                )
            return invalid
        if session["status"] != "active":
            return error_response(403, "account_disabled", "This account is not active.")
        user = {
            "id": session["uid"],
            "email": session["email"],
            "full_name": session["full_name"],
            "role": session["role"],
            "tenant_id": session["tenant_id"],
        }
        async with conn.transaction():
            await conn.execute(
                "UPDATE auth_sessions SET revoked = TRUE WHERE id = $1", session["id"]
            )
            tokens = _issue_tokens(conn, user, request=request)
            await conn.execute(
                "INSERT INTO auth_sessions (user_id, jti_hash, user_agent, ip, expires_at) "
                "VALUES ($1, $2, $3, $4, $5)",
                user["id"],
                tokens["jti_hash"],
                tokens["ua"],
                tokens["ip"],
                tokens["expires_at"],
            )
    _set_auth_cookies(response, tokens["access"], tokens["refresh"])
    return _token_response(user, tokens)


# --------------------------------------------------------------------------- #
# Logout (revoke the presented refresh session)                              #
# --------------------------------------------------------------------------- #
@router.post("/logout")
async def logout(
    payload: dict[str, Any],
    response: Response,
    vitrin_refresh: str | None = _REFRESH_COOKIE,
):
    s = get_settings()
    raw = str(payload.get("refresh_token", "") or vitrin_refresh or "")
    if raw and s.auth_secret:
        try:
            claims = _decode_token(raw, s.auth_secret)
            jti_hash = _hash_token(str(claims.get("jti", "")))
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE auth_sessions SET revoked = TRUE WHERE jti_hash = $1", jti_hash
                )
        except TokenError:
            pass
    _clear_auth_cookies(response)
    return {"status": "logged_out"}


# --------------------------------------------------------------------------- #
# Current user                                                               #
# --------------------------------------------------------------------------- #
@router.get("/me")
async def me(authorization: str | None = _AUTHZ, vitrin_access: str | None = _ACCESS_COOKIE):
    principal = await current_principal(authorization, vitrin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    return {
        "id": principal.user_id,
        "email": principal.email,
        "role": principal.role.value,
        "tenant_id": principal.tenant_id,
        "is_admin": principal.is_admin,
    }
