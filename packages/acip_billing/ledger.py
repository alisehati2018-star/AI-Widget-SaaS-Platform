"""Credit ledger + plan enforcement (M11: REQ-M11-009).

Append-only `credit_ledger`: each model/search call records a negative delta
sized by the rung's cost multiplier. The tenant's spend this period is the sum
of deltas; plan enforcement compares it against the plan's monthly credit cap.
Best-effort writes — billing must never break the request path; the M6 budget
hard-cap is the real-time spend backstop.
"""

from __future__ import annotations

from typing import Any

from acip_core.logging import get_logger

log = get_logger("billing.ledger")


async def record_charge(pg_pool, tenant_id: str, *, rung: str, cost: float,
                        reason: str = "turn") -> None:
    if pg_pool is None or cost <= 0:
        return
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO credit_ledger (tenant_id, delta, rung, reason) "
                "VALUES ($1, $2, $3, $4)",
                tenant_id, -abs(cost), rung, reason,
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("ledger.charge_failed", error=str(exc))


async def balance(pg_pool, tenant_id: str) -> float:
    """Net credits this tenant has consumed (negative = spent)."""
    if pg_pool is None:
        return 0.0
    try:
        async with pg_pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT coalesce(sum(delta), 0) FROM credit_ledger WHERE tenant_id = $1",
                tenant_id,
            )
        return float(val or 0.0)
    except Exception:  # noqa: BLE001
        return 0.0


async def plan_status(pg_pool, tenant_id: str) -> dict[str, Any]:
    """Compare spend against the tenant plan's monthly credit cap."""
    if pg_pool is None:
        return {"spent": 0.0, "cap": None, "within_plan": True}
    try:
        async with pg_pool.acquire() as conn:
            cap = await conn.fetchval(
                "SELECT p.monthly_credit_cap FROM tenants t "
                "JOIN plans p ON p.id = t.plan_id WHERE t.id = $1",
                tenant_id,
            )
    except Exception:  # noqa: BLE001
        cap = None
    spent = -(await balance(pg_pool, tenant_id))
    within = cap is None or spent <= float(cap)
    return {"spent": spent, "cap": float(cap) if cap is not None else None, "within_plan": within}
