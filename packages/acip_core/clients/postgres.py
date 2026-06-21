"""PostgreSQL connection pool + readiness probe (REQ-M1-004).

Control-plane only (tenants, api_keys, plans, usage). No shopper-facing data
ever lives here (blueprint §3.4).
"""

from __future__ import annotations

import json

import asyncpg

from ..config import get_settings

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Decode json/jsonb columns into Python objects (asyncpg returns raw text
    otherwise — GP-1). Applies to settings, audit detail, plan features, etc."""
    for typename in ("json", "jsonb"):
        await conn.set_type_codec(
            typename, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def get_pg_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=s.pg_dsn, min_size=1, max_size=10, init=_init_connection
        )
    return _pool


async def pg_ready() -> bool:
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            return (await conn.fetchval("SELECT 1")) == 1
    except Exception:  # noqa: BLE001
        return False
