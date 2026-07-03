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
from acip_billing import (
    create_order,
    create_topup_order,
    mark_order_paid,
    proration_preview,
    set_cancel,
)
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from acip_notify import invoice_email, send_email
from fastapi import APIRouter, Cookie, Header, Request

from ..schemas import CheckoutRequest, TopupRequest, parse
from .tenant import _require_tenant


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


router = APIRouter(tags=["billing"])

_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_access")
_SIGNATURE = Header(default=None, alias="x-billing-signature")


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


@router.get("/tenant/billing/invoices")
async def invoices(
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
            "SELECT number, description, amount, currency, status, created_at FROM invoices "
            "WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            p.tenant_id,
            max(1, min(200, limit)),
            max(0, offset),
        )
    return {
        "invoices": [
            {
                "number": r["number"],
                "description": r["description"],
                "amount": float(r["amount"]),
                "currency": r["currency"],
                "status": r["status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }


_INVOICE_HTML = """<!doctype html><html dir="rtl" lang="fa"><head><meta charset="utf-8">
<title>فاکتور {number}</title>
<style>
  body {{ font-family: Tahoma, sans-serif; max-width: 640px; margin: 3rem auto; color: #111; }}
  .head {{ display: flex; justify-content: space-between; align-items: baseline;
           border-bottom: 2px solid #111; padding-bottom: .75rem; }}
  h1 {{ font-size: 1.3rem; margin: 0; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
  td, th {{ padding: .6rem .4rem; border-bottom: 1px solid #ddd; text-align: right; }}
  .total {{ font-weight: bold; font-size: 1.1rem; }}
  .muted {{ color: #666; font-size: .85rem; }}
  .badge {{ padding: .15rem .6rem; border: 1px solid #111; border-radius: 999px;
            font-size: .8rem; }}
  @media print {{ body {{ margin: 1rem; }} }}
</style></head><body>
<div class="head"><h1>فاکتور شمارهٔ {number}</h1><span class="badge">{status_fa}</span></div>
<p class="muted">فروشگاه: {store} · تاریخ صدور: {date}</p>
<table>
  <thead><tr><th>شرح</th><th>مبلغ</th></tr></thead>
  <tbody>
    <tr><td>{description}</td><td>{amount} {currency}</td></tr>
    <tr class="total"><td>جمع کل</td><td>{amount} {currency}</td></tr>
  </tbody>
</table>
<p class="muted">این فاکتور توسط پلتفرم ویترین صادر شده است. برای چاپ یا ذخیره به‌صورت PDF از
گزینهٔ Print مرورگر استفاده کنید.</p>
</body></html>"""


@router.get("/tenant/billing/invoices/{number}/html")
async def invoice_html(
    number: int, authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """A standalone, printable HTML invoice (browser print → PDF). Scoped to
    the signed-in tenant — the number is only looked up within their rows."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT i.number, i.description, i.amount, i.currency, i.status, i.created_at, "
            "t.name AS store FROM invoices i JOIN tenants t ON t.id = i.tenant_id "
            "WHERE i.tenant_id = $1 AND i.number = $2",
            p.tenant_id,
            number,
        )
    if row is None:
        return error_response(404, "not_found", "No such invoice.")
    import html as _html

    from fastapi.responses import HTMLResponse

    html = _INVOICE_HTML.format(
        number=row["number"],
        status_fa="پرداخت‌شده" if row["status"] == "paid" else "باطل‌شده",
        # Store name and description are tenant-authored text — escape them so
        # the printable page can never carry markup into a teammate's browser.
        store=_html.escape(row["store"] or ""),
        date=row["created_at"].strftime("%Y-%m-%d") if row["created_at"] else "—",
        description=_html.escape(row["description"] or ""),
        amount=f"{float(row['amount']):,.2f}",
        currency=_html.escape(row["currency"] or ""),
    )
    return HTMLResponse(content=html)


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


@router.get("/tenant/billing/invoices/{number}/pdf")
async def invoice_pdf(
    number: int, authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """The invoice as a downloadable PDF (server-rendered, Persian-shaped).
    Falls back with a clear 503 when no PDF font/engine is available — the
    printable HTML route always works."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return error_response(401, "unauthenticated", "Sign in to your store account.")
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT i.number, i.description, i.amount, i.currency, i.status, i.created_at, "
            "t.name AS store FROM invoices i JOIN tenants t ON t.id = i.tenant_id "
            "WHERE i.tenant_id = $1 AND i.number = $2",
            p.tenant_id,
            number,
        )
    if row is None:
        return error_response(404, "not_found", "No such invoice.")
    from acip_billing.invoice_pdf import render_invoice_pdf

    pdf = render_invoice_pdf(
        number=row["number"],
        store=row["store"] or "",
        date=row["created_at"].strftime("%Y-%m-%d") if row["created_at"] else "—",
        description=row["description"] or "",
        amount=f"{float(row['amount']):,.2f}",
        currency=row["currency"] or "",
        status_fa="پرداخت‌شده" if row["status"] == "paid" else "باطل‌شده",
        font_path=get_settings().invoice_font_path or None,
    )
    if pdf is None:
        return error_response(
            503, "pdf_unavailable",
            "PDF rendering is not available on this server (no Persian font/engine); "
            "use the printable HTML invoice instead.",
        )
    from fastapi.responses import Response

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice-{number}.pdf"'},
    )


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
