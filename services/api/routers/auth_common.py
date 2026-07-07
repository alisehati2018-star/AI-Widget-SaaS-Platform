"""Shared helpers for the human-authentication routers (session cookies,
token issuance/verification, rate limiting, principal resolution)."""

from __future__ import annotations

import hashlib
import ipaddress
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from acip_auth import Role, create_access_token, create_refresh_token, decode_token
from acip_auth.models import AuthPrincipal
from acip_auth.tokens import ExpiredTokenError, TokenError
from acip_core.clients import get_redis
from acip_core.config import get_settings
from acip_core.ratelimit import RateLimiter
from fastapi import Cookie, Header, Request, Response

_AUTHZ = Header(default=None, alias="authorization")
_ACCESS_COOKIE = Cookie(default=None, alias="vitrin_access")
_REFRESH_COOKIE = Cookie(default=None, alias="vitrin_refresh")
_LOCALE_COOKIE = Cookie(default=None, alias="NEXT_LOCALE")  # recipient's UI locale

_RATE_LIMITED = ("rate_limited", "Too many requests from your network. Please slow down.")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


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


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _slugify(name: str) -> str:
    base = _SLUG_RE.sub("-", name.lower()).strip("-")[:40] or "store"
    return f"{base}-{secrets.token_hex(3)}"


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
