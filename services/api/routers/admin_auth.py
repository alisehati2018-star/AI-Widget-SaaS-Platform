"""Platform-admin authentication surface — fully separate from customer auth.

Platform admins live in their own ``admin_users`` table (migration
``0011_admin_users.sql``) with their own session table (``admin_sessions``),
their own cookies (``vitrin_admin_access`` / ``vitrin_admin_refresh`` /
``vitrin_admin_csrf``), and their own endpoints below, all under ``/admin/auth``.

Nothing here ever reads or writes the customer ``users`` table, and nothing in
``services/api/routers/auth.py`` (the customer-facing surface) ever reads or
writes ``admin_users`` — the two identity planes are isolated at both the
database and the routing layer, so a bug in one auth path can't grant access
in the other.

Session lifecycle (login/refresh/logout/me/bootstrap) lives here; account
changes (password/email) live in ``admin_auth_account.py``; TOTP two-factor
enrollment lives in ``admin_auth_totp.py``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from acip_auth import hash_password, needs_rehash, validate_password_strength, verify_password
from acip_auth.tokens import TokenError
from acip_auth.totp import verify_totp_step
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter, Request, Response

from .admin_auth_common import (
    _ACCESS_COOKIE,
    _ADMIN,
    _AUTHZ,
    _EMAIL_RE,
    _RATE_LIMITED,
    _REFRESH_COOKIE,
    _clear_admin_cookies,
    _hash_token,
    _ip_rate_ok,
    _issue_tokens,
    _now,
    _set_admin_cookies,
    _token_response,
    admin_current_principal,
)
from .admin_auth_common import decode_token as _decode_token  # re-exported for /refresh

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


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
        admin = await conn.fetchrow(
            "SELECT id, email, password_hash, full_name, status, failed_logins, locked_until, "
            "totp_secret, totp_enabled, totp_last_step "
            "FROM admin_users WHERE lower(email) = $1",
            email,
        )
        if admin is None:
            return generic
        if admin["status"] != "active":
            return error_response(403, "account_disabled", "This account is not active.")
        if admin["locked_until"] and admin["locked_until"] > _now():
            return error_response(
                429, "account_locked", "Too many failed attempts. Try again later."
            )
        if not verify_password(password, admin["password_hash"]):
            attempts = int(admin["failed_logins"]) + 1
            lock = (
                _now() + timedelta(minutes=s.login_lockout_minutes)
                if attempts >= s.login_max_attempts
                else None
            )
            await conn.execute(
                "UPDATE admin_users SET failed_logins = $1, locked_until = $2 WHERE id = $3",
                attempts,
                lock,
                admin["id"],
            )
            return generic

        # Second factor (Phase 9 hardening): once enabled, the password alone
        # never signs an admin in. A missing code gets a distinct machine code
        # so the login form can reveal the TOTP field; a WRONG code counts as
        # a failed attempt (same lockout ladder as a wrong password).
        if admin["totp_enabled"]:
            totp = str(payload.get("totp_code", "")).strip()
            if not totp:
                return error_response(
                    401, "totp_required", "Enter the 6-digit code from your authenticator app."
                )
            step = verify_totp_step(str(admin["totp_secret"]), totp)
            # Replay guard: a code at or before the last accepted step is dead,
            # even inside the clock-skew window (a sniffed code can't be reused).
            if step is None or step <= int(admin["totp_last_step"]):
                attempts = int(admin["failed_logins"]) + 1
                lock = (
                    _now() + timedelta(minutes=s.login_lockout_minutes)
                    if attempts >= s.login_max_attempts
                    else None
                )
                await conn.execute(
                    "UPDATE admin_users SET failed_logins = $1, locked_until = $2 WHERE id = $3",
                    attempts,
                    lock,
                    admin["id"],
                )
                return error_response(401, "invalid_totp", "The 6-digit code is not valid.")
            await conn.execute(
                "UPDATE admin_users SET totp_last_step = $1 WHERE id = $2", step, admin["id"]
            )

        async with conn.transaction():
            new_hash = hash_password(password) if needs_rehash(admin["password_hash"]) else None
            await conn.execute(
                "UPDATE admin_users SET failed_logins = 0, locked_until = NULL, "
                "last_login_at = now(), password_hash = COALESCE($1, password_hash) WHERE id = $2",
                new_hash,
                admin["id"],
            )
            tokens = _issue_tokens(dict(admin), request=request)
            await conn.execute(
                "INSERT INTO admin_sessions (admin_user_id, jti_hash, user_agent, ip, expires_at) "
                "VALUES ($1, $2, $3, $4, $5)",
                admin["id"],
                tokens["jti_hash"],
                tokens["ua"],
                tokens["ip"],
                tokens["expires_at"],
            )
        await audit(pool, actor=email, action="admin_auth.login", detail={})
    _set_admin_cookies(response, tokens["access"], tokens["refresh"])
    return _token_response(dict(admin), tokens)


@router.post("/refresh")
async def refresh(
    payload: dict[str, Any],
    request: Request,
    response: Response,
    vitrin_admin_refresh: str | None = _REFRESH_COOKIE,
):
    s = get_settings()
    if not s.auth_secret:
        return error_response(503, "auth_unconfigured", "Authentication is not configured.")
    raw = str(payload.get("refresh_token", "") or vitrin_admin_refresh or "")
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
            "SELECT s.id, s.revoked, a.id AS aid, a.email, a.full_name, a.status "
            "FROM admin_sessions s JOIN admin_users a ON a.id = s.admin_user_id "
            "WHERE s.jti_hash = $1",
            jti_hash,
        )
        if session is None or session["revoked"]:
            if session is not None:
                await conn.execute(
                    "UPDATE admin_sessions SET revoked = TRUE WHERE admin_user_id = $1",
                    session["aid"],
                )
            return invalid
        if session["status"] != "active":
            return error_response(403, "account_disabled", "This account is not active.")
        admin = {"id": session["aid"], "email": session["email"], "full_name": session["full_name"]}
        async with conn.transaction():
            await conn.execute(
                "UPDATE admin_sessions SET revoked = TRUE WHERE id = $1", session["id"]
            )
            tokens = _issue_tokens(admin, request=request)
            await conn.execute(
                "INSERT INTO admin_sessions (admin_user_id, jti_hash, user_agent, ip, expires_at) "
                "VALUES ($1, $2, $3, $4, $5)",
                admin["id"],
                tokens["jti_hash"],
                tokens["ua"],
                tokens["ip"],
                tokens["expires_at"],
            )
    _set_admin_cookies(response, tokens["access"], tokens["refresh"])
    return _token_response(admin, tokens)


@router.post("/logout")
async def logout(
    payload: dict[str, Any],
    response: Response,
    vitrin_admin_refresh: str | None = _REFRESH_COOKIE,
):
    s = get_settings()
    raw = str(payload.get("refresh_token", "") or vitrin_admin_refresh or "")
    if raw and s.auth_secret:
        try:
            claims = _decode_token(raw, s.auth_secret)
            jti_hash = _hash_token(str(claims.get("jti", "")))
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE admin_sessions SET revoked = TRUE WHERE jti_hash = $1", jti_hash
                )
        except TokenError:
            pass
    _clear_admin_cookies(response)
    return {"status": "logged_out"}


@router.get("/me")
async def me(authorization: str | None = _AUTHZ, vitrin_admin_access: str | None = _ACCESS_COOKIE):
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "Sign in to the admin panel.")
    return {
        "id": principal.user_id,
        "email": principal.email,
        "role": "platform_admin",
        "tenant_id": None,
        "is_admin": True,
    }


@router.post("/bootstrap")
async def bootstrap(payload: dict[str, Any], x_admin_token: str | None = _ADMIN):
    """Create the first (or an additional) platform admin — gated by the raw
    operator token (never exposed in any UI), for initial setup. Once at least
    one admin exists, use the role editor on the Users page to add more."""
    s = get_settings()
    if not s.admin_token or x_admin_token != s.admin_token:
        return error_response(401, "unauthorized", "A valid x-admin-token is required.")
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    full_name = str(payload.get("full_name", "")).strip() or None
    if not _EMAIL_RE.match(email):
        return error_response(422, "invalid_email", "A valid email is required.")
    pw_problems = validate_password_strength(password)
    if pw_problems:
        return error_response(422, "weak_password", " ".join(pw_problems))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM admin_users WHERE lower(email) = $1", email):
            return error_response(409, "email_taken", "An account with this email already exists.")
        admin_id = await conn.fetchval(
            "INSERT INTO admin_users (email, password_hash, full_name) "
            "VALUES ($1, $2, $3) RETURNING id",
            email,
            hash_password(password),
            full_name,
        )
    await audit(pool, actor="operator", action="admin_auth.bootstrap", detail={"email": email})
    return {"id": str(admin_id), "email": email, "role": "platform_admin"}
