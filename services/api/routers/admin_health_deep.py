"""Admin surface — deep system health: one endpoint that probes EVERY
subsystem (core stores, queue, AI routing registry, migrations, and the
config-dependent integrations) so operators — and the ops CLI
``scripts/system_health.py`` — get a single complete picture.

`/admin/health` (admin_monitoring.py) stays the cheap dependency probe that
feeds the sparkline; this endpoint is the full diagnosis.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.config import get_settings
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "db" / "migrations"


async def _probe(name: str, fn) -> dict[str, Any]:
    """Run one async probe → {name, status, latency_ms, detail}. Never raises."""
    t0 = time.monotonic()
    try:
        detail = await fn()
        return {
            "component": name,
            "status": "ok",
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "detail": detail or {},
        }
    except Exception as exc:  # noqa: BLE001 - a health probe must never crash
        return {
            "component": name,
            "status": "error",
            "latency_ms": None,
            "detail": {"error": str(exc)[:200]},
        }


async def _check_postgres() -> dict[str, Any]:
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
        applied = await conn.fetchval(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        )
    on_disk = sorted(p.stem for p in _MIGRATIONS_DIR.glob("*.sql"))
    latest = on_disk[-1] if on_disk else None
    if latest and applied != latest:
        raise RuntimeError(f"migrations behind: applied={applied} latest={latest}")
    return {"migrations": applied}


async def _check_redis() -> dict[str, Any]:
    redis = get_redis()
    if redis is None or not await redis.ping():
        raise RuntimeError("redis not reachable")
    return {}


async def _check_elasticsearch() -> dict[str, Any]:
    if not await get_es_client().ping():
        raise RuntimeError("elasticsearch not reachable")
    return {}


async def _check_queue() -> dict[str, Any]:
    from .admin_ops_status import _inspect_workers

    workers = await asyncio.wait_for(asyncio.to_thread(_inspect_workers), timeout=10)
    if not workers:
        raise RuntimeError("no celery worker answered the control ping")
    return {"workers": len(workers)}


async def _check_ai_registry() -> dict[str, Any]:
    from api.runtime import get_provider_registry

    snap = await get_provider_registry().snapshot()
    chat = len(snap.endpoints_by_task.get("chat", []))
    if chat == 0:
        raise RuntimeError("no chat endpoint bound (env fallback missing too)")
    return {
        "chat_chain": chat,
        "embedding_chain": len(snap.embedding_endpoints),
        "rerank_chain": len(snap.rerank_endpoints),
        "failover_enabled": snap.failover_enabled,
    }


def _config_report() -> list[dict[str, Any]]:
    """Config-dependent integrations: not probed over the network — reported
    as configured/not_configured so a bare deployment reads as informative,
    not broken."""
    s = get_settings()
    return [
        {
            "component": "billing_psp",
            "status": "configured" if s.zarinpal_merchant_id else "not_configured",
            "detail": {"provider": "zarinpal" if s.zarinpal_merchant_id else None},
        },
        {
            "component": "email",
            "status": "configured" if s.email_provider != "console" else "not_configured",
            "detail": {"provider": s.email_provider},
        },
    ]


@router.get("/health/deep")
async def deep_health(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Full-system health: every runtime subsystem probed concurrently, plus
    the configuration state of optional integrations. `status` is `ok` only
    when every probed component is ok (config-only items don't degrade it)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()

    components = list(
        await asyncio.gather(
            _probe("postgres", _check_postgres),
            _probe("redis", _check_redis),
            _probe("elasticsearch", _check_elasticsearch),
            _probe("queue", _check_queue),
            _probe("ai_registry", _check_ai_registry),
        )
    )
    probed_ok = all(c["status"] == "ok" for c in components)
    components.extend(_config_report())
    return {
        "status": "ok" if probed_ok else "degraded",
        "checked_at": int(time.time()),
        "components": components,
    }
