"""AI task routing + pricing management (operator plane).

``/admin/ai/routes`` — the ordered model chain per task ('chat', 'analyst');
changes apply live through the gateway registry's TTL cache.
``/admin/ai/pricing`` — credit value, platform margin, flat search price and
local-model cost attribution.
"""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from fastapi import APIRouter

from .admin_ai_common import (
    _ADMIN,
    _AUTHZ,
    _COOKIE,
    _TASK_MODALITY,
    _TASKS,
    _UUID_RE,
    _forbidden,
    _invalid,
    _invalidate_registry,
    _model_eligibility,
    _ok,
)

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


# --------------------------------------------------------------------------- #
# Routes (task → ordered model chain)                                          #
# --------------------------------------------------------------------------- #
@router.get("/routes")
async def get_routes(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT r.task, r.position, r.model_id, m.model, m.label, m.enabled AS model_enabled, "
            "p.name AS provider, p.is_local, p.enabled AS provider_enabled, "
            "(p.api_key <> '') AS provider_has_api_key "
            "FROM ai_routes r JOIN ai_models m ON m.id = r.model_id "
            "JOIN ai_providers p ON p.id = m.provider_id ORDER BY r.task, r.position"
        )
    routes: dict[str, list[dict]] = {task: [] for task in _TASKS}
    for r in rows:
        is_eligible, reason = _model_eligibility(
            r["model_enabled"], r["provider_enabled"], r["provider_has_api_key"]
        )
        routes.setdefault(r["task"], []).append(
            {
                "model_id": str(r["model_id"]),
                "model": r["model"],
                "label": r["label"],
                "provider": r["provider"],
                "is_local": r["is_local"],
                "is_eligible": is_eligible,
                "ineligible_reason": reason,
            }
        )
    return {"routes": routes, "tasks": list(_TASKS)}


@router.put("/routes/{task}")
async def put_route(
    task: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Replace the ordered chain for one task with the given model-id list."""
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if task not in _TASKS:
        return _invalid(f"task must be one of {', '.join(_TASKS)}.")
    model_ids = payload.get("model_ids", [])
    if not isinstance(model_ids, list) or len(model_ids) > 10:
        return _invalid("'model_ids' must be a list of at most 10 model ids.")
    for mid in model_ids:
        if not isinstance(mid, str) or not _UUID_RE.match(mid):
            return _invalid("Every entry of 'model_ids' must be a model UUID.")
    required_modality = _TASK_MODALITY[task]
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            found = {
                str(r["id"]): r
                for r in await conn.fetch(
                    "SELECT id, modality, dims FROM ai_models WHERE id = ANY($1::uuid[])",
                    model_ids,
                )
            }
            missing = [m for m in model_ids if m not in found]
            if missing:
                return _invalid("Unknown model id(s) in 'model_ids'.")
            wrong_modality = [
                mid for mid in model_ids if found[mid]["modality"] != required_modality
            ]
            if wrong_modality:
                return _invalid(
                    f"task '{task}' requires models of modality '{required_modality}'."
                )
            if task == "embedding":
                expected_dims = get_settings().embedding_dims
                mismatched = [
                    mid for mid in model_ids
                    if found[mid]["dims"] is not None and found[mid]["dims"] != expected_dims
                ]
                if mismatched:
                    return _invalid(
                        f"model dims must match the configured embedding dimension "
                        f"({expected_dims}); check the model(s) with a different 'dims' value."
                    )
            await conn.execute("DELETE FROM ai_routes WHERE task = $1", task)
            for pos, mid in enumerate(model_ids):
                await conn.execute(
                    "INSERT INTO ai_routes (task, position, model_id) VALUES ($1, $2, $3)",
                    task,
                    pos,
                    mid,
                )
    await audit(
        pool, actor="operator", action="ai.route_update",
        detail={"task": task, "chain_length": len(model_ids)},
    )
    _invalidate_registry()
    return {"task": task, "count": len(model_ids)}


# --------------------------------------------------------------------------- #
# Global routing settings (failover master switch)                            #
# --------------------------------------------------------------------------- #
@router.get("/routing-settings")
async def get_routing_settings(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT failover_enabled FROM ai_routing_settings WHERE id")
    return {"failover_enabled": row["failover_enabled"]}


@router.put("/routing-settings")
async def put_routing_settings(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Master on/off switch for cross-endpoint retry/failover. When off, the
    registry only ever tries the first (primary) endpoint of any chain —
    per-provider `max_retries` still governs retry count while this is on."""
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if "failover_enabled" not in payload:
        return _invalid("Field 'failover_enabled' is required.")
    enabled = bool(payload["failover_enabled"])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE ai_routing_settings SET failover_enabled = $1, updated_at = now() WHERE id",
            enabled,
        )
    await audit(
        pool, actor="operator", action="ai.routing_settings_update",
        detail={"failover_enabled": enabled},
    )
    _invalidate_registry()
    return {"failover_enabled": enabled}


# --------------------------------------------------------------------------- #
# Pricing                                                                      #
# --------------------------------------------------------------------------- #
@router.get("/pricing")
async def get_pricing(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM pricing_settings WHERE id")
    from acip_billing.pricing import parse_pricing_row

    cfg = parse_pricing_row(row)
    return {
        "usd_per_credit": cfg.usd_per_credit,
        "margin_percent": cfg.margin_percent,
        "search_credits": cfg.search_credits,
        "local_input_usd_per_1m": cfg.local_input_usd_per_1m,
        "local_output_usd_per_1m": cfg.local_output_usd_per_1m,
    }


@router.put("/pricing")
async def put_pricing(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    fields: dict[str, float] = {}
    bounds = {
        "usd_per_credit": (1e-9, 1000.0),
        "margin_percent": (0.0, 1000.0),
        "search_credits": (0.0, 1000.0),
        "local_input_usd_per_1m": (0.0, 100000.0),
        "local_output_usd_per_1m": (0.0, 100000.0),
    }
    for key, (lo, hi) in bounds.items():
        if key in payload:
            try:
                val = float(payload[key])
            except (TypeError, ValueError):
                return _invalid(f"Field '{key}' must be a number.")
            if not (lo <= val <= hi):
                return _invalid(f"Field '{key}' must be between {lo} and {hi}.")
            fields[key] = val
    if not fields:
        return _invalid("No editable fields provided.")
    sets = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(fields))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE pricing_settings SET {sets}, updated_at = now() WHERE id",  # noqa: S608
            *fields.values(),
        )
    await audit(pool, actor="operator", action="ai.pricing_update", detail=fields)
    _invalidate_registry()
    return await get_pricing(x_admin_token, authorization, vitrin_access)
