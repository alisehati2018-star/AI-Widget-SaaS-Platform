"""Shared helpers for the billing routers: PSP selection, hosted-payment
redirects, and the paid-invoice receipt email."""

from __future__ import annotations

from acip_core.config import get_settings
from acip_core.errors import error_response
from acip_notify import invoice_email, send_email
from fastapi import Cookie, Header

_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_access")
_SIGNATURE = Header(default=None, alias="x-billing-signature")


def _zarinpal():
    """The configured ZarinPal provider, or None (manual mode)."""
    s = get_settings()
    if s.billing_provider != "zarinpal" or not s.zarinpal_merchant_id:
        return None
    from acip_billing.psp import ZarinPalProvider

    api_origin = (s.widget_base_url or s.app_base_url).rstrip("/")
    return ZarinPalProvider(
        s.zarinpal_merchant_id,
        f"{api_origin}/billing/callback",
        base_url=s.zarinpal_base_url,
    )


async def _start_hosted_payment(pool, order: dict, description: str, email: str):
    """Attach a hosted-payment redirect to a pending order (ZarinPal).

    On PSP failure the order stays pending and a stable 502 is returned —
    the shopper can retry; nothing was activated.
    """
    from acip_billing.psp import PspError

    psp = _zarinpal()
    if psp is None:
        order["next"] = "awaiting_confirmation"
        return order
    try:
        payment = await psp.request_payment(
            float(order["amount"]), description, email=email or None
        )
    except PspError as exc:
        return error_response(502, "psp_unavailable", f"Payment gateway error: {exc}")
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE orders SET provider_ref = $1 WHERE id = $2::uuid",
            payment["authority"],
            order["order_id"],
        )
    order["next"] = "redirect"
    order["redirect_url"] = payment["redirect_url"]
    return order


async def _email_invoice(pool, result: dict) -> None:
    """Send the paid invoice receipt to the tenant's owner (best-effort)."""
    if not result.get("invoice_number"):
        return
    async with pool.acquire() as conn:
        email = await conn.fetchval(
            "SELECT email FROM users WHERE tenant_id = $1 AND role = 'store_owner' "
            "ORDER BY created_at ASC LIMIT 1",
            result["tenant_id"],
        )
    if not email:
        return
    desc = (
        f"{result.get('plan_name') or 'Plan'} plan"
        if result.get("kind") == "subscription"
        else "Credit top-up"
    )
    subject, text, html = invoice_email(
        result["invoice_number"], desc, result["amount"], result["currency"]
    )
    await send_email(email, subject, text, html)
