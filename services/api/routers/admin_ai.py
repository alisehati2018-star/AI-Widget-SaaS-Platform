"""AI provider / pricing / finance management (operator plane).

Everything the operator needs to run a profitable multi-provider AI business:

* ``/admin/ai/providers`` (+ models) — CRUD over the vendor registry with each
  model's real per-1M-token provider cost. API keys are write-only (masked on
  every read).
* ``/admin/ai/routes`` — the ordered model chain per task ('chat', 'analyst');
  changes apply live through the gateway registry's TTL cache.
* ``/admin/ai/pricing`` — credit value, platform margin, flat search price and
  local-model cost attribution.
* ``/admin/ai/finance`` — the profit view: credits consumed (revenue value at
  the configured credit price) vs actual provider COGS, by day / model /
  tenant.

Same auth model as the rest of the admin plane (operator token or admin JWT).
"""

from __future__ import annotations

import re
from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter, Cookie, Header

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_admin_access")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_TASKS = ("chat", "analyst")


async def _ok(token, authorization, cookie) -> bool:
    from .admin import _admin_ok

    return await _admin_ok(token, authorization, cookie)


def _forbidden():
    return error_response(401, "unauthorized", "A valid x-admin-token is required.")


def _not_found():
    return error_response(404, "not_found", "No such resource.")


def _invalid(msg: str):
    return error_response(422, "invalid_request", msg)


def _mask(key: str | None) -> str:
    if not key:
        return ""
    return f"…{key[-4:]}" if len(key) > 4 else "…"


def _invalidate_registry() -> None:
    """Make routing/pricing changes visible to the gateway immediately."""
    from ..runtime import get_provider_registry

    get_provider_registry().invalidate()


def _provider_row(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "name": r["name"],
        "kind": r["kind"],
        "base_url": r["base_url"],
        "api_key_masked": _mask(r["api_key"]),
        "has_api_key": bool(r["api_key"]),
        "is_local": r["is_local"],
        "enabled": r["enabled"],
        "timeout_s": float(r["timeout_s"]),
        "notes": r["notes"],
    }


def _model_row(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "provider_id": str(r["provider_id"]),
        "model": r["model"],
        "label": r["label"],
        "input_usd_per_1m": float(r["input_usd_per_1m"]),
        "output_usd_per_1m": float(r["output_usd_per_1m"]),
        "enabled": r["enabled"],
    }


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
            "SELECT r.task, r.position, r.model_id, m.model, p.name AS provider, p.is_local "
            "FROM ai_routes r JOIN ai_models m ON m.id = r.model_id "
            "JOIN ai_providers p ON p.id = m.provider_id ORDER BY r.task, r.position"
        )
    routes: dict[str, list[dict]] = {task: [] for task in _TASKS}
    for r in rows:
        routes.setdefault(r["task"], []).append(
            {
                "model_id": str(r["model_id"]),
                "model": r["model"],
                "provider": r["provider"],
                "is_local": r["is_local"],
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
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            known = {
                str(r["id"])
                for r in await conn.fetch(
                    "SELECT id FROM ai_models WHERE id = ANY($1::uuid[])", model_ids
                )
            }
            missing = [m for m in model_ids if m not in known]
            if missing:
                return _invalid("Unknown model id(s) in 'model_ids'.")
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


# --------------------------------------------------------------------------- #
# Finance (profit view)                                                        #
# --------------------------------------------------------------------------- #
@router.get("/finance")
async def finance(
    days: int = 30,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Profit view over a window: what tenants consumed (credits, valued at
    the configured credit price) vs what the platform actually paid providers
    (COGS), broken down by day, model and tenant."""
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    days = max(1, min(days, 365))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        pricing_row = await conn.fetchrow("SELECT * FROM pricing_settings WHERE id")
        totals = await conn.fetchrow(
            "SELECT COALESCE(sum(cost), 0) AS credits, "
            "COALESCE(sum(provider_cost), 0) AS cogs, count(*) AS calls "
            "FROM usage_events WHERE occurred_at >= now() - ($1 || ' days')::interval",
            str(days),
        )
        by_day = await conn.fetch(
            "SELECT date_trunc('day', occurred_at)::date AS day, "
            "COALESCE(sum(cost), 0) AS credits, COALESCE(sum(provider_cost), 0) AS cogs "
            "FROM usage_events WHERE occurred_at >= now() - ($1 || ' days')::interval "
            "GROUP BY 1 ORDER BY 1",
            str(days),
        )
        by_model = await conn.fetch(
            "SELECT COALESCE(provider, '—') AS provider, COALESCE(model, '—') AS model, "
            "count(*) AS calls, COALESCE(sum(tokens_in), 0) AS tokens_in, "
            "COALESCE(sum(tokens_out), 0) AS tokens_out, "
            "COALESCE(sum(cost), 0) AS credits, COALESCE(sum(provider_cost), 0) AS cogs "
            "FROM usage_events WHERE occurred_at >= now() - ($1 || ' days')::interval "
            "AND rung IN ('local', 'frontier') "
            "GROUP BY 1, 2 ORDER BY cogs DESC, credits DESC LIMIT 20",
            str(days),
        )
        by_tenant = await conn.fetch(
            "SELECT t.name, t.slug, count(*) AS calls, "
            "COALESCE(sum(u.cost), 0) AS credits, "
            "COALESCE(sum(u.provider_cost), 0) AS cogs "
            "FROM usage_events u JOIN tenants t ON t.id = u.tenant_id "
            "WHERE u.occurred_at >= now() - ($1 || ' days')::interval "
            "GROUP BY t.id ORDER BY credits DESC LIMIT 10",
            str(days),
        )
        revenue = await conn.fetch(
            "SELECT currency, COALESCE(sum(amount), 0) AS amount FROM invoices "
            "WHERE status = 'paid' AND created_at >= now() - ($1 || ' days')::interval "
            "GROUP BY currency",
            str(days),
        )
    from acip_billing.pricing import parse_pricing_row

    cfg = parse_pricing_row(pricing_row)
    credits = float(totals["credits"])
    cogs = float(totals["cogs"])
    value_usd = credits * cfg.usd_per_credit
    return {
        "days": days,
        "usd_per_credit": cfg.usd_per_credit,
        "margin_percent": cfg.margin_percent,
        "credits_consumed": credits,
        "consumption_value_usd": value_usd,
        "provider_cost_usd": cogs,
        "gross_margin_usd": value_usd - cogs,
        "calls": int(totals["calls"]),
        "billed_revenue": [
            {"currency": r["currency"], "amount": float(r["amount"])} for r in revenue
        ],
        "by_day": [
            {
                "day": r["day"].isoformat(),
                "credits": float(r["credits"]),
                "cogs_usd": float(r["cogs"]),
            }
            for r in by_day
        ],
        "by_model": [
            {
                "provider": r["provider"],
                "model": r["model"],
                "calls": int(r["calls"]),
                "tokens_in": int(r["tokens_in"]),
                "tokens_out": int(r["tokens_out"]),
                "credits": float(r["credits"]),
                "cogs_usd": float(r["cogs"]),
            }
            for r in by_model
        ],
        "by_tenant": [
            {
                "name": r["name"],
                "slug": r["slug"],
                "calls": int(r["calls"]),
                "credits": float(r["credits"]),
                "cogs_usd": float(r["cogs"]),
            }
            for r in by_tenant
        ],
    }
