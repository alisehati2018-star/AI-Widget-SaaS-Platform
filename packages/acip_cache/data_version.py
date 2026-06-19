"""Per-tenant data version (M6: REQ-M6-005 cache hygiene).

Cache keys embed the tenant's data version. A sync event that changes truth
(price/stock/catalogue) bumps the version, which atomically invalidates every
cached answer for that tenant without scanning keys.
"""

from __future__ import annotations


def _key(tenant_id: str) -> str:
    return f"data_version:{tenant_id}"


async def current_data_version(redis, tenant_id: str) -> int:
    if redis is None:
        return 0
    try:
        val = await redis.get(_key(tenant_id))
        return int(val) if val is not None else 0
    except Exception:  # noqa: BLE001
        return 0


async def bump_data_version(redis, tenant_id: str) -> int:
    """Invalidate the tenant's caches by advancing its data version."""
    if redis is None:
        return 0
    try:
        return int(await redis.incr(_key(tenant_id)))
    except Exception:  # noqa: BLE001
        return 0
