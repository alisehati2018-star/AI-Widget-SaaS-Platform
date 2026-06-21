"""Public (unauthenticated) read surface for the marketing site (Phase 7).

Only non-sensitive, cacheable data: the published plan catalogue that powers the
pricing page. No tenant data, no PII.
"""

from __future__ import annotations

from typing import Any

from acip_core.clients import get_pg_pool
from fastapi import APIRouter

router = APIRouter(tags=["public"])


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    """Public plan catalogue for the pricing page (ordered, public plans only)."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT code, name, description, price_monthly, currency, credits_per_month, "
            "rate_limit_per_min, features, sort_order FROM plans "
            "WHERE is_public = TRUE ORDER BY sort_order ASC"
        )
    return {
        "plans": [
            {
                "code": r["code"],
                "name": r["name"],
                "description": r["description"],
                "price_monthly": float(r["price_monthly"]),
                "currency": r["currency"],
                "credits_per_month": float(r["credits_per_month"]),
                "rate_limit_per_min": r["rate_limit_per_min"],
                "features": r["features"],
            }
            for r in rows
        ]
    }
