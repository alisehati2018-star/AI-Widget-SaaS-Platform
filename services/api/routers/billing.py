"""Billing / buy-plan surface (Phase 7, M11).

Provider-agnostic checkout:
- A logged-in store owner starts checkout for a plan; the order is priced
  server-side from the `plans` table (never trust a client amount).
- The 'manual' provider leaves the order pending for operator confirmation
  (works out of the box). A real gateway is wired via ``/billing/webhook``,
  whose body is HMAC-SHA256 verified against ``BILLING_WEBHOOK_SECRET``.

Marking an order paid activates the subscription and grants the plan credits
(see ``acip_billing.subscription``).
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from acip_auth.models import Role
from acip_billing import create_order, mark_order_paid
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter, Header, Request

from .tenant import _require_tenant

router = APIRouter(tags=["billing"])

_AUTHZ = Header(default=None, alias="authorization")
_SIGNATURE = Header(default=None, alias="x-billing-signature")


@router.post("/tenant/billing/checkout")
async def checkout(payload: dict[str, Any], authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    if p.role != Role.STORE_OWNER:
        return error_response(403, "forbidden", "Only the store owner can purchase a plan.")
    assert p.tenant_id is not None
    plan_code = str(payload.get("plan_code", "")).strip()
    if not plan_code:
        return error_response(422, "invalid_request", "Field 'plan_code' is required.")

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
                403, "email_unverified",
                "Verify your email before purchasing a plan.",
            )
    order = await create_order(pool, p.tenant_id, plan_code, provider=s.billing_provider)
    if order is None:
        return error_response(404, "unknown_plan", "No such plan.")
    await audit(pool, actor=p.email, action="billing.checkout", tenant_id=p.tenant_id,
                detail={"plan": plan_code, "order_id": order["order_id"]})

    # The manual provider has no external redirect: the order awaits operator
    # confirmation. Real providers return a hosted-payment redirect URL here.
    if s.billing_provider == "manual":
        order["next"] = "awaiting_confirmation"
        order["instructions"] = (
            "Your order is pending. Complete payment per your invoice; access "
            "activates once the platform confirms receipt."
        )
    else:
        order["next"] = "redirect"
        order["redirect_url"] = ""  # populated by the concrete provider integration
    return order


@router.get("/tenant/billing/orders")
async def my_orders(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT o.id, o.amount, o.currency, o.status, o.provider, o.created_at, "
            "o.paid_at, COALESCE(pl.name, '—') AS plan FROM orders o "
            "LEFT JOIN plans pl ON pl.id = o.plan_id "
            "WHERE o.tenant_id = $1 ORDER BY o.created_at DESC LIMIT 100",
            p.tenant_id,
        )
    return {
        "orders": [
            {
                "id": str(r["id"]), "plan": r["plan"], "amount": float(r["amount"]),
                "currency": r["currency"], "status": r["status"], "provider": r["provider"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "paid_at": r["paid_at"].isoformat() if r["paid_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/billing/webhook")
async def webhook(request: Request, x_billing_signature: str | None = _SIGNATURE):
    """Payment-provider callback. Body is HMAC-SHA256 signed with
    ``BILLING_WEBHOOK_SECRET``; an invalid/absent signature is rejected."""
    s = get_settings()
    if not s.billing_webhook_secret:
        return error_response(503, "billing_unconfigured", "Webhooks are disabled.")
    raw = await request.body()
    expected = hmac.new(s.billing_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    if not x_billing_signature or not hmac.compare_digest(expected, x_billing_signature):
        return error_response(401, "bad_signature", "Invalid webhook signature.")
    import json

    try:
        body = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return error_response(400, "invalid_body", "Body must be JSON.")
    order_id = str(body.get("order_id", ""))
    status = str(body.get("status", ""))
    if status != "paid" or not order_id:
        return {"status": "ignored"}
    pool = await get_pg_pool()
    result = await mark_order_paid(pool, order_id, period_days=s.subscription_period_days)
    if result is None:
        return error_response(404, "unknown_order", "No such order.")
    await audit(pool, actor="provider", action="billing.paid",
                tenant_id=result["tenant_id"], detail={"order_id": order_id, "via": "webhook"})
    return {"status": "ok", "activated": result["plan_code"]}
