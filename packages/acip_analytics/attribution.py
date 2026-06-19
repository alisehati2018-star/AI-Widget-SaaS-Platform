"""AI attribution & the four-dimension summary (M10: REQ-M10-005, M9-005).

Attributes activity to the assistant from the metering stream (`usage_events`)
and the leads table, and assembles the relevance/latency/cost/reliability view
(blueprint §18 "one dashboard, four dimensions"). Tenant-scoped; read-only.
"""

from __future__ import annotations

from typing import Any

from acip_core.logging import get_logger

log = get_logger("analytics.attribution")


async def attribution_summary(pg_pool, tenant_id: str) -> dict[str, Any]:
    """Assistant cost/usage attribution from the metering stream."""
    if pg_pool is None:
        return {"turns": 0, "leads": 0, "total_cost": 0.0, "paid_share": 0.0}
    try:
        async with pg_pool.acquire() as conn:
            turns = await conn.fetchval(
                "SELECT count(*) FROM usage_events WHERE tenant_id = $1 AND route = 'chat'",
                tenant_id,
            )
            paid = await conn.fetchval(
                "SELECT count(*) FROM usage_events "
                "WHERE tenant_id = $1 AND route = 'chat' AND rung = 'frontier'",
                tenant_id,
            )
            total_cost = await conn.fetchval(
                "SELECT coalesce(sum(cost), 0) FROM usage_events WHERE tenant_id = $1",
                tenant_id,
            )
            leads = await conn.fetchval(
                "SELECT count(*) FROM leads WHERE tenant_id = $1", tenant_id
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("attribution.failed", error=str(exc))
        return {"turns": 0, "leads": 0, "total_cost": 0.0, "paid_share": 0.0}
    turns = int(turns or 0)
    paid = int(paid or 0)
    return {
        "turns": turns,
        "leads": int(leads or 0),
        "total_cost": float(total_cost or 0.0),
        "paid_share": (paid / turns) if turns else 0.0,
        "no_paid_share": (1 - paid / turns) if turns else 1.0,
    }


async def four_dimension_summary(pg_pool, redis, tenant_id: str) -> dict[str, Any]:
    """Relevance · latency · cost · reliability, side by side (REQ-M9-005)."""
    attrib = await attribution_summary(pg_pool, tenant_id)
    latency_p95 = None
    if pg_pool is not None:
        try:
            async with pg_pool.acquire() as conn:
                latency_p95 = await conn.fetchval(
                    "SELECT percentile_disc(0.95) WITHIN GROUP (ORDER BY latency_ms) "
                    "FROM usage_events WHERE tenant_id = $1 AND latency_ms IS NOT NULL",
                    tenant_id,
                )
        except Exception:  # noqa: BLE001
            latency_p95 = None
    return {
        "cost": {"total": attrib["total_cost"], "no_paid_share": attrib["no_paid_share"]},
        "latency": {"p95_ms": int(latency_p95) if latency_p95 is not None else None},
        "relevance": {"note": "NDCG@10 from the golden-set eval (deferred validation)"},
        "reliability": {"turns": attrib["turns"]},
    }
