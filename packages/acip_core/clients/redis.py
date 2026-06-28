"""Redis client factory + readiness probe (REQ-M1-005).

Backs caches, rate limits, sessions, and the Celery broker in later phases.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from ..config import get_settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        # protocol=2 keeps compatibility with older local Redis (e.g. Windows 5.x).
        _redis = aioredis.from_url(
            get_settings().redis_url, decode_responses=True, protocol=2
        )
    return _redis


async def redis_ready() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:  # noqa: BLE001
        return False
