"""AI model catalog CRUD (operator plane).

``/admin/ai/models`` — the flat model catalog across every provider (list,
filter, create, edit, delete, bulk-delete). Provider CRUD lives in
``admin_ai_providers.py``.
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
)

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])
_MODALITIES = ("chat", "embedding", "rerank")


def _parse_modality_dims(payload: dict[str, Any]) -> tuple[str, int | None] | None:
    """Returns (modality, dims) or None if payload is invalid (caller returns
    the accompanying error)."""
    modality = str(payload.get("modality", "chat"))
    if modality not in _MODALITIES:
        return None
    dims = payload.get("dims")
    if dims is not None:
        try:
            dims = int(dims)
        except (TypeError, ValueError):
            return None
        if dims <= 0:
            return None
    return modality, dims


@router.get("/models")
async def list_models(
    provider_id: str | None = None,
    modality: str | None = None,
    q: str | None = None,
    include_inactive: bool = False,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Flat catalog across every provider — the Models page's data source."""
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    clauses: list[str] = []
    params: list[Any] = []
    if not include_inactive:
        clauses.append("m.enabled")
    if provider_id:
        if not _UUID_RE.match(provider_id):
            return _invalid("provider_id must be a UUID.")
        params.append(provider_id)
        clauses.append(f"m.provider_id = ${len(params)}")
    if modality:
        if modality not in _MODALITIES:
            return _invalid("modality must be 'chat', 'embedding' or 'rerank'.")
        params.append(modality)
        clauses.append(f"m.modality = ${len(params)}")
    if q:
        params.append(f"%{q.lower()}%")
        clauses.append(
            f"(lower(m.model) LIKE ${len(params)} OR lower(coalesce(m.label, '')) LIKE "
            f"${len(params)} OR lower(p.name) LIKE ${len(params)})"
        )
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT m.*, p.name AS provider_name, p.is_local AS provider_is_local "  # noqa: S608
            f"FROM ai_models m JOIN ai_providers p ON p.id = m.provider_id "
            f"{where} ORDER BY m.model",
            *params,
        )
    out = []
    for r in rows:
        row = _model_row(r)
        row["provider_name"] = r["provider_name"]
        row["provider_is_local"] = r["provider_is_local"]
        out.append(row)
    return {"models": out, "total": len(out)}


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
    parsed = _parse_modality_dims(payload)
    if parsed is None:
        return _invalid("Invalid modality/dims.")
    modality, dims = parsed
    context_window = payload.get("context_window")
    if context_window is not None:
        try:
            context_window = int(context_window)
        except (TypeError, ValueError):
            return _invalid("context_window must be an integer.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT 1 FROM ai_providers WHERE id = $1", provider_id):
            return _not_found()
        if await conn.fetchval(
            "SELECT 1 FROM ai_models WHERE provider_id = $1 AND model = $2", provider_id, model
        ):
            return _invalid("This model already exists on the provider.")
        input_cost = float(payload.get("input_usd_per_1m", 0) or 0)
        output_cost = float(payload.get("output_usd_per_1m", 0) or 0)
        is_free_tier = bool(payload.get("is_free_tier", input_cost == 0 and output_cost == 0))
        row = await conn.fetchrow(
            "INSERT INTO ai_models (provider_id, model, label, input_usd_per_1m, "
            "output_usd_per_1m, enabled, modality, dims, context_window, is_free_tier) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING *",
            provider_id,
            model,
            (str(payload.get("label", "")).strip() or None),
            input_cost,
            output_cost,
            bool(payload.get("enabled", True)),
            modality,
            dims,
            context_window,
            is_free_tier,
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
        ("modality", str), ("is_free_tier", bool),
    ):
        if key in payload:
            fields[key] = cast(payload[key])
    if "modality" in fields and fields["modality"] not in _MODALITIES:
        return _invalid("modality must be 'chat', 'embedding' or 'rerank'.")
    for int_field in ("dims", "context_window"):
        if int_field in payload:
            value = payload[int_field]
            if value is not None:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    return _invalid(f"{int_field} must be an integer.")
                if int_field == "dims" and value <= 0:
                    return _invalid("dims must be a positive integer.")
            fields[int_field] = value
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


async def _routes_using_model(conn, model_id: str) -> int:
    return await conn.fetchval(
        "SELECT count(*) FROM ai_routes WHERE model_id = $1", model_id
    )


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
        if not await conn.fetchval("SELECT 1 FROM ai_models WHERE id = $1", model_id):
            return _not_found()
        in_use = await _routes_using_model(conn, model_id)
        if in_use:
            return _invalid(
                f"This model is used in {in_use} routing chain position(s); "
                "remove it from AI Config first."
            )
        deleted = await conn.fetchval(
            "DELETE FROM ai_models WHERE id = $1 RETURNING model", model_id
        )
    await audit(pool, actor="operator", action="ai.model_delete", detail={"model": deleted})
    _invalidate_registry()
    return {"status": "deleted"}


@router.post("/models/bulk-delete")
async def bulk_delete_models(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return _invalid("'ids' must be a non-empty list of model UUIDs.")
    unique_ids = list(dict.fromkeys(str(i) for i in ids))
    pool = await get_pg_pool()
    deleted: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    async with pool.acquire() as conn:
        for model_id in unique_ids:
            if not _UUID_RE.match(model_id):
                continue
            row = await conn.fetchrow(
                "SELECT id, model, label FROM ai_models WHERE id = $1", model_id
            )
            if row is None:
                continue
            in_use = await _routes_using_model(conn, model_id)
            if in_use:
                blocked.append({"id": model_id, "model": row["model"], "chain_positions": in_use})
                continue
            await conn.execute("DELETE FROM ai_models WHERE id = $1", model_id)
            deleted.append({"id": model_id, "model": row["model"]})
    if deleted:
        await audit(
            pool, actor="operator", action="ai.model_bulk_delete",
            detail={"deleted": len(deleted), "blocked": len(blocked)},
        )
        _invalidate_registry()
    return {"deleted": len(deleted), "blocked": blocked}
