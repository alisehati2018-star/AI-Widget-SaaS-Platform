"""Security primitives (Phase 0 scaffolding only).

Establishes the *shape* of scoped, least-privilege API keys (blueprint §9.2)
so later phases can enforce them. Phase 0 only extracts and structures the key;
full validation, tenant binding, and the isolation invariant are Phase 1/3
(REQ-M11-001/002/005) and are intentionally NOT implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

API_KEY_HEADER = "x-api-key"


class KeyScope(StrEnum):
    """Least-privilege roles a key may carry (§9.2)."""

    WIDGET = "widget"      # shopper-facing: search + chat only
    ADMIN = "admin"        # operator console
    SYNC = "sync"          # store connectors / ingest


@dataclass(frozen=True)
class ApiKeyPrincipal:
    """Resolved identity for a request. Phase 0 returns an unverified stub."""

    tenant_id: str | None
    scope: KeyScope | None
    raw_key: str | None
    verified: bool = False


def extract_principal(api_key: str | None) -> ApiKeyPrincipal:
    """Extract (but do NOT verify) the principal from a raw key header.

    Verification against PostgreSQL `api_keys` and tenant binding land in
    Phase 1/3. This keeps the dependency surface stable for routers now.
    """
    if not api_key:
        return ApiKeyPrincipal(tenant_id=None, scope=None, raw_key=None, verified=False)
    return ApiKeyPrincipal(tenant_id=None, scope=None, raw_key=api_key, verified=False)
