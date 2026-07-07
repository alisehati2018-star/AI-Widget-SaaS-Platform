"""Admin surface — billing operations: orders, renewals, dunning, refunds,
and the platform-wide invoice ledger."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden, _iso

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/orders")
async def list_orders(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Recent billing orders + paid-revenue total (Phase 6/7)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT o.id, o.amount, o.currency, o.status, o.provider, o.created_at, "
            "COALESCE(t.name, '—') AS tenant, COALESCE(p.name, '—') AS plan FROM orders o "
            "LEFT JOIN tenants t ON t.id = o.tenant_id "
            "LEFT JOIN plans p ON p.id = o.plan_id ORDER BY o.created_at DESC LIMIT 200"
        )
        revenue = await conn.fetchval(
            "SELECT COALESCE(sum(amount), 0) FROM orders WHERE status = 'paid'"
        )
    return {
        "revenue_total": float(revenue or 0),
        "orders": [
            {
                "id": str(r["id"]),
                "tenant": r["tenant"],
                "plan": r["plan"],
                "amount": float(r["amount"]),
                "currency": r["currency"],
                "status": r["status"],
                "provider": r["provider"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
    }


@router.post("/orders/{order_id}/mark-paid")
async def admin_mark_paid(
    order_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Operator confirmation of a manual/invoice payment → activates the plan."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_billing import mark_order_paid

    from .billing_common import _email_invoice

    pool = await get_pg_pool()
    days = get_settings().subscription_period_days
    result = await mark_order_paid(pool, order_id, period_days=days)
    if result is None:
        return error_response(404, "unknown_order", "No such order.")
    if not result.get("already"):
        await _email_invoice(pool, result)
    await audit(
        pool,
        actor="operator",
        action="billing.mark_paid",
        tenant_id=result["tenant_id"],
        detail={"order_id": order_id, "kind": result["kind"]},
    )
    return {
        "status": "paid",
        "kind": result["kind"],
        "activated": result.get("plan_code"),
        "invoice_number": result.get("invoice_number"),
        "already": result.get("already"),
    }


@router.post("/billing/run-renewals")
async def run_renewals(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Period-end processing: downgrade cancelled subs, mark others past_due."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_billing import process_renewals

    pool = await get_pg_pool()
    result = await process_renewals(pool, trial_plan_code=get_settings().trial_plan_code)
    await audit(pool, actor="operator", action="billing.run_renewals", detail=result)
    return result


@router.post("/billing/run-dunning")
async def run_dunning(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Email every past-due subscription a payment reminder."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_billing import list_past_due
    from acip_notify import dunning_email, send_email

    pool = await get_pg_pool()
    due = await list_past_due(pool)
    sent = 0
    for row in due:
        if row["email"]:
            subject, text, html = dunning_email(
                row["plan"] or "your plan", row["amount"], row["currency"] or "USD"
            )
            await send_email(row["email"], subject, text, html)
            sent += 1
    await audit(
        pool,
        actor="operator",
        action="billing.run_dunning",
        detail={"past_due": len(due), "emailed": sent},
    )
    return {"past_due": len(due), "emailed": sent}


@router.post("/orders/{order_id}/refund")
async def admin_refund(
    order_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Mark an order refunded (does not auto-downgrade the live subscription)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE orders SET status = 'refunded' WHERE id = $1 RETURNING tenant_id", order_id
        )
    if row is None:
        return error_response(404, "unknown_order", "No such order.")
    await audit(
        pool,
        actor="operator",
        action="billing.refund",
        tenant_id=str(row["tenant_id"]),
        detail={"order_id": order_id},
    )
    return {"status": "refunded"}


@router.get("/invoices")
async def list_invoices(
    q: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    where: list[str] = []
    params: list[Any] = []
    if q:
        params.append(f"%{q.strip()}%")
        where.append(f"(t.slug ILIKE ${len(params)} OR t.name ILIKE ${len(params)})")
    if status in ("paid", "void"):
        params.append(status)
        where.append(f"i.status = ${len(params)}")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    base = f"FROM invoices i JOIN tenants t ON t.id = i.tenant_id {clause}"
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        summary = await conn.fetchrow(
            f"SELECT count(*) AS total, "
            f"COALESCE(sum(i.amount) FILTER (WHERE i.status = 'paid'), 0) AS paid_amount, "
            f"count(*) FILTER (WHERE i.status = 'paid') AS paid_count {base}",
            *params,
        )
        rows = await conn.fetch(
            f"SELECT i.id, i.number, i.description, i.amount, i.currency, i.status, "
            f"i.created_at, t.slug, t.name {base} "
            f"ORDER BY i.created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}",
            *params, limit, offset,
        )
    return {
        "invoices": [
            {
                "id": str(r["id"]),
                "number": int(r["number"]),
                "tenant_slug": r["slug"],
                "tenant_name": r["name"],
                "description": r["description"],
                "amount": float(r["amount"]),
                "currency": r["currency"],
                "status": r["status"],
                "created_at": _iso(r["created_at"]),
            }
            for r in rows
        ],
        "total": int(summary["total"]),
        "paid_amount": float(summary["paid_amount"]),
        "paid_count": int(summary["paid_count"]),
        "limit": limit,
        "offset": offset,
    }
