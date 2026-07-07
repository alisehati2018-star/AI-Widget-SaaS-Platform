"""AI provider + model registry CRUD (operator plane).

``/admin/ai/providers`` (+ models) — CRUD over the vendor registry with each
model's real per-1M-token provider cost. API keys are write-only (masked on
every read).
"""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
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


# --------------------------------------------------------------------------- #
# Providers                                                                    #
# --------------------------------------------------------------------------- #
@router.get("/providers")
async def list_providers(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        providers = await conn.fetch("SELECT * FROM ai_providers ORDER BY created_at")
        models = await conn.fetch("SELECT * FROM ai_models ORDER BY created_at")
    by_provider: dict[str, list[dict]] = {}
    for m in models:
        by_provider.setdefault(str(m["provider_id"]), []).append(_model_row(m))
    out = []
    for p in providers:
        row = _provider_row(p)
        row["models"] = by_provider.get(row["id"], [])
        out.append(row)
    return {"providers": out}


@router.post("/providers")
async def create_provider(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    name = str(payload.get("name", "")).strip()
    base_url = str(payload.get("base_url", "")).strip()
    if not name or not base_url:
        return _invalid("Fields 'name' and 'base_url' are required.")
    kind = str(payload.get("kind", "openai-compatible"))
    if kind not in ("openai-compatible", "local"):
        return _invalid("kind must be 'openai-compatible' or 'local'.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM ai_providers WHERE name = $1", name):
            return _invalid("A provider with this name already exists.")
        row = await conn.fetchrow(
            "INSERT INTO ai_providers (name, kind, base_url, api_key, is_local, enabled, "
            "timeout_s, notes) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *",
            name,
            kind,
            base_url,
            str(payload.get("api_key", "") or ""),
            bool(payload.get("is_local", kind == "local")),
            bool(payload.get("enabled", True)),
            float(payload.get("timeout_s", 30) or 30),
            (str(payload.get("notes", "")).strip() or None),
        )
    await audit(pool, actor="operator", action="ai.provider_create", detail={"name": name})
    _invalidate_registry()
    return _provider_row(row)


@router.patch("/providers/{provider_id}")
async def update_provider(
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
    fields: dict[str, Any] = {}
    for key, cast in (
        ("name", str), ("base_url", str), ("notes", str),
        ("is_local", bool), ("enabled", bool), ("timeout_s", float),
    ):
        if key in payload:
            fields[key] = cast(payload[key])
    # api_key is write-only: an empty/missing value means "keep the stored key".
    if str(payload.get("api_key", "") or "").strip():
        fields["api_key"] = str(payload["api_key"]).strip()
    if not fields:
        return _invalid("No editable fields provided.")
    sets = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE ai_providers SET {sets}, updated_at = now() "  # noqa: S608
            "WHERE id = $1 RETURNING *",
            provider_id,
            *fields.values(),
        )
    if row is None:
        return _not_found()
    await audit(
        pool, actor="operator", action="ai.provider_update",
        detail={"id": provider_id, "fields": sorted(fields)},
    )
    _invalidate_registry()
    return _provider_row(row)


@router.delete("/providers/{provider_id}")
async def delete_provider(
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
        deleted = await conn.fetchval(
            "DELETE FROM ai_providers WHERE id = $1 RETURNING name", provider_id
        )
    if deleted is None:
        return _not_found()
    await audit(pool, actor="operator", action="ai.provider_delete", detail={"name": deleted})
    _invalidate_registry()
    return {"status": "deleted"}


@router.post("/providers/{provider_id}/ping")
async def ping_provider(
    provider_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Reachability probe: any HTTP answer from base_url proves it listens."""
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _UUID_RE.match(provider_id):
        return _not_found()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        url = await conn.fetchval(
            "SELECT base_url FROM ai_providers WHERE id = $1", provider_id
        )
    if url is None:
        return _not_found()
    import time

    import httpx

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            await client.get(url)
        return {"reachable": True, "latency_ms": int((time.monotonic() - t0) * 1000)}
    except Exception:  # noqa: BLE001
        return {"reachable": False, "latency_ms": None}


# --------------------------------------------------------------------------- #
# Models                                                                       #
# --------------------------------------------------------------------------- #
@router.post("/providers/{provider_id}/models")
async def create_model(
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
    model = str(payload.get("model", "")).strip()
    if not model:
        return _invalid("Field 'model' is required.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT 1 FROM ai_providers WHERE id = $1", provider_id):
            return _not_found()
        if await conn.fetchval(
            "SELECT 1 FROM ai_models WHERE provider_id = $1 AND model = $2", provider_id, model
        ):
            return _invalid("This model already exists on the provider.")
        row = await conn.fetchrow(
            "INSERT INTO ai_models (provider_id, model, label, input_usd_per_1m, "
            "output_usd_per_1m, enabled) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *",
            provider_id,
            model,
            (str(payload.get("label", "")).strip() or None),
            float(payload.get("input_usd_per_1m", 0) or 0),
            float(payload.get("output_usd_per_1m", 0) or 0),
            bool(payload.get("enabled", True)),
        )
    await audit(pool, actor="operator", action="ai.model_create", detail={"model": model})
    _invalidate_registry()
    return _model_row(row)


@router.patch("/models/{model_id}")
async def update_model(
    model_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _UUID_RE.match(model_id):
        return _not_found()
    fields: dict[str, Any] = {}
    for key, cast in (
        ("model", str), ("label", str), ("enabled", bool),
        ("input_usd_per_1m", float), ("output_usd_per_1m", float),
    ):
        if key in payload:
            fields[key] = cast(payload[key])
    if not fields:
        return _invalid("No editable fields provided.")
    sets = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE ai_models SET {sets} WHERE id = $1 RETURNING *",  # noqa: S608
            model_id,
            *fields.values(),
        )
    if row is None:
        return _not_found()
    await audit(
        pool, actor="operator", action="ai.model_update",
        detail={"id": model_id, "fields": sorted(fields)},
    )
    _invalidate_registry()
    return _model_row(row)


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _UUID_RE.match(model_id):
        return _not_found()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        deleted = await conn.fetchval(
            "DELETE FROM ai_models WHERE id = $1 RETURNING model", model_id
        )
    if deleted is None:
        return _not_found()
    await audit(pool, actor="operator", action="ai.model_delete", detail={"model": deleted})
    _invalidate_registry()
    return {"status": "deleted"}
