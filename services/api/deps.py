"""Request dependencies — tenant resolution from the scoped API key (Phase 1).

Resolves `tenant_id` (and scope) from the `x-api-key` header against the
control-plane `api_keys` table so every request is tenant-scoped — the data
half of the isolation invariant (REQ-M11-001/002). Full least-privilege RBAC
enforcement is Phase 3 (M11); Phase 1 needs reliable tenant resolution.
"""

from __future__ import annotations

import hashlib

from acip_core.clients import get_pg_pool
from acip_core.security import API_KEY_HEADER, ApiKeyPrincipal, KeyScope


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def resolve_principal(api_key: str | None) -> ApiKeyPrincipal:
    """Look up the key; return an unverified principal if missing/unknown."""
    if not api_key:
        return ApiKeyPrincipal(tenant_id=None, scope=None, raw_key=None, verified=False)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tenant_id, scope FROM api_keys WHERE key_hash = $1 AND revoked = FALSE",
            hash_key(api_key),
        )
    if row is None:
        return ApiKeyPrincipal(tenant_id=None, scope=None, raw_key=api_key, verified=False)
    return ApiKeyPrincipal(
        tenant_id=str(row["tenant_id"]),
        scope=KeyScope(row["scope"]),
        raw_key=api_key,
        verified=True,
    )


# Re-exported for routers.
__all__ = ["resolve_principal", "hash_key", "API_KEY_HEADER", "KeyScope"]
