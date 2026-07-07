"""Shared store-owner auth dep used across every tenant_* router.

Every endpoint authenticates a *person* via their access JWT and derives the
``tenant_id`` from the authenticated principal — **never** from client input —
so a store user can only ever touch their own tenant.
"""

from __future__ import annotations

from acip_auth.models import AuthPrincipal, Role
from acip_core.errors import error_response
from fastapi import Cookie, Header

from .auth_common import current_principal

_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_access")
_TENANT_ROLES = frozenset({Role.STORE_OWNER, Role.STORE_STAFF})


async def _require_tenant(
    authorization: str | None, access_cookie: str | None = None
) -> AuthPrincipal | None:
    """Return a tenant-scoped principal, or None if not a logged-in store user."""
    principal = await current_principal(authorization, access_cookie)
    if principal is None or principal.tenant_id is None or principal.role not in _TENANT_ROLES:
        return None
    return principal


def _unauth():
    return error_response(401, "unauthenticated", "Sign in to your store account.")


def _owner_only():
    return error_response(403, "forbidden", "This action requires the store owner role.")
