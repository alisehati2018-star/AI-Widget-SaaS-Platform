"""Provider quick-add templates + live model discovery (``/admin/ai/...``).

Lets an admin pick a known vendor (OpenRouter/OpenAI/Google/DeepSeek/Groq/
Bynara/AvalAI/Conduit), paste in an API key, then fetch that vendor's real
model list and bulk-import the ones they want — instead of typing every
model id in by hand via `admin_ai_providers.py::create_model`.
"""

from __future__ import annotations

from typing import Any

import httpx
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_gateway.provider_templates import PROVIDER_TEMPLATES, discover_models, get_template
from fastapi import APIRouter

from .admin_ai_common import (
    _ADMIN,
    _AUTHZ,
    _COOKIE,
    _UUID_RE,
    _forbidden,
    _invalid,
    _invalidate_registry,
    _model_row,
    _not_found,
    _ok,
    _provider_row,
)

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


@router.get("/provider-templates")
async def list_provider_templates(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        existing = {
            r["name"] for r in await conn.fetch("SELECT name FROM ai_providers")
        }
    return {
        "templates": [
            {**t, "already_created": t["key"] in existing} for t in PROVIDER_TEMPLATES
        ]
    }


@router.post("/providers/from-template")
async def create_provider_from_template(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    template_key = str(payload.get("template_key", "")).strip()
    template = get_template(template_key)
    if template is None:
        return _invalid("Unknown template_key.")
    name = str(payload.get("name", "")).strip() or template["key"]
    api_key = str(payload.get("api_key", "") or "").strip()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM ai_providers WHERE name = $1", name):
            return _invalid("A provider with this name already exists.")
        row = await conn.fetchrow(
            "INSERT INTO ai_providers (name, kind, base_url, api_key, is_local, enabled, "
            "discover_kind) VALUES ($1, 'openai-compatible', $2, $3, FALSE, TRUE, $4) "
            "RETURNING *",
            name,
            template["base_url"],
            api_key,
            template["discover_kind"],
        )
    await audit(
        pool, actor="operator", action="ai.provider_create",
        detail={"name": name, "template_key": template_key},
    )
    _invalidate_registry()
    return _provider_row(row)


@router.post("/providers/{provider_id}/discover")
async def discover_provider_models(
    provider_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _UUID_RE.match(provider_id):
        return _not_found()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        provider = await conn.fetchrow(
            "SELECT base_url, api_key, discover_kind FROM ai_providers WHERE id = $1",
            provider_id,
        )
        if provider is None:
            return _not_found()
        existing = {
            r["model"]
            for r in await conn.fetch(
                "SELECT model FROM ai_models WHERE provider_id = $1", provider_id
            )
        }
    try:
        models = await discover_models(
            base_url=provider["base_url"],
            api_key=provider["api_key"] or "",
            discover_kind=provider["discover_kind"],
        )
    except httpx.HTTPError as exc:
        return _invalid(f"Could not fetch the model list from this provider: {exc}")
    return {
        "models": [
            {**m, "already_imported": m["model"] in existing} for m in models
        ],
        "source": provider["discover_kind"],
    }


@router.post("/providers/{provider_id}/models/import")
async def import_discovered_models(
    provider_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _UUID_RE.match(provider_id):
        return _not_found()
    items = payload.get("models", [])
    if not isinstance(items, list) or not items or len(items) > 200:
        return _invalid("'models' must be a non-empty list of at most 200 entries.")
    modality = str(payload.get("modality", "chat"))
    if modality not in ("chat", "embedding", "rerank"):
        return _invalid("modality must be 'chat', 'embedding' or 'rerank'.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT 1 FROM ai_providers WHERE id = $1", provider_id):
            return _not_found()
        imported = []
        async with conn.transaction():
            for item in items:
                model_id = str(item.get("model", "")).strip()
                if not model_id:
                    continue
                context_window = item.get("context_length")
                try:
                    context_window = int(context_window) if context_window is not None else None
                except (TypeError, ValueError):
                    context_window = None
                input_cost = float(item.get("input_usd_per_1m", 0) or 0)
                output_cost = float(item.get("output_usd_per_1m", 0) or 0)
                is_free_tier = input_cost == 0 and output_cost == 0
                row = await conn.fetchrow(
                    "INSERT INTO ai_models (provider_id, model, label, input_usd_per_1m, "
                    "output_usd_per_1m, modality, context_window, is_free_tier) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
                    "ON CONFLICT (provider_id, model) DO UPDATE SET "
                    "label = EXCLUDED.label, input_usd_per_1m = EXCLUDED.input_usd_per_1m, "
                    "output_usd_per_1m = EXCLUDED.output_usd_per_1m, "
                    "context_window = EXCLUDED.context_window, "
                    "is_free_tier = EXCLUDED.is_free_tier RETURNING *",
                    provider_id,
                    model_id,
                    (str(item.get("label", "")).strip() or None) or model_id,
                    input_cost,
                    output_cost,
                    modality,
                    context_window,
                    is_free_tier,
                )
                imported.append(_model_row(row))
    await audit(
        pool, actor="operator", action="ai.model_import",
        detail={"provider_id": provider_id, "count": len(imported)},
    )
    _invalidate_registry()
    return {"imported": imported, "count": len(imported)}
