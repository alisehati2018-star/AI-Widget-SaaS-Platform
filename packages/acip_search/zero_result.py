"""Zero-result logging (M5: REQ-M5-008).

Every empty search is the platform's richest signal — a quality bug, a synonym
opportunity, and a merchandising insight at once. We record them to a per-tenant
Redis list (cheap, bounded); the dashboard (M9) and the relevance loop consume
them later. This is the capture half of the §6.8 loop.
"""

from __future__ import annotations

from acip_core.logging import get_logger

log = get_logger("zero_result")

_MAX_PER_TENANT = 1000


async def log_zero_result(redis, tenant_id: str, query: str) -> None:
    """Best-effort capture; never raises into the request path."""
    log.info("search.zero_result", tenant_id=tenant_id, query=query)
    if redis is None:
        return
    key = f"zero_result:{tenant_id}"
    try:
        await redis.lpush(key, query)
        await redis.ltrim(key, 0, _MAX_PER_TENANT - 1)
    except Exception:  # noqa: BLE001 - capture is best-effort
        pass
