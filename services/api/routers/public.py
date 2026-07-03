"""Public (unauthenticated) read surface for the marketing site (Phase 7).

Only non-sensitive, cacheable data: the published plan catalogue that powers the
pricing page. No tenant data, no PII.
"""

from __future__ import annotations

import re
from typing import Any

from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from acip_notify import contact_notification, send_email
from fastapi import APIRouter

router = APIRouter(tags=["public"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    """Public plan catalogue for the pricing page (ordered, public plans only)."""
    from acip_core.config import get_settings

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT code, name, name_fa, description, description_fa, price_monthly, "
            "currency, credits_per_month, rate_limit_per_min, features, features_fa, "
            "sort_order FROM plans WHERE is_public = TRUE ORDER BY sort_order ASC"
        )
    s = get_settings()
    return {
        "plans": [
            {
                "code": r["code"],
                "name": r["name"],
                "name_fa": r["name_fa"],
                "description": r["description"],
                "description_fa": r["description_fa"],
                "price_monthly": float(r["price_monthly"]),
                "currency": r["currency"],
                "credits_per_month": float(r["credits_per_month"]),
                "rate_limit_per_min": r["rate_limit_per_min"],
                "features": r["features"],
                "features_fa": r["features_fa"],
            }
            for r in rows
        ],
        # Billing meta so clients price things (e.g. credit top-ups) from the
        # SERVER's configuration instead of hardcoding a rate (audit W7).
        "billing": {
            "currency": s.billing_currency,
            "topup_credits_per_unit": s.topup_credits_per_unit,
        },
    }


@router.post("/contact")
async def contact(payload: dict[str, Any]) -> Any:
    """Public contact form: persist the message + notify the platform inbox."""
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    message = str(payload.get("message", "")).strip()
    if not name or not message or not _EMAIL_RE.match(email):
        return error_response(422, "invalid_request", "name, valid email and message are required.")
    if len(message) > 5000:
        return error_response(422, "too_long", "Message is too long.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO contact_messages (name, email, message) VALUES ($1, $2, $3)",
            name, email, message,
        )
    subject, text, html = contact_notification(name, email, message)
    await send_email(get_settings().contact_inbox, subject, text, html)
    return {"status": "received"}
