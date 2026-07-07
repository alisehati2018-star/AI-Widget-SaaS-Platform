"""Admin surface — widget global defaults (M8): platform-wide widget
configuration set by the operator; per-store overrides live in tenant settings."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool, get_redis
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])

_WIDGET_DEFAULTS_KEY = "widget:global_defaults"


@router.get("/widget-defaults")
async def get_widget_defaults(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import json

    redis = get_redis()
    raw = await redis.get(_WIDGET_DEFAULTS_KEY) if redis is not None else None
    defaults = json.loads(raw) if raw else _default_widget_config()
    return {"defaults": defaults}


@router.post("/widget-defaults")
async def set_widget_defaults(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import json

    allowed = {
        "primary_color",
        "chat_enabled",
        "search_enabled",
        "position",
        "platform_brand",
        "max_results",
        "greeting",
    }
    defaults = {**_default_widget_config(), **{k: v for k, v in payload.items() if k in allowed}}
    redis = get_redis()
    if redis is not None:
        await redis.set(_WIDGET_DEFAULTS_KEY, json.dumps(defaults))
    await audit(await get_pg_pool(), actor="operator", action="widget.defaults", detail=defaults)
    return {"status": "saved", "defaults": defaults}


def _default_widget_config() -> dict[str, Any]:
    return {
        "primary_color": "#1A7A4B",
        "chat_enabled": True,
        "search_enabled": True,
        "position": "bottom-right",
        "platform_brand": True,
        "max_results": 12,
        "greeting": "سلام! چطور می‌تونم در پیدا کردن محصول کمکتون کنم؟",
    }
