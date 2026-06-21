"""Subscription + order lifecycle (Phase 7/E billing, manual model).

Provider-agnostic: orders are priced server-side (never trust the client), then
marked paid by a verified webhook or operator confirmation. Marking paid grants
credits, (re)activates the subscription, and issues an invoice. Also handles
credit top-ups, plan-change proration, cancel/resume, period-end renewals, and
dunning of past-due subscriptions.
"""

from __future__ import annotations

from typing import Any

from acip_core.config import get_settings
from acip_core.logging import get_logger

log = get_logger("billing.subscription")


async def _plan_row(conn, plan_code: str) -> Any:
    return await conn.fetchrow(
        "SELECT id, code, name, price_monthly, currency, credits_per_month "
        "FROM plans WHERE code = $1",
        plan_code,
    )


async def _active_sub(conn, tenant_id: str) -> Any:
    """Current subscription joined to its plan (price + period end)."""
    return await conn.fetchrow(
        "SELECT s.status, s.current_period_end, s.cancel_at_period_end, "
        "p.code AS plan_code, p.name AS plan_name, p.price_monthly "
        "FROM subscriptions s LEFT JOIN plans p ON p.id = s.plan_id "
        "WHERE s.tenant_id = $1",
        tenant_id,
    )


def _proration_credit(old_price: float, period_end, period_days: int) -> float:
    """Unused-time credit from the current plan when changing mid-period."""
    if old_price <= 0 or period_end is None:
        return 0.0
    from datetime import UTC, datetime

    remaining = (period_end - datetime.now(UTC)).total_seconds() / 86400.0
    remaining = max(0.0, min(float(period_days), remaining))
    return round(old_price * remaining / period_days, 2)


async def proration_preview(
    pool, tenant_id: str, plan_code: str, *, period_days: int = 30
) -> dict[str, Any] | None:
    if pool is None:
        return None
    async with pool.acquire() as conn:
        plan = await _plan_row(conn, plan_code)
        if plan is None:
            return None
        sub = await _active_sub(conn, tenant_id)
    base = float(plan["price_monthly"])
    credit = 0.0
    if sub is not None and sub["status"] == "active":
        credit = _proration_credit(
            float(sub["price_monthly"] or 0), sub["current_period_end"], period_days
        )
    amount_due = max(0.0, round(base - credit, 2))
    return {
        "plan_code": plan["code"],
        "plan_name": plan["name"],
        "base_price": base,
        "proration_credit": credit,
        "amount_due": amount_due,
        "currency": plan["currency"],
    }


async def create_order(
    pool,
    tenant_id: str,
    plan_code: str,
    *,
    provider: str = "manual",
    apply_proration: bool = True,
    period_days: int = 30,
) -> dict[str, Any] | None:
    """Create a pending subscription order, prorated against any active plan."""
    if pool is None:
        return None
    async with pool.acquire() as conn:
        plan = await _plan_row(conn, plan_code)
        if plan is None:
            return None
        amount = float(plan["price_monthly"])
        credit = 0.0
        if apply_proration:
            sub = await _active_sub(conn, tenant_id)
            if sub is not None and sub["status"] == "active":
                credit = _proration_credit(
                    float(sub["price_monthly"] or 0), sub["current_period_end"], period_days
                )
                amount = max(0.0, round(amount - credit, 2))
        order_id = await conn.fetchval(
            "INSERT INTO orders (tenant_id, plan_id, amount, currency, provider, status, kind) "
            "VALUES ($1, $2, $3, $4, $5, 'pending', 'subscription') RETURNING id",
            tenant_id,
            plan["id"],
            amount,
            plan["currency"],
            provider,
        )
    return {
        "order_id": str(order_id),
        "kind": "subscription",
        "plan_code": plan["code"],
        "plan_name": plan["name"],
        "amount": amount,
        "proration_credit": credit,
        "currency": plan["currency"],
        "provider": provider,
        "status": "pending",
    }


async def create_topup_order(
    pool, tenant_id: str, credits: float, *, provider: str = "manual"
) -> dict[str, Any] | None:
    """Create a pending credit top-up order priced by the configured rate."""
    if pool is None or credits <= 0:
        return None
    s = get_settings()
    amount = round(credits / max(1, s.topup_credits_per_unit), 2)
    async with pool.acquire() as conn:
        order_id = await conn.fetchval(
            "INSERT INTO orders (tenant_id, plan_id, amount, currency, provider, status, "
            "kind, credits) VALUES ($1, NULL, $2, $3, $4, 'pending', 'topup', $5) RETURNING id",
            tenant_id,
            amount,
            s.billing_currency,
            provider,
            credits,
        )
    return {
        "order_id": str(order_id),
        "kind": "topup",
        "credits": credits,
        "amount": amount,
        "currency": s.billing_currency,
        "provider": provider,
        "status": "pending",
    }


async def activate_plan(pool, tenant_id: str, plan_code: str, *, period_days: int = 30) -> bool:
    """Point the tenant at the plan, mark the subscription active, grant credits."""
    if pool is None:
        return False
    async with pool.acquire() as conn:
        plan = await _plan_row(conn, plan_code)
        if plan is None:
            return False
        async with conn.transaction():
            await conn.execute(
                "UPDATE tenants SET plan_id = $1, updated_at = now() WHERE id = $2",
                plan["id"],
                tenant_id,
            )
            await conn.execute(
                "INSERT INTO subscriptions (tenant_id, plan_id, status, current_period_end, "
                "cancel_at_period_end) VALUES ($1, $2, 'active', "
                "now() + ($3 || ' days')::interval, FALSE) "
                "ON CONFLICT (tenant_id) DO UPDATE SET plan_id = EXCLUDED.plan_id, "
                "status = 'active', current_period_end = EXCLUDED.current_period_end, "
                "cancel_at_period_end = FALSE, updated_at = now()",
                tenant_id,
                plan["id"],
                str(period_days),
            )
            credits = float(plan["credits_per_month"] or 0)
            if credits > 0:
                await conn.execute(
                    "INSERT INTO credit_ledger (tenant_id, delta, rung, reason) "
                    "VALUES ($1, $2, 'grant', 'plan_grant')",
                    tenant_id,
                    credits,
                )
    return True


async def _create_invoice(conn, tenant_id, order_id, description, amount, currency) -> int:
    return await conn.fetchval(
        "INSERT INTO invoices (tenant_id, order_id, description, amount, currency) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING number",
        tenant_id,
        order_id,
        description,
        amount,
        currency,
    )


async def mark_order_paid(pool, order_id: str, *, period_days: int = 30) -> dict[str, Any] | None:
    """Mark an order paid → grant/activate + issue an invoice. Idempotent."""
    if pool is None:
        return None
    async with pool.acquire() as conn:
        order = await conn.fetchrow(
            "SELECT o.id, o.tenant_id, o.status, o.kind, o.credits, o.amount, o.currency, "
            "p.code AS plan_code, p.name AS plan_name FROM orders o "
            "LEFT JOIN plans p ON p.id = o.plan_id WHERE o.id = $1",
            order_id,
        )
        if order is None:
            return None
        tenant_id = str(order["tenant_id"])
        if order["status"] == "paid":
            return {
                "order_id": order_id,
                "tenant_id": tenant_id,
                "kind": order["kind"],
                "plan_code": order["plan_code"],
                "status": "paid",
                "already": True,
            }
        await conn.execute(
            "UPDATE orders SET status = 'paid', paid_at = now() WHERE id = $1", order_id
        )

    invoice_no: int | None = None
    if order["kind"] == "topup":
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO credit_ledger (tenant_id, delta, rung, reason) "
                    "VALUES ($1, $2, 'grant', 'topup')",
                    tenant_id,
                    float(order["credits"]),
                )
                invoice_no = await _create_invoice(
                    conn,
                    tenant_id,
                    order_id,
                    f"Credit top-up: {int(order['credits'])} credits",
                    float(order["amount"]),
                    order["currency"],
                )
    else:
        await activate_plan(pool, tenant_id, order["plan_code"], period_days=period_days)
        async with pool.acquire() as conn:
            invoice_no = await _create_invoice(
                conn,
                tenant_id,
                order_id,
                f"{order['plan_name']} plan — {period_days} days",
                float(order["amount"]),
                order["currency"],
            )
    return {
        "order_id": order_id,
        "tenant_id": tenant_id,
        "kind": order["kind"],
        "plan_code": order["plan_code"],
        "plan_name": order["plan_name"],
        "amount": float(order["amount"]),
        "currency": order["currency"],
        "invoice_number": invoice_no,
        "status": "paid",
        "already": False,
    }


async def set_cancel(pool, tenant_id: str, cancel: bool) -> bool:
    """Schedule cancellation at period end (or undo it)."""
    if pool is None:
        return False
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE subscriptions SET cancel_at_period_end = $1, updated_at = now() "
            "WHERE tenant_id = $2 RETURNING tenant_id",
            cancel,
            tenant_id,
        )
    return updated is not None


async def process_renewals(pool, *, trial_plan_code: str = "free") -> dict[str, int]:
    """Period-end processing: subscriptions marked cancel→downgrade to the free
    plan; others past their period→`past_due` (manual model needs a new payment)."""
    if pool is None:
        return {"downgraded": 0, "past_due": 0}
    async with pool.acquire() as conn:
        to_cancel = await conn.fetch(
            "SELECT tenant_id FROM subscriptions WHERE status = 'active' "
            "AND current_period_end IS NOT NULL AND current_period_end <= now() "
            "AND cancel_at_period_end = TRUE"
        )
        past = await conn.fetch(
            "UPDATE subscriptions SET status = 'past_due', updated_at = now() "
            "WHERE status = 'active' AND current_period_end IS NOT NULL "
            "AND current_period_end <= now() AND cancel_at_period_end = FALSE "
            "RETURNING tenant_id"
        )
    for row in to_cancel:
        await activate_plan(pool, str(row["tenant_id"]), trial_plan_code)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE subscriptions SET cancel_at_period_end = FALSE WHERE tenant_id = $1",
                row["tenant_id"],
            )
    return {"downgraded": len(to_cancel), "past_due": len(past)}


async def list_past_due(pool) -> list[dict[str, Any]]:
    """Past-due subscriptions with owner email + plan (for dunning)."""
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT s.tenant_id, p.name AS plan, p.price_monthly, p.currency, "
            "u.email FROM subscriptions s "
            "LEFT JOIN plans p ON p.id = s.plan_id "
            "LEFT JOIN users u ON u.tenant_id = s.tenant_id AND u.role = 'store_owner' "
            "WHERE s.status = 'past_due'"
        )
    return [
        {
            "tenant_id": str(r["tenant_id"]),
            "email": r["email"],
            "plan": r["plan"],
            "amount": float(r["price_monthly"] or 0),
            "currency": r["currency"],
        }
        for r in rows
    ]
