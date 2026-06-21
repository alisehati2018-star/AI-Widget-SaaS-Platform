"""Subscription + order lifecycle (Phase 7 billing).

Provider-agnostic: an order is created server-side with the plan's authoritative
price, then marked paid either by a manual operator confirmation or a verified
provider webhook. Marking paid activates the subscription and grants the plan's
monthly credits. All amounts come from the `plans` table — never from the client.
"""

from __future__ import annotations

from typing import Any

from acip_core.logging import get_logger

log = get_logger("billing.subscription")


async def _plan_row(conn, plan_code: str) -> Any:
    return await conn.fetchrow(
        "SELECT id, code, name, price_monthly, currency, credits_per_month "
        "FROM plans WHERE code = $1",
        plan_code,
    )


async def create_order(
    pool, tenant_id: str, plan_code: str, *, provider: str = "manual"
) -> dict[str, Any] | None:
    """Create a pending order priced from the plan. Returns the order, or None
    if the plan is unknown."""
    if pool is None:
        return None
    async with pool.acquire() as conn:
        plan = await _plan_row(conn, plan_code)
        if plan is None:
            return None
        order_id = await conn.fetchval(
            "INSERT INTO orders (tenant_id, plan_id, amount, currency, provider, status) "
            "VALUES ($1, $2, $3, $4, $5, 'pending') RETURNING id",
            tenant_id, plan["id"], plan["price_monthly"], plan["currency"], provider,
        )
    return {
        "order_id": str(order_id),
        "plan_code": plan["code"],
        "plan_name": plan["name"],
        "amount": float(plan["price_monthly"]),
        "currency": plan["currency"],
        "provider": provider,
        "status": "pending",
    }


async def activate_plan(pool, tenant_id: str, plan_code: str, *, period_days: int = 30) -> bool:
    """Point the tenant at the plan, mark the subscription active, and grant the
    plan's monthly credits. Idempotent per call (safe to re-run)."""
    if pool is None:
        return False
    async with pool.acquire() as conn:
        plan = await _plan_row(conn, plan_code)
        if plan is None:
            return False
        async with conn.transaction():
            await conn.execute(
                "UPDATE tenants SET plan_id = $1, updated_at = now() WHERE id = $2",
                plan["id"], tenant_id,
            )
            await conn.execute(
                "INSERT INTO subscriptions (tenant_id, plan_id, status, current_period_end) "
                "VALUES ($1, $2, 'active', now() + ($3 || ' days')::interval) "
                "ON CONFLICT (tenant_id) DO UPDATE SET plan_id = EXCLUDED.plan_id, "
                "status = 'active', current_period_end = EXCLUDED.current_period_end, "
                "updated_at = now()",
                tenant_id, plan["id"], str(period_days),
            )
            credits = float(plan["credits_per_month"] or 0)
            if credits > 0:
                await conn.execute(
                    "INSERT INTO credit_ledger (tenant_id, delta, rung, reason) "
                    "VALUES ($1, $2, 'grant', 'plan_grant')",
                    tenant_id, credits,
                )
    return True


async def mark_order_paid(
    pool, order_id: str, *, period_days: int = 30
) -> dict[str, Any] | None:
    """Mark a pending order paid and activate its plan. Idempotent: a paid order
    is not granted twice. Returns a summary, or None if the order is unknown."""
    if pool is None:
        return None
    async with pool.acquire() as conn:
        order = await conn.fetchrow(
            "SELECT o.id, o.tenant_id, o.status, p.code AS plan_code "
            "FROM orders o JOIN plans p ON p.id = o.plan_id WHERE o.id = $1",
            order_id,
        )
        if order is None:
            return None
        if order["status"] == "paid":
            return {"order_id": order_id, "tenant_id": str(order["tenant_id"]),
                    "plan_code": order["plan_code"], "status": "paid", "already": True}
        await conn.execute(
            "UPDATE orders SET status = 'paid', paid_at = now() WHERE id = $1", order_id
        )
    await activate_plan(pool, str(order["tenant_id"]), order["plan_code"], period_days=period_days)
    return {"order_id": order_id, "tenant_id": str(order["tenant_id"]),
            "plan_code": order["plan_code"], "status": "paid", "already": False}
