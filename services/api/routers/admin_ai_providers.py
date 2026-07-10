"""AI provider registry CRUD (operator plane).

``/admin/ai/providers`` — CRUD over the vendor registry, each with its live
30-day platform usage (credits/cost/calls) and an external credit/key-health
check. API keys are write-only (masked on every read). Model CRUD lives in
``admin_ai_models.py``.
"""

from __future__ import annotations

from typing import Any

import httpx
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_gateway.provider_credit import check_provider_credit
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

_DISCOVER_KINDS = ("openai_compatible", "openrouter", "google", "bynara", "conduit")


async def _platform_usage_by_provider(conn, days: int = 30) -> dict[str, dict[str, Any]]:
    rows = await conn.fetch(
        "SELECT COALESCE(provider, '—') AS provider, count(*) AS calls, "
        "COALESCE(sum(cost), 0) AS credits, COALESCE(sum(provider_cost), 0) AS cost_usd "
        "FROM usage_events WHERE occurred_at >= now() - ($1 || ' days')::interval "
        "GROUP BY 1",
        str(days),
    )
    return {
        r["provider"]: {
            "period_days": days,
            "call_count": int(r["calls"]),
            "platform_credits": float(r["credits"]),
            "estimated_cost_usd": float(r["cost_usd"]),
        }
        for r in rows
    }


_EMPTY_USAGE = {
    "period_days": 30, "call_count": 0, "platform_credits": 0.0, "estimated_cost_usd": 0.0
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
        providers = await conn.fetch(
            "SELECT * FROM ai_providers ORDER BY priority DESC, created_at"
        )
        models = await conn.fetch("SELECT * FROM ai_models ORDER BY created_at")
        usage_by_name = await _platform_usage_by_provider(conn)
    by_provider: dict[str, list[dict]] = {}
    for m in models:
        by_provider.setdefault(str(m["provider_id"]), []).append(_model_row(m))
    out = []
    for p in providers:
        row = _provider_row(p)
        row["models"] = by_provider.get(row["id"], [])
        row["platform_usage"] = usage_by_name.get(p["name"], _EMPTY_USAGE)
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
    discover_kind = str(payload.get("discover_kind", "openai_compatible"))
    if discover_kind not in _DISCOVER_KINDS:
        return _invalid("discover_kind is not a known provider template kind.")
    try:
        max_retries = int(payload.get("max_retries", 0) or 0)
        retry_backoff_ms = int(payload.get("retry_backoff_ms", 250) or 250)
        priority = int(payload.get("priority", 0) or 0)
    except (TypeError, ValueError):
        return _invalid("max_retries/retry_backoff_ms/priority must be integers.")
    if not (0 <= max_retries <= 5):
        return _invalid("max_retries must be between 0 and 5.")
    if not (0 <= retry_backoff_ms <= 10000):
        return _invalid("retry_backoff_ms must be between 0 and 10000.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM ai_providers WHERE name = $1", name):
            return _invalid("A provider with this name already exists.")
        row = await conn.fetchrow(
            "INSERT INTO ai_providers (name, kind, base_url, api_key, is_local, enabled, "
            "timeout_s, notes, discover_kind, max_retries, retry_backoff_ms, priority) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING *",
            name,
            kind,
            base_url,
            str(payload.get("api_key", "") or ""),
            bool(payload.get("is_local", kind == "local")),
            bool(payload.get("enabled", True)),
            float(payload.get("timeout_s", 30) or 30),
            (str(payload.get("notes", "")).strip() or None),
            discover_kind,
            max_retries,
            retry_backoff_ms,
            priority,
        )
    await audit(pool, actor="operator", action="ai.provider_create", detail={"name": name})
    _invalidate_registry()
    row_out = _provider_row(row)
    row_out["models"] = []
    row_out["platform_usage"] = dict(_EMPTY_USAGE)
    return row_out


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
        ("discover_kind", str), ("max_retries", int), ("retry_backoff_ms", int),
        ("priority", int),
    ):
        if key in payload:
            fields[key] = cast(payload[key])
    if "discover_kind" in fields and fields["discover_kind"] not in _DISCOVER_KINDS:
        return _invalid("discover_kind is not a known provider template kind.")
    if "max_retries" in fields and not (0 <= fields["max_retries"] <= 5):
        return _invalid("max_retries must be between 0 and 5.")
    if "retry_backoff_ms" in fields and not (0 <= fields["retry_backoff_ms"] <= 10000):
        return _invalid("retry_backoff_ms must be between 0 and 10000.")
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
        if row is not None:
            usage_by_name = await _platform_usage_by_provider(conn)
            models_rows = await conn.fetch(
                "SELECT * FROM ai_models WHERE provider_id = $1 ORDER BY created_at", provider_id
            )
    if row is None:
        return _not_found()
    await audit(
        pool, actor="operator", action="ai.provider_update",
        detail={"id": provider_id, "fields": sorted(fields)},
    )
    _invalidate_registry()
    row_out = _provider_row(row)
    row_out["models"] = [_model_row(m) for m in models_rows]
    row_out["platform_usage"] = usage_by_name.get(row["name"], _EMPTY_USAGE)
    return row_out


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
        if not await conn.fetchval("SELECT 1 FROM ai_providers WHERE id = $1", provider_id):
            return _not_found()
        model_count = await conn.fetchval(
            "SELECT count(*) FROM ai_models WHERE provider_id = $1", provider_id
        )
        if model_count:
            return _invalid(
                f"This provider still has {model_count} model(s); delete or move them first."
            )
        deleted = await conn.fetchval(
            "DELETE FROM ai_providers WHERE id = $1 RETURNING name", provider_id
        )
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

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            await client.get(url)
        return {"reachable": True, "latency_ms": int((time.monotonic() - t0) * 1000)}
    except Exception:  # noqa: BLE001
        return {"reachable": False, "latency_ms": None}


@router.post("/providers/{provider_id}/check-credit")
async def check_credit(
    provider_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """External balance / key-health check, alongside this provider's
    internal 30-day platform usage (most vendors don't expose a balance API —
    see `packages/acip_gateway/provider_credit.py` for what degrades to a
    plain key-health check)."""
    if not await _ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _UUID_RE.match(provider_id):
        return _not_found()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        provider = await conn.fetchrow(
            "SELECT name, base_url, api_key, discover_kind FROM ai_providers WHERE id = $1",
            provider_id,
        )
        if provider is None:
            return _not_found()
        usage_by_name = await _platform_usage_by_provider(conn)
    if not provider["api_key"]:
        return _invalid("This provider has no API key configured.")
    try:
        credit = await check_provider_credit(
            base_url=provider["base_url"],
            api_key=provider["api_key"],
            discover_kind=provider["discover_kind"],
        )
    except httpx.HTTPError as exc:
        return _invalid(f"Credit check failed: {exc}")
    return {
        "credit": credit,
        "platform_usage": usage_by_name.get(provider["name"], _EMPTY_USAGE),
    }
