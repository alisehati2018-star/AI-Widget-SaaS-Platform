"""Identity model: human roles + the resolved request principal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """Human roles (distinct from machine ``KeyScope``).

    - ``PLATFORM_ADMIN`` operates the whole platform: tenants, plans, billing,
      global analytics. Has no single owning tenant.
    - ``STORE_OWNER`` owns one tenant (store): manages their dashboard, keys,
      synonyms, billing, and team.
    - ``STORE_STAFF`` is invited into a tenant with reduced privileges.
    """

    PLATFORM_ADMIN = "platform_admin"
    STORE_OWNER = "store_owner"
    STORE_STAFF = "store_staff"


# Roles permitted to reach the platform-admin plane.
ADMIN_ROLES: frozenset[Role] = frozenset({Role.PLATFORM_ADMIN})
# Roles permitted to reach a tenant's store dashboard.
TENANT_ROLES: frozenset[Role] = frozenset({Role.STORE_OWNER, Role.STORE_STAFF})


@dataclass(frozen=True)
class AuthPrincipal:
    """The authenticated person behind a request (resolved from an access token)."""

    user_id: str
    email: str
    role: Role
    tenant_id: str | None  # None for platform admins
    token_id: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role in ADMIN_ROLES

    def can_access_tenant(self, tenant_id: str) -> bool:
        """Platform admins see every tenant; tenant users see only their own."""
        if self.is_admin:
            return True
        return self.tenant_id is not None and self.tenant_id == tenant_id
