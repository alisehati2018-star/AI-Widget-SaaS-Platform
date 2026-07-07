"""Admin surface — operational monitoring: live dependency health and usage/
credit consumption (+ CSV export).

Celery queue depth, the legacy env-based inference status view, and feature
flags live in ``admin_ops_status.py``.

(Multi-provider AI configuration — providers/models/routing/pricing/profit —
lives in `admin_ai_providers.py`/`admin_ai_routing.py`/`admin_ai_finance.py`;
this module's sibling `/models` endpoint is the older, purely-env-configured
snapshot kept for the local-infra status table.)
"""

from __future__ import annotations

from typing import Any

from acip_core.clients import get_es_client as _get_es_client
from acip_core.clients import get_pg_pool, get_redis
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden, _iso

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def system_health(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Live dependency status (PG / Redis / Elasticsearch) with per-probe
    latency, plus a rolling history (kept in Redis) for the health sparkline."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import json
    import time

    deps: dict[str, str] = {}
    latency: dict[str, int | None] = {}

    t0 = time.monotonic()
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        deps["postgres"] = "ok"
        latency["postgres"] = int((time.monotonic() - t0) * 1000)
    except Exception:  # noqa: BLE001
        deps["postgres"] = "unavailable"
        latency["postgres"] = None
    redis = get_redis()
    t0 = time.monotonic()
    try:
        deps["redis"] = "ok" if (redis is not None and await redis.ping()) else "unavailable"
        latency["redis"] = (
            int((time.monotonic() - t0) * 1000) if deps["redis"] == "ok" else None
        )
    except Exception:  # noqa: BLE001
        deps["redis"] = "unavailable"
        latency["redis"] = None
    t0 = time.monotonic()
    try:
        deps["elasticsearch"] = "ok" if await _get_es_client().ping() else "unavailable"
        latency["elasticsearch"] = (
            int((time.monotonic() - t0) * 1000) if deps["elasticsearch"] == "ok" else None
        )
    except Exception:  # noqa: BLE001
        deps["elasticsearch"] = "unavailable"
        latency["elasticsearch"] = None

    overall = "ok" if all(v == "ok" for v in deps.values()) else "degraded"

    # Rolling sample history for the sparkline (best-effort; capped at 96).
    history: list[dict[str, Any]] = []
    if redis is not None and deps["redis"] == "ok":
        try:
            sample = {
                "ts": int(time.time()),
                "ok": sum(1 for v in deps.values() if v == "ok"),
                "total": len(deps),
                "pg_ms": latency["postgres"],
            }
            key = "admin:health:history"
            await redis.lpush(key, json.dumps(sample))
            await redis.ltrim(key, 0, 95)
            raw = await redis.lrange(key, 0, 95)
            history = [json.loads(x) for x in reversed(raw)]
        except Exception:  # noqa: BLE001
            history = []
    return {"status": overall, "dependencies": deps, "latency_ms": latency, "history": history}


def _usage_filters(
    tenant: str | None, route: str | None, rung: str | None, days: int
) -> tuple[str, list[Any]]:
    """WHERE clause + params shared by the usage summary, event list and CSV
    export, so all three views always describe the same slice."""
    where: list[str] = []
    params: list[Any] = []
    if tenant:
        params.append(f"%{tenant.strip()}%")
        where.append(
            f"u.tenant_id IN (SELECT id FROM tenants "
            f"WHERE slug ILIKE ${len(params)} OR name ILIKE ${len(params)})"
        )
    if route:
        params.append(f"%{route.strip()}%")
        where.append(f"u.route ILIKE ${len(params)}")
    if rung:
        params.append(rung.strip())
        where.append(f"COALESCE(u.rung, 'unknown') = ${len(params)}")
    if days:
        params.append(days)
        where.append(f"u.occurred_at >= now() - make_interval(days => ${len(params)})")
    return ("WHERE " + " AND ".join(where)) if where else "", params


_USAGE_SELECT = (
    "SELECT u.occurred_at, t.slug AS tenant_slug, u.route, "
    "COALESCE(u.rung, 'unknown') AS rung, u.tokens_in, u.tokens_out, "
    "u.cache_outcome, u.latency_ms, u.cost "
    "FROM usage_events u JOIN tenants t ON t.id = u.tenant_id"
)


@router.get("/usage")
async def usage_monitoring(
    tenant: str | None = None,
    route: str | None = None,
    rung: str | None = None,
    days: int = 30,
    fmt: str | None = None,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Platform-wide usage + credit consumption with tenant/route/rung/date
    filters. `fmt=csv` streams the filtered events as a CSV download."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    days = max(1, min(int(days), 366))
    clause, params = _usage_filters(tenant, route, rung, days)
    pool = await get_pg_pool()

    if fmt == "csv":
        import csv
        import io

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"{_USAGE_SELECT} {clause} ORDER BY u.occurred_at DESC LIMIT 10000", *params
            )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "occurred_at", "tenant", "route", "rung",
            "tokens_in", "tokens_out", "cache_outcome", "latency_ms", "cost",
        ])
        for r in rows:
            writer.writerow([
                _iso(r["occurred_at"]), r["tenant_slug"], r["route"], r["rung"],
                r["tokens_in"], r["tokens_out"], r["cache_outcome"],
                r["latency_ms"], float(r["cost"]),
            ])
        from fastapi.responses import Response

        return Response(
            content=buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"content-disposition": 'attachment; filename="usage-export.csv"'},
        )

    async with pool.acquire() as conn:
        totals = await conn.fetchrow(
            f"SELECT count(*) AS calls, COALESCE(sum(u.tokens_in), 0) AS tin, "
            f"COALESCE(sum(u.tokens_out), 0) AS tout, COALESCE(sum(u.cost), 0) AS cost "
            f"FROM usage_events u {clause}"
        , *params)
        by_rung = await conn.fetch(
            f"SELECT COALESCE(u.rung, 'unknown') AS rung, count(*) AS n "
            f"FROM usage_events u {clause} GROUP BY 1 ORDER BY n DESC", *params
        )
        recent = await conn.fetch(
            f"{_USAGE_SELECT} {clause} ORDER BY u.occurred_at DESC LIMIT 50", *params
        )
        spent = await conn.fetchval(
            "SELECT COALESCE(-sum(delta), 0) FROM credit_ledger WHERE delta < 0"
        )
    return {
        "calls": int(totals["calls"]),
        "tokens_in": int(totals["tin"]),
        "tokens_out": int(totals["tout"]),
        "cost": float(totals["cost"]),
        "credits_spent": float(spent or 0),
        "by_rung": [{"rung": r["rung"], "count": int(r["n"])} for r in by_rung],
        "events": [
            {
                "occurred_at": _iso(r["occurred_at"]),
                "tenant": r["tenant_slug"],
                "route": r["route"],
                "rung": r["rung"],
                "tokens_in": r["tokens_in"],
                "tokens_out": r["tokens_out"],
                "cache_outcome": r["cache_outcome"],
                "latency_ms": r["latency_ms"],
                "cost": float(r["cost"]),
            }
            for r in recent
        ],
        "days": days,
    }
