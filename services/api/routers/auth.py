"""Human authentication surface (Phase 5, M9/M11).

People (platform admins + store owners/staff) authenticate here — distinct from
the machine scoped API keys in ``/v1/*``. Security posture:
- Passwords hashed with PBKDF2 (``acip_auth.passwords``); only hashes stored.
- Short-lived access JWTs + single-use rotating refresh tokens; refresh jtis are
  stored hashed and revocable (logout / breach).
- Brute-force defence: per-account failed-login counter + timed lockout.
- Generic error messages (no account enumeration) on login/reset.
- Self-serve signup provisions a tenant + a trial subscription atomically.
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
from acip_notify import reset_email, send_email, verification_email
from fastapi import APIRouter, Cookie, Header, Request, Response

router = APIRouter(prefix="/auth", tags=["auth"])

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")
_ACCESS_COOKIE = Cookie(default=None, alias="vitrin_access")
_REFRESH_COOKIE = Cookie(default=None, alias="vitrin_refresh")


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    """Issue httpOnly access+refresh cookies + a readable CSRF token (dual-support
    alongside the bearer tokens returned in the body)."""
    s = get_settings()
    secure = s.cookie_secure
    samesite = cast(Literal["lax", "strict", "none"], s.cookie_samesite)
    response.set_cookie(
        "vitrin_access",
        access,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
        max_age=s.access_token_ttl,
    )
    response.set_cookie(
        "vitrin_refresh",
        refresh,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
        max_age=s.refresh_token_ttl,
    )
    response.set_cookie(
        "vitrin_csrf",
        secrets.token_urlsafe(24),
        httponly=False,
        secure=secure,
        samesite=samesite,
        path="/",
        max_age=s.refresh_token_ttl,
    )


def _clear_auth_cookies(response: Response) -> None:
    for name in ("vitrin_access", "vitrin_refresh", "vitrin_csrf"):
        response.delete_cookie(name, path="/")


async def _ip_rate_ok(request: Request) -> bool:
    """Per-IP throttle for unauthenticated auth endpoints (SE-4). Fails open if
    Redis is down (the per-account lockout remains the backstop)."""
    s = get_settings()
    ip = request.client.host if request.client else "unknown"
    limiter = RateLimiter(get_redis(), default_per_min=s.auth_ip_rate_per_min)
    return await limiter.allow(f"authip:{ip}")


_RATE_LIMITED = ("rate_limited", "Too many requests from your network. Please slow down.")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _slugify(name: str) -> str:
    base = _SLUG_RE.sub("-", name.lower()).strip("-")[:40] or "store"
    return f"{base}-{secrets.token_hex(3)}"


def _secret_or_503() -> str | None:
    secret = get_settings().auth_secret
    return secret or None


async def _create_verification(conn: Any, user_id: Any) -> str:
    """Insert a hashed email-verification token and return the raw token."""
    token = secrets.token_urlsafe(32)
    await conn.execute(
        "INSERT INTO email_verifications (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
        user_id,
        _hash_token(token),
        _now() + timedelta(hours=24),
    )
    return token


def _issue_tokens(conn: Any, user: dict, *, request: Request) -> dict[str, Any]:
    """Mint an access token + persist a rotating refresh session. Caller commits."""
    s = get_settings()
    secret = s.auth_secret
    access = create_access_token(
        user_id=str(user["id"]),
        role=str(user["role"]),
        tenant_id=str(user["tenant_id"]) if user["tenant_id"] else None,
        email=str(user["email"]),
        secret=secret,
        ttl_seconds=s.access_token_ttl,
    )
    refresh, jti = create_refresh_token(
        user_id=str(user["id"]), secret=secret, ttl_seconds=s.refresh_token_ttl
    )
    return {
        "access": access,
        "refresh": refresh,
        "jti_hash": _hash_token(jti),
        "expires_at": _now() + timedelta(seconds=s.refresh_token_ttl),
        "ua": (request.headers.get("user-agent") or "")[:300],
        "ip": _client_ip(request),
    }


def _client_ip(request: Request) -> str | None:
    """Return the client host only if it's a valid IP (the `ip` column is INET);
    proxies / test clients can present a non-IP host, which must store as NULL."""
    host = request.client.host if request.client else None
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host


def _token_response(user: dict, tokens: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    return {
        "access_token": tokens["access"],
        "refresh_token": tokens["refresh"],
        "token_type": "bearer",
        "expires_in": s.access_token_ttl,
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user["role"],
            "tenant_id": str(user["tenant_id"]) if user.get("tenant_id") else None,
        },
    }


# --------------------------------------------------------------------------- #
# Signup (self-serve store owner)                                             #
# --------------------------------------------------------------------------- #
@router.post("/signup")
async def signup(payload: dict[str, Any], request: Request, response: Response):
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
    subject, text, html = verification_email(f"{s.app_base_url}/verify-email?token={verify_token}")
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
        claims = decode_token(raw, s.auth_secret)
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
            claims = decode_token(raw, s.auth_secret)
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
async def current_principal(
    authorization: str | None, access_cookie: str | None = None
) -> AuthPrincipal | None:
    """Resolve the access token (bearer header OR httpOnly cookie) into a
    principal (or None). Dual-support during the cookie migration window."""
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
    if claims.get("typ") != "access":
        return None
    try:
        role = Role(str(claims.get("role")))
    except ValueError:
        return None
    return AuthPrincipal(
        user_id=str(claims.get("sub")),
        email=str(claims.get("email", "")),
        role=role,
        tenant_id=claims.get("tid"),
        token_id=claims.get("jti"),
    )


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


# --------------------------------------------------------------------------- #
# Password reset (request + confirm) — no account enumeration                #
# --------------------------------------------------------------------------- #
@router.post("/password/reset-request")
async def reset_request(payload: dict[str, Any], request: Request):
    if not await _ip_rate_ok(request):
        return error_response(429, *_RATE_LIMITED)
    email = str(payload.get("email", "")).strip().lower()
    accepted = {"status": "accepted"}  # always generic
    if not _EMAIL_RE.match(email):
        return accepted
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id, email FROM users WHERE lower(email) = $1", email)
        if user is not None:
            token = secrets.token_urlsafe(32)
            await conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
                user["id"],
                _hash_token(token),
                _now() + timedelta(hours=1),
            )
            subject, text, html = reset_email(f"{s.app_base_url}/reset-password?token={token}")
            await send_email(email, subject, text, html)
            if s.env != "production":  # dev convenience for testing
                accepted["reset_token"] = token
    return accepted


@router.post("/verify-request")
async def verify_request(payload: dict[str, Any], request: Request):
    """(Re)send an email-verification link. Generic response (no enumeration)."""
    if not await _ip_rate_ok(request):
        return error_response(429, *_RATE_LIMITED)
    email = str(payload.get("email", "")).strip().lower()
    accepted: dict[str, Any] = {"status": "accepted"}
    if not _EMAIL_RE.match(email):
        return accepted
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email_verified FROM users WHERE lower(email) = $1", email
        )
        if user is not None and not user["email_verified"]:
            token = await _create_verification(conn, user["id"])
            subject, text, html = verification_email(f"{s.app_base_url}/verify-email?token={token}")
            await send_email(email, subject, text, html)
            if s.env != "production":
                accepted["verify_token"] = token
    return accepted


@router.post("/verify-confirm")
async def verify_confirm(payload: dict[str, Any]):
    """Confirm an email-verification token → mark the user verified (single-use)."""
    token = str(payload.get("token", ""))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id FROM email_verifications WHERE token_hash = $1 "
            "AND used_at IS NULL AND expires_at > now()",
            _hash_token(token),
        )
        if row is None:
            return error_response(400, "invalid_token", "Invalid or expired verification token.")
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET email_verified = TRUE WHERE id = $1", row["user_id"]
            )
            await conn.execute(
                "UPDATE email_verifications SET used_at = now() WHERE id = $1", row["id"]
            )
    return {"status": "verified"}


@router.post("/password/reset-confirm")
async def reset_confirm(payload: dict[str, Any]):
    token = str(payload.get("token", ""))
    new_password = str(payload.get("password", ""))
    pw_problems = validate_password_strength(new_password)
    if pw_problems:
        return error_response(422, "weak_password", " ".join(pw_problems))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id FROM password_resets WHERE token_hash = $1 "
            "AND used_at IS NULL AND expires_at > now()",
            _hash_token(token),
        )
        if row is None:
            return error_response(400, "invalid_token", "Invalid or expired reset token.")
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET password_hash = $1, failed_logins = 0, locked_until = NULL "
                "WHERE id = $2",
                hash_password(new_password),
                row["user_id"],
            )
            await conn.execute(
                "UPDATE password_resets SET used_at = now() WHERE id = $1", row["id"]
            )
            # Force re-login everywhere after a password change.
            await conn.execute(
                "UPDATE auth_sessions SET revoked = TRUE WHERE user_id = $1", row["user_id"]
            )
    return {"status": "password_updated"}


# --------------------------------------------------------------------------- #
# Bootstrap the first platform admin (operator-token gated, one-time)        #
# --------------------------------------------------------------------------- #
@router.post("/bootstrap-admin")
async def bootstrap_admin(payload: dict[str, Any], x_admin_token: str | None = _ADMIN):
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
        if await conn.fetchval("SELECT 1 FROM users WHERE lower(email) = $1", email):
            return error_response(409, "email_taken", "An account with this email already exists.")
        user_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash, full_name, role, email_verified) "
            "VALUES ($1, $2, $3, 'platform_admin', TRUE) RETURNING id",
            email,
            hash_password(password),
            full_name,
        )
    await audit(pool, actor="operator", action="auth.bootstrap_admin", detail={"email": email})
    return {"id": str(user_id), "email": email, "role": "platform_admin"}
