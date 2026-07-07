"""AI finance / profit view (operator plane).

``/admin/ai/finance`` — credits consumed (revenue value at the configured
credit price) vs actual provider COGS, by day / model / tenant.
"""

from __future__ import annotations

from acip_core.clients import get_pg_pool
from fastapi import APIRouter

from .admin_ai_common import _ADMIN, _AUTHZ, _COOKIE, _forbidden, _ok

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


@router.get("/finance")
async def finance(
    days: int = 30,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Profit view over a window: what tenants consumed (credits, valued at
    the configured credit price) vs what the platform actually paid providers
    (COGS), broken down by day, model and tenant."""
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    days = max(1, min(days, 365))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        pricing_row = await conn.fetchrow("SELECT * FROM pricing_settings WHERE id")
        totals = await conn.fetchrow(
            "SELECT COALESCE(sum(cost), 0) AS credits, "
            "COALESCE(sum(provider_cost), 0) AS cogs, count(*) AS calls "
            "FROM usage_events WHERE occurred_at >= now() - ($1 || ' days')::interval",
            str(days),
        )
        by_day = await conn.fetch(
            "SELECT date_trunc('day', occurred_at)::date AS day, "
            "COALESCE(sum(cost), 0) AS credits, COALESCE(sum(provider_cost), 0) AS cogs "
            "FROM usage_events WHERE occurred_at >= now() - ($1 || ' days')::interval "
            "GROUP BY 1 ORDER BY 1",
            str(days),
        )
        by_model = await conn.fetch(
            "SELECT COALESCE(provider, '—') AS provider, COALESCE(model, '—') AS model, "
            "count(*) AS calls, COALESCE(sum(tokens_in), 0) AS tokens_in, "
            "COALESCE(sum(tokens_out), 0) AS tokens_out, "
            "COALESCE(sum(cost), 0) AS credits, COALESCE(sum(provider_cost), 0) AS cogs "
            "FROM usage_events WHERE occurred_at >= now() - ($1 || ' days')::interval "
            "AND rung IN ('local', 'frontier') "
            "GROUP BY 1, 2 ORDER BY cogs DESC, credits DESC LIMIT 20",
            str(days),
        )
        by_tenant = await conn.fetch(
            "SELECT t.name, t.slug, count(*) AS calls, "
            "COALESCE(sum(u.cost), 0) AS credits, "
            "COALESCE(sum(u.provider_cost), 0) AS cogs "
            "FROM usage_events u JOIN tenants t ON t.id = u.tenant_id "
            "WHERE u.occurred_at >= now() - ($1 || ' days')::interval "
            "GROUP BY t.id ORDER BY credits DESC LIMIT 10",
            str(days),
        )
        revenue = await conn.fetch(
            "SELECT currency, COALESCE(sum(amount), 0) AS amount FROM invoices "
            "WHERE status = 'paid' AND created_at >= now() - ($1 || ' days')::interval "
            "GROUP BY currency",
            str(days),
        )
    from acip_billing.pricing import parse_pricing_row

    cfg = parse_pricing_row(pricing_row)
    credits = float(totals["credits"])
    cogs = float(totals["cogs"])
    value_usd = credits * cfg.usd_per_credit
    return {
        "days": days,
        "usd_per_credit": cfg.usd_per_credit,
        "margin_percent": cfg.margin_percent,
        "credits_consumed": credits,
        "consumption_value_usd": value_usd,
        "provider_cost_usd": cogs,
        "gross_margin_usd": value_usd - cogs,
        "calls": int(totals["calls"]),
        "billed_revenue": [
            {"currency": r["currency"], "amount": float(r["amount"])} for r in revenue
        ],
        "by_day": [
            {
                "day": r["day"].isoformat(),
                "credits": float(r["credits"]),
                "cogs_usd": float(r["cogs"]),
            }
            for r in by_day
        ],
        "by_model": [
            {
                "provider": r["provider"],
                "model": r["model"],
                "calls": int(r["calls"]),
                "tokens_in": int(r["tokens_in"]),
                "tokens_out": int(r["tokens_out"]),
                "credits": float(r["credits"]),
                "cogs_usd": float(r["cogs"]),
            }
            for r in by_model
        ],
        "by_tenant": [
            {
                "name": r["name"],
                "slug": r["slug"],
                "calls": int(r["calls"]),
                "credits": float(r["credits"]),
                "cogs_usd": float(r["cogs"]),
            }
            for r in by_tenant
        ],
    }
