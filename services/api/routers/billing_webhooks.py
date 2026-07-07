"""Billing — payment-provider callbacks: the ZarinPal return URL and the
generic signed webhook."""

from __future__ import annotations

import hashlib
import hmac

from acip_billing import mark_order_paid
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter, Request

from .billing_common import _SIGNATURE, _email_invoice, _zarinpal

router = APIRouter(tags=["billing"])


@router.get("/billing/callback")
async def zarinpal_callback(Authority: str = "", Status: str = ""):  # noqa: N803 - ZarinPal's casing
    """ZarinPal return URL. The redirect alone activates NOTHING: the order is
    looked up by its stored authority and the payment is verified server-side
    (amount included) before it is marked paid. The shopper is then bounced
    back to the dashboard billing page with a status flag."""
    from fastapi.responses import RedirectResponse

    s = get_settings()
    back = f"{s.app_base_url.rstrip('/')}/dashboard/billing"
    if not Authority:
        return RedirectResponse(f"{back}?payment=failed", status_code=302)

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        order = await conn.fetchrow(
            "SELECT id, tenant_id, amount, status FROM orders "
            "WHERE provider_ref = $1 AND provider = 'zarinpal' "
            "ORDER BY created_at DESC LIMIT 1",
            Authority,
        )
    if order is None:
        return RedirectResponse(f"{back}?payment=failed", status_code=302)
    if order["status"] == "paid":  # replayed callback: already settled
        return RedirectResponse(f"{back}?payment=success", status_code=302)

    psp = _zarinpal()
    verified = None
    if psp is not None and Status == "OK":
        from acip_billing.psp import PspError

        try:
            verified = await psp.verify(Authority, float(order["amount"]))
        except PspError:
            verified = None
    if verified is None:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE orders SET status = 'failed' WHERE id = $1 AND status = 'pending'",
                order["id"],
            )
        await audit(
            pool,
            actor="zarinpal",
            action="billing.payment_failed",
            tenant_id=str(order["tenant_id"]),
            detail={"authority": Authority, "status": Status},
        )
        return RedirectResponse(f"{back}?payment=failed", status_code=302)

    result = await mark_order_paid(
        pool, str(order["id"]), period_days=s.subscription_period_days
    )
    if result is not None and not result.get("already"):
        await _email_invoice(pool, result)
    await audit(
        pool,
        actor="zarinpal",
        action="billing.paid",
        tenant_id=str(order["tenant_id"]),
        detail={"authority": Authority, "ref_id": verified["ref_id"], "via": "callback"},
    )
    return RedirectResponse(f"{back}?payment=success&ref={verified['ref_id']}", status_code=302)


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
    if not result.get("already"):
        await _email_invoice(pool, result)
    await audit(
        pool,
        actor="provider",
        action="billing.paid",
        tenant_id=result["tenant_id"],
        detail={"order_id": order_id, "via": "webhook", "kind": result["kind"]},
    )
    return {"status": "ok", "kind": result["kind"], "activated": result.get("plan_code")}
