"""Billing — invoice listing + printable HTML/PDF receipts (tenant-scoped)."""

from __future__ import annotations

from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from .billing_common import _AUTHZ, _COOKIE
from .tenant_common import _require_tenant

router = APIRouter(tags=["billing"])


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
