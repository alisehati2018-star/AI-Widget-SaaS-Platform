"""Embeddable widget surface (M8).

Serves the single-line loader script the store drops into its site, and the
per-store widget config the loader fetches (global operator defaults merged with
the tenant's own dashboard settings). The loader + config talk only to the
public API with a shopper-scoped key — presentation only, never weakens the
tenant isolation invariant.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from acip_core.clients import get_pg_pool, get_redis
from fastapi import APIRouter, Header, Response

from ..deps import API_KEY_HEADER, KeyScope, principal_allowed, resolve_principal

router = APIRouter(tags=["widget"])

_KEY = Header(default=None, alias=API_KEY_HEADER)

# loader.js lives in the repo at apps/dashboard/widget/loader.js
_LOADER_PATH = (
    Path(__file__).resolve().parents[3] / "apps" / "dashboard" / "widget" / "loader.js"
)
_WIDGET_DEFAULTS_KEY = "widget:global_defaults"

# Keys a store may override from its dashboard (presentation only).
_TENANT_KEYS = (
    "primary_color",
    "logo_url",
    "greeting",
    "position",
    "title",
    "placeholder",
    "chat_enabled",
    "search_enabled",
)


def _platform_defaults() -> dict[str, Any]:
    return {
        "primary_color": "#1A7A4B",
        "chat_enabled": True,
        "search_enabled": True,
        "position": "bottom-right",
        "max_results": 12,
        "greeting": "سلام! چطور می‌تونم در پیدا کردن محصول کمکتون کنم؟",
    }


@router.get("/widget/v1.js")
async def loader_script() -> Response:
    """The single-line embeddable loader (cacheable, public)."""
    try:
        body = _LOADER_PATH.read_text(encoding="utf-8")
    except OSError:
        body = "/* acip widget loader unavailable */"
    return Response(
        content=body,
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/v1/widget/config")
async def widget_config(x_api_key: str | None = _KEY) -> Any:
    """Resolved widget config for a store: global defaults ← tenant overrides."""
    principal = await resolve_principal(x_api_key)
    if not principal.tenant_id or not principal_allowed(principal, KeyScope.WIDGET):
        # Public-safe defaults if the key is missing/invalid — the widget still
        # renders, just without store branding.
        return _platform_defaults()

    config = _platform_defaults()
    redis = get_redis()
    if redis is not None:
        raw = await redis.get(_WIDGET_DEFAULTS_KEY)
        if raw:
            try:
                config.update(json.loads(raw))
            except (ValueError, TypeError):
                pass

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        settings = await conn.fetchval(
            "SELECT settings FROM tenants WHERE id = $1", principal.tenant_id
        )
    if isinstance(settings, str):
        try:
            settings = json.loads(settings)
        except (ValueError, TypeError):
            settings = {}
    settings = settings or {}
    # Map dashboard setting names → widget config keys.
    if settings.get("widget_greeting"):
        config["greeting"] = settings["widget_greeting"]
    for key in _TENANT_KEYS:
        if settings.get(key) not in (None, ""):
            config[key] = settings[key]
    return config
