"""Store-owner dashboard API — profile overview + widget install info.

Every other tenant-dashboard domain (search/analytics/assistant, catalogue
sync, leads, API keys, settings, team, GDPR self-serve, credits, audit,
knowledge base) lives in its own `tenant_*` router — all mounted under the
same `/tenant` prefix in `main.py`, so the split is invisible to clients.
"""

from __future__ import annotations

from acip_billing.ledger import plan_status, usage_summary
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/profile")
async def profile(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        t = await conn.fetchrow(
            "SELECT t.slug, t.name, t.status, t.tracking_enabled, t.settings, "
            "COALESCE(pl.name, '—') AS plan, pl.code AS plan_code, "
            "COALESCE(pl.name_fa, pl.name, '—') AS plan_fa, "
            "COALESCE(s.status, 'none') AS sub_status, "
            "s.current_period_end "
            "FROM tenants t "
            "LEFT JOIN subscriptions s ON s.tenant_id = t.id "
            "LEFT JOIN plans pl ON pl.id = s.plan_id WHERE t.id = $1",
            p.tenant_id,
        )
        email_verified = await conn.fetchval(
            "SELECT email_verified FROM users WHERE id = $1", p.user_id
        )
    status = await plan_status(pool, p.tenant_id)
    usage = await usage_summary(pool, p.tenant_id)
    if t is None:
        return error_response(404, "not_found", "Tenant not found.")
    period_end = t["current_period_end"]
    return {
        "tenant_id": p.tenant_id,
        "slug": t["slug"],
        "name": t["name"],
        "status": t["status"],
        "plan": t["plan"],
        "plan_code": t["plan_code"],
        "plan_fa": t["plan_fa"],
        "sub_status": t["sub_status"],
        "current_period_end": period_end.isoformat() if period_end else None,
        "tracking_enabled": t["tracking_enabled"],
        "settings": t["settings"],
        "email_verified": bool(email_verified),
        "credits": {
            "spent": usage["used"],
            "granted": usage["granted"],
            "balance": status.get("balance", 0.0),
            "cap": status.get("cap"),
            "within_plan": status.get("within_plan", True),
        },
        "role": p.role.value,
    }


@router.get("/widget")
async def widget_embed(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    """Widget install info for the dashboard: the public loader base, whether the
    store is approved + has an active widget key (so the embed line is 'ready'),
    the one-line snippet, and the store's per-store widget settings."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    s = get_settings()
    api_base = (s.widget_base_url or s.app_base_url).rstrip("/")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, settings FROM tenants WHERE id = $1", p.tenant_id
        )
        has_widget_key = bool(
            await conn.fetchval(
                "SELECT 1 FROM api_keys WHERE tenant_id = $1 AND scope = 'widget' "
                "AND revoked = FALSE LIMIT 1",
                p.tenant_id,
            )
        )
    status = row["status"] if row else "pending"
    approved = status == "active"
    ready = approved and has_widget_key
    settings = row["settings"] if row else {}
    if isinstance(settings, str):
        import json as _json

        try:
            settings = _json.loads(settings)
        except (ValueError, TypeError):
            settings = {}
    key_hint = "YOUR_WIDGET_KEY"
    snippet = (
        f'<script src="{api_base}/widget/v1.js"\n'
        f'        data-acip-key="{key_hint}"\n'
        f'        data-acip-base="{api_base}" async></script>'
    )
    return {
        "api_base": api_base,
        "status": status,
        "approved": approved,
        "has_widget_key": has_widget_key,
        "ready": ready,
        "snippet": snippet,
        "settings": settings or {},
    }
