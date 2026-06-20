"""Per-tenant rate limiting (M11: REQ-M11-003).

A fixed-window counter in Redis, keyed per tenant per minute, enforced at the
edge to protect the cluster and cap spend (blueprint §9.2). Fails open (allows)
if Redis is unavailable so a cache outage never takes down the request path —
the budget hard-cap (M6) remains the spend backstop.
"""

from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, redis, default_per_min: int = 120) -> None:
        self._redis = redis
        self._default = default_per_min

    async def allow(self, tenant_id: str, *, limit: int | None = None) -> bool:
        if self._redis is None:
            return True
        limit = limit or self._default
        window = int(time.time() // 60)
        key = f"ratelimit:{tenant_id}:{window}"
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, 60)
            return count <= limit
        except Exception:  # noqa: BLE001 - fail open; budget cap is the backstop
            return True
