"""Usage metering (M6: REQ-M6-012).

Every search/model call emits a usage record (tenant, route, rung, tokens,
cache outcome, latency, cost) into the control-plane `usage_events` table. This
is the stream FinOps attribution, budgets, and dashboards consume (Phase 2/3).
Best-effort: a metering failure must never break the request path.
"""

from __future__ import annotations

from acip_core.logging import get_logger

log = get_logger("metering")


async def record_usage(
    pg_pool,
    tenant_id: str,
    *,
    route: str,
    rung: str = "search",
    tokens_in: int = 0,
    tokens_out: int = 0,
    cache_outcome: str = "miss",
    latency_ms: int | None = None,
    cost: float = 0.0,
    **_ignored,
) -> None:
    if pg_pool is None:
        return
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO usage_events
                    (tenant_id, route, rung, tokens_in, tokens_out,
                     cache_outcome, latency_ms, cost)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                tenant_id,
                route,
                rung,
                tokens_in,
                tokens_out,
                cache_outcome,
                latency_ms,
                cost,
            )
    except Exception as exc:  # noqa: BLE001 - metering is best-effort
        log.warning("metering.failed", error=str(exc))
