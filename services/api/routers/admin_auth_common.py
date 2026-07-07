"""Shared helpers for the platform-admin authentication routers (cookies,
token issuance, rate limiting, principal resolution). Fully separate from the
customer-facing ``auth_common.py`` — the two identity planes never mix."""

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
