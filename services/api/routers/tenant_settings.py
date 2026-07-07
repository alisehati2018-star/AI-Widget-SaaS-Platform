"""Store-owner dashboard — store settings + white-label branding."""

from __future__ import annotations

from typing import Any

from acip_auth.models import Role
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _owner_only, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.patch("/settings")
async def update_settings(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    # Whitelist the keys a tenant may set (platform branding stays visible).
    allowed = {
        "logo_url", "primary_color", "store_url", "platform", "widget_greeting",
        "position", "chat_enabled", "search_enabled", "title", "placeholder",
        # Store pull credentials for delta reconciliation (Phase 7).
        "woo_consumer_key", "woo_consumer_secret", "oc_export_token",
    }
    patch = {k: v for k, v in payload.items() if k in allowed}
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE tenants SET settings = settings || $1::jsonb, updated_at = now() WHERE id = $2",
            patch,
            p.tenant_id,
        )
    await audit(pool, actor=p.email, action="settings.update", tenant_id=p.tenant_id, detail=patch)
    return {"status": "saved", "settings": patch}
