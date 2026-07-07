"""Billing / buy-plan surface (Phase 7, M11) — subscription lifecycle.

Provider-agnostic checkout:
- A logged-in store owner starts checkout for a plan; the order is priced
  server-side from the `plans` table (never trust a client amount).
- The 'manual' provider leaves the order pending for operator confirmation
  (works out of the box). A real gateway is wired via ``/billing/webhook``,
  whose body is HMAC-SHA256 verified against ``BILLING_WEBHOOK_SECRET``.

Marking an order paid activates the subscription and grants the plan credits
(see ``acip_billing.subscription``).

Invoices (list/HTML/PDF) live in ``billing_invoices.py``; the ZarinPal
callback + provider webhook live in ``billing_webhooks.py``.
"""

from __future__ import annotations

from typing import Any

from acip_auth.models import Role
from acip_billing import create_order, create_topup_order, proration_preview, set_cancel
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from ..schemas import CheckoutRequest, TopupRequest, parse
from .billing_common import _AUTHZ, _COOKIE, _start_hosted_payment
from .tenant_common import _require_tenant

router = APIRouter(tags=["billing"])


@router.post("/tenant/billing/checkout")
async def checkout(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    if p.role != Role.STORE_OWNER:
        return error_response(403, "forbidden", "Only the store owner can purchase a plan.")
    assert p.tenant_id is not None
    req, invalid = parse(CheckoutRequest, payload)
    if invalid is not None or req is None:
        return invalid
    plan_code = req.plan_code.strip()

    s = get_settings()
    pool = await get_pg_pool()
    # Require a verified email before money-moving actions.
    if s.email_verification_required:
        async with pool.acquire() as conn:
            verified = await conn.fetchval(
                "SELECT email_verified FROM users WHERE id = $1", p.user_id
            )
        if not verified:
            return error_response(
                403,
                "email_unverified",
                "Verify your email before purchasing a plan.",
            )
    order = await create_order(pool, p.tenant_id, plan_code, provider=s.billing_provider)
    if order is None:
        return error_response(404, "unknown_plan", "No such plan.")
    await audit(
        pool,
        actor=p.email,
        action="billing.checkout",
        tenant_id=p.tenant_id,
        detail={"plan": plan_code, "order_id": order["order_id"]},
    )

    # The manual provider has no external redirect: the order awaits operator
    # confirmation. ZarinPal returns a hosted-payment redirect URL.
    if s.billing_provider == "manual":
        order["next"] = "awaiting_confirmation"
        order["instructions"] = (
            "Your order is pending. Complete payment per your invoice; access "
            "activates once the platform confirms receipt."
        )
        return order
    return await _start_hosted_payment(pool, order, f"Vitrin plan: {plan_code}", p.email)


@router.get("/tenant/billing/orders")
async def my_orders(
    limit: int = 100,
    offset: int = 0,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT o.id, o.amount, o.currency, o.status, o.provider, o.created_at, "
            "o.paid_at, COALESCE(pl.name, '—') AS plan FROM orders o "
            "LEFT JOIN plans pl ON pl.id = o.plan_id "
            "WHERE o.tenant_id = $1 ORDER BY o.created_at DESC LIMIT $2 OFFSET $3",
            p.tenant_id,
            max(1, min(200, limit)),
            max(0, offset),
        )
    return {
        "orders": [
            {
                "id": str(r["id"]),
                "plan": r["plan"],
                "amount": float(r["amount"]),
                "currency": r["currency"],
                "status": r["status"],
                "provider": r["provider"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "paid_at": r["paid_at"].isoformat() if r["paid_at"] else None,
            }
            for r in rows
        ]
    }


@router.get("/tenant/billing/preview")
async def preview(
    plan_code: str, authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """Proration preview for switching to a plan (credit for unused time)."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    assert p.tenant_id is not None
    s = get_settings()
    result = await proration_preview(
        await get_pg_pool(), p.tenant_id, plan_code, period_days=s.subscription_period_days
    )
    if result is None:
        return error_response(404, "unknown_plan", "No such plan.")
    return result


@router.post("/tenant/billing/topup")
async def topup(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """Buy a one-off credit top-up (priced by the configured rate)."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    if p.role != Role.STORE_OWNER:
        return error_response(403, "forbidden", "Only the store owner can buy credits.")
    assert p.tenant_id is not None
    req, invalid = parse(TopupRequest, payload)
    if invalid is not None or req is None:
        return invalid
    credits = req.credits
    s = get_settings()
    pool = await get_pg_pool()
    if s.email_verification_required:
        async with pool.acquire() as conn:
            verified = await conn.fetchval(
                "SELECT email_verified FROM users WHERE id = $1", p.user_id
            )
        if not verified:
            return error_response(403, "email_unverified", "Verify your email first.")
    order = await create_topup_order(pool, p.tenant_id, credits, provider=s.billing_provider)
    if order is None:
        return error_response(422, "invalid_request", "Could not create top-up.")
    await audit(
        pool,
        actor=p.email,
        action="billing.topup",
        tenant_id=p.tenant_id,
        detail={"credits": credits, "order_id": order["order_id"]},
    )
    if s.billing_provider == "manual":
        order["next"] = "awaiting_confirmation"
        return order
    return await _start_hosted_payment(pool, order, f"Vitrin credits: {credits:g}", p.email)


@router.post("/tenant/billing/cancel")
async def cancel(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    if p.role != Role.STORE_OWNER:
        return error_response(403, "forbidden", "Only the store owner can cancel.")
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    ok = await set_cancel(pool, p.tenant_id, True)
    if not ok:
        return error_response(404, "no_subscription", "No subscription to cancel.")
    await audit(pool, actor=p.email, action="billing.cancel", tenant_id=p.tenant_id, detail={})
    return {"status": "cancel_scheduled"}


@router.post("/tenant/billing/resume")
async def resume(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    if p.role != Role.STORE_OWNER:
        return error_response(403, "forbidden", "Only the store owner can resume.")
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    await set_cancel(pool, p.tenant_id, False)
    await audit(pool, actor=p.email, action="billing.resume", tenant_id=p.tenant_id, detail={})
    return {"status": "resumed"}
