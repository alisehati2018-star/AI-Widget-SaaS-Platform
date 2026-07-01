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
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from acip_auth import (
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from acip_auth.models import AuthPrincipal
from acip_auth.tokens import ExpiredTokenError, TokenError
from acip_core.audit import audit
from acip_core.clients import get_pg_pool, get_redis
from acip_core.config import get_settings
from acip_core.errors import error_response
from acip_core.ratelimit import RateLimiter
from fastapi import APIRouter, Cookie, Header, Request, Response

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")
_ACCESS_COOKIE = Cookie(default=None, alias="vitrin_admin_access")
_REFRESH_COOKIE = Cookie(default=None, alias="vitrin_admin_refresh")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RATE_LIMITED = ("rate_limited", "Too many requests from your network. Please slow down.")


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str | None:
    host = request.client.host if request.client else None
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host


def _set_admin_cookies(response: Response, access: str, refresh: str) -> None:
    s = get_settings()
    secure = s.cookie_secure
    samesite = cast(Literal["lax", "strict", "none"], s.cookie_samesite)
    response.set_cookie(
        "vitrin_admin_access", access, httponly=True, secure=secure,
        samesite=samesite, path="/", max_age=s.access_token_ttl,
    )
    response.set_cookie(
        "vitrin_admin_refresh", refresh, httponly=True, secure=secure,
        samesite=samesite, path="/", max_age=s.refresh_token_ttl,
    )
    response.set_cookie(
        "vitrin_admin_csrf", secrets.token_urlsafe(24), httponly=False,
        secure=secure, samesite=samesite, path="/", max_age=s.refresh_token_ttl,
    )


def _clear_admin_cookies(response: Response) -> None:
    for name in ("vitrin_admin_access", "vitrin_admin_refresh", "vitrin_admin_csrf"):
        response.delete_cookie(name, path="/")


async def _ip_rate_ok(request: Request) -> bool:
    s = get_settings()
    ip = request.client.host if request.client else "unknown"
    limiter = RateLimiter(get_redis(), default_per_min=s.auth_ip_rate_per_min)
    return await limiter.allow(f"adminauthip:{ip}")


def _issue_tokens(admin: dict, *, request: Request) -> dict[str, Any]:
    s = get_settings()
    secret = s.auth_secret
    access = create_access_token(
        user_id=str(admin["id"]),
        role=Role.PLATFORM_ADMIN.value,
        tenant_id=None,
        email=str(admin["email"]),
        secret=secret,
        ttl_seconds=s.access_token_ttl,
    )
    refresh, jti = create_refresh_token(
        user_id=str(admin["id"]), secret=secret, ttl_seconds=s.refresh_token_ttl
    )
    return {
        "access": access,
        "refresh": refresh,
        "jti_hash": _hash_token(jti),
        "expires_at": _now() + timedelta(seconds=s.refresh_token_ttl),
        "ua": (request.headers.get("user-agent") or "")[:300],
        "ip": _client_ip(request),
    }


def _token_response(admin: dict, tokens: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    return {
        "access_token": tokens["access"],
        "refresh_token": tokens["refresh"],
        "token_type": "bearer",
        "expires_in": s.access_token_ttl,
        "user": {
            "id": str(admin["id"]),
            "email": admin["email"],
            "full_name": admin.get("full_name"),
            "role": "platform_admin",
            "tenant_id": None,
        },
    }


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
            "SELECT id, email, password_hash, full_name, status, failed_logins, locked_until "
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
        claims = decode_token(raw, s.auth_secret)
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
            claims = decode_token(raw, s.auth_secret)
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


async def admin_current_principal(
    authorization: str | None, access_cookie: str | None = None
) -> AuthPrincipal | None:
    """Resolve the admin access token (bearer header OR the admin-only httpOnly
    cookie) into a principal, or None. Used by every ``/admin/*`` endpoint."""
    s = get_settings()
    if not s.auth_secret:
        return None
    token: str | None = None
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    if token is None and access_cookie:
        token = access_cookie
    if not token:
        return None
    try:
        claims = decode_token(token, s.auth_secret)
    except (ExpiredTokenError, TokenError):
        return None
    if claims.get("typ") != "access" or claims.get("role") != Role.PLATFORM_ADMIN.value:
        return None
    return AuthPrincipal(
        user_id=str(claims.get("sub")),
        email=str(claims.get("email", "")),
        role=Role.PLATFORM_ADMIN,
        tenant_id=None,
        token_id=claims.get("jti"),
    )


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


@router.post("/change-password")
async def change_password(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_admin_access: str | None = _ACCESS_COOKIE,
):
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    current = str(payload.get("current_password", ""))
    new_password = str(payload.get("new_password", ""))
    pw_problems = validate_password_strength(new_password)
    if pw_problems:
        return error_response(422, "weak_password", " ".join(pw_problems))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT password_hash FROM admin_users WHERE id = $1::uuid", principal.user_id
        )
        if row is None or not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        await conn.execute(
            "UPDATE admin_users SET password_hash = $1 WHERE id = $2::uuid",
            hash_password(new_password),
            principal.user_id,
        )
    return {"status": "password_updated"}


@router.post("/change-email")
async def change_email(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_admin_access: str | None = _ACCESS_COOKIE,
):
    """Change the signed-in admin's email. No verification email is sent —
    platform admins are provisioned/managed by other admins, not self-serve."""
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    current = str(payload.get("current_password", ""))
    new_email = str(payload.get("new_email", "")).strip().lower()
    if not _EMAIL_RE.match(new_email):
        return error_response(422, "invalid_email", "A valid email is required.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email, password_hash FROM admin_users WHERE id = $1::uuid", principal.user_id
        )
        if row is None or not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        if new_email == row["email"]:
            return error_response(422, "invalid_email", "This is already your email address.")
        if await conn.fetchval(
            "SELECT 1 FROM admin_users WHERE lower(email) = $1 AND id <> $2::uuid",
            new_email,
            principal.user_id,
        ):
            return error_response(409, "email_taken", "An account with this email already exists.")
        await conn.execute(
            "UPDATE admin_users SET email = $1 WHERE id = $2::uuid", new_email, principal.user_id
        )
        await audit(
            pool,
            actor=row["email"],
            action="admin_auth.change_email",
            detail={"new_email": new_email},
        )
    return {"status": "email_changed", "email": new_email}


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
