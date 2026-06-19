"""PostgreSQL connection pool + readiness probe (REQ-M1-004).

Control-plane only (tenants, api_keys, plans, usage). No shopper-facing data
ever lives here (blueprint §3.4).
"""

from __future__ import annotations

import asyncpg

from ..config import get_settings

_pool: asyncpg.Pool | None = None


async def get_pg_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = await asyncpg.create_pool(dsn=s.pg_dsn, min_size=1, max_size=10)
    return _pool


async def pg_ready() -> bool:
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            return (await conn.fetchval("SELECT 1")) == 1
    except Exception:  # noqa: BLE001
        return False
