"""Shared admin-plane auth deps + small helpers used across every admin_* router.

Splitting the once-monolithic `admin.py` (2400+ lines) into cohesive per-domain
routers meant every one of them needs the same authorization check and a
handful of tiny formatting helpers — this module is the single place those
live, so `_admin_ok`'s behavior (and any future change to it) is guaranteed
identical everywhere it's used.
"""

from __future__ import annotations

import secrets
from typing import Any

from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import Cookie, Header

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_admin_access")


def _authorized(token: str | None) -> bool:
    expected = get_settings().admin_token
    # If no admin token is configured, the admin plane is closed by default.
    if not expected or not token:
        return False
    return secrets.compare_digest(token, expected)


async def _admin_ok(
    token: str | None, authorization: str | None, access_cookie: str | None = None
) -> bool:
    """Authorize the admin plane via EITHER the operator token (automation) OR
    an admin-plane JWT (bearer or the admin-only cookie, from ``admin_auth``).
    The admin identity plane is fully separate from customer auth — this never
    touches the tenant `users` table."""
    if _authorized(token):
        return True
    from .admin_auth_common import admin_current_principal

    principal = await admin_current_principal(authorization, access_cookie)
    return principal is not None


def _forbidden():
    return error_response(401, "unauthorized", "A valid x-admin-token is required.")


def _not_found():
    return error_response(404, "not_found", "No such tenant.")


def _iso(v) -> str | None:
    return v.isoformat() if v is not None else None


def _valid_uuid(value: str) -> bool:
    import uuid as _uuid

    try:
        _uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


async def _key_rows(conn, tenant_id: str) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        "SELECT id, scope, label, revoked, created_at, last_used_at "
        "FROM api_keys WHERE tenant_id = $1 ORDER BY created_at DESC",
        tenant_id,
    )
    return [
        {
            "id": str(r["id"]),
            "scope": r["scope"],
            "label": r["label"],
            "revoked": r["revoked"],
            "created_at": _iso(r["created_at"]),
            "last_used_at": _iso(r["last_used_at"]),
        }
        for r in rows
    ]


__all__ = [
    "_ADMIN",
    "_AUTHZ",
    "_COOKIE",
    "_admin_ok",
    "_authorized",
    "_forbidden",
    "_iso",
    "_key_rows",
    "_not_found",
    "_valid_uuid",
]
