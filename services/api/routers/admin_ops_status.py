"""Admin surface — Celery queue depth, the legacy env-based inference status
view, and feature flags.

Live dependency health and usage/credit consumption live in
``admin_monitoring.py``.
"""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])


def _inspect_workers() -> list[dict[str, Any]]:
    """Blocking Celery inspect (run in a thread): live workers, their active
    task counts and registered task names. Empty list = no worker replied.
    Each inspect call waits its full timeout (it cannot know how many workers
    exist), so keep it short — three calls run back to back."""
    from worker.celery_app import celery_app

    insp = celery_app.control.inspect(timeout=1.0)
    ping = insp.ping() or {}
    active = insp.active() or {}
    registered = insp.registered() or {}
    workers: list[dict[str, Any]] = []
    for name in sorted(ping):
        tasks = active.get(name) or []
        workers.append({
            "name": name,
            "status": "online",
            "active_tasks": [
                {"name": t.get("name"), "id": t.get("id")} for t in tasks[:10]
            ],
            "active_count": len(tasks),
            "registered": sorted(registered.get(name) or [])[:20],
        })
    return workers


@router.get("/queue")
async def queue_monitoring(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Celery broker reachability, pending depth, and live worker heartbeat
    (workers answering a control ping, with their active tasks)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import asyncio

    s = get_settings()
    # The queue lives in the BROKER's Redis database (often a different db
    # index than the app cache), so probe that URL, not get_redis().
    import redis.asyncio as aioredis

    depth: int | None = None
    reachable = False
    try:
        broker = aioredis.from_url(s.celery_broker_url)
        try:
            if await broker.ping():
                reachable = True
                depth = int(await broker.llen("celery"))
        finally:
            await broker.aclose()
    except Exception:  # noqa: BLE001
        reachable = False
    workers: list[dict[str, Any]] = []
    if reachable:
        try:
            workers = await asyncio.wait_for(asyncio.to_thread(_inspect_workers), timeout=10)
        except Exception:  # noqa: BLE001 - inspect is best-effort
            workers = []
    return {
        "broker": s.celery_broker_url,
        "reachable": reachable,
        "pending": depth,
        "workers": workers,
    }


@router.get("/models")
async def model_monitoring(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Gateway / inference configuration + per-rung call distribution."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        by_rung = await conn.fetch(
            "SELECT COALESCE(rung, 'unknown') AS rung, count(*) AS n FROM usage_events "
            "GROUP BY rung ORDER BY n DESC"
        )
    return {
        "embeddings_url": s.embeddings_url,
        "reranker_url": s.reranker_url,
        "llm_url": s.llm_url,
        "llm_model": s.llm_model,
        "frontier_enabled": s.frontier_enabled,
        "frontier_model": s.frontier_model or None,
        "rerank_enabled": s.rerank_enabled,
        "by_rung": [{"rung": r["rung"], "count": int(r["n"])} for r in by_rung],
    }


@router.post("/models/ping")
async def model_ping(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Probe the configured inference services (embeddings / reranker / LLM)
    and report reachability + latency, so the operator can see at a glance
    which local models are actually up."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import time

    import httpx

    s = get_settings()
    targets = {
        "embeddings": s.embeddings_url,
        "reranker": s.reranker_url,
        "llm": s.llm_url,
    }
    results: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(timeout=3, follow_redirects=True) as client:
        for name, url in targets.items():
            if not url:
                results[name] = {"configured": False, "reachable": False, "latency_ms": None}
                continue
            t0 = time.monotonic()
            try:
                # Any HTTP answer (even 404) proves the service is listening.
                await client.get(url)
                results[name] = {
                    "configured": True,
                    "reachable": True,
                    "latency_ms": int((time.monotonic() - t0) * 1000),
                }
            except Exception:  # noqa: BLE001
                results[name] = {"configured": True, "reachable": False, "latency_ms": None}
    return {"services": results}


@router.get("/feature-flags")
async def get_feature_flags(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT key, enabled, description, updated_at, updated_by "
            "FROM feature_flags ORDER BY key"
        )
    return {
        "flags": [
            {
                "key": r["key"],
                "enabled": r["enabled"],
                "description": r["description"],
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
                "updated_by": r["updated_by"],
            }
            for r in rows
        ]
    }


@router.post("/feature-flags/{key}")
async def set_feature_flag(
    key: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    enabled = bool(payload.get("enabled", False))
    from .admin_auth_common import admin_current_principal

    principal = await admin_current_principal(authorization, vitrin_access)
    actor = principal.email if principal else "operator"
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE feature_flags SET enabled = $1, updated_at = now(), updated_by = $2 "
            "WHERE key = $3 RETURNING key",
            enabled,
            actor,
            key,
        )
    if updated is None:
        return error_response(404, "not_found", "No such flag.")
    await audit(pool, actor=actor, action="flag.set", detail={"key": key, "enabled": enabled})
    return {"key": key, "enabled": enabled}
