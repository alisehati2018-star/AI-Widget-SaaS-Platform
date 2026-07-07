"""Store-owner dashboard — search analytics, assistant status, live search
test, and synonym curation (tenant-scoped, degrade-safe when ES is down)."""

from __future__ import annotations

from typing import Any

from acip_analytics import aggregations as _agg
from acip_analytics import attribution as _attr
from acip_analytics import why_summary as _why
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


async def _es_or_default(coro, default):
    """Run an ES-backed call; on any cluster failure return (default, True) so
    the owner dashboard degrades gracefully instead of 500ing."""
    try:
        return await coro, False
    except Exception:  # noqa: BLE001 - ES down must not crash the dashboard
        return default, True


async def _tenant_docs(tenant_id: str) -> tuple[int | None, bool]:
    """(indexed-doc count, degraded). ``tenant_doc_count`` swallows errors and
    returns 0 (a missing index is a legitimate 0), so reachability must be
    probed separately — otherwise "cluster down" would masquerade as "empty"."""
    es = get_es_client()
    try:
        reachable = await es.ping()
    except Exception:  # noqa: BLE001
        reachable = False
    if not reachable:
        return None, True
    import acip_search.index_admin as ia

    return await ia.tenant_doc_count(es, tenant_id), False


@router.get("/analytics")
async def analytics(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    es = get_es_client()
    most_wanted, d1 = await _es_or_default(_agg.most_wanted(es, p.tenant_id), [])
    zero, d2 = await _es_or_default(_agg.zero_result_terms(es, p.tenant_id), [])
    funnel, d3 = await _es_or_default(_agg.funnel(es, p.tenant_id), {})
    return {
        "four_dimensions": await _attr.four_dimension_summary(pool, get_redis(), p.tenant_id),
        "most_wanted": most_wanted,
        "zero_results": zero,
        "funnel": funnel,
        "degraded": d1 or d2 or d3,
    }


@router.get("/insight")
async def insight(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    empty: dict[str, Any] = {
        "demand_gaps": [], "funnel": {}, "dropoffs": [],
        "biggest_dropoff": None, "headline": "",
    }
    result, degraded = await _es_or_default(_why(get_es_client(), p.tenant_id), empty)
    return {"insight": result, "degraded": degraded}


@router.get("/assistant-status")
async def assistant_status(
    authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """Owner-safe assistant health: is the platform flag on, is a local LLM
    configured, and is the store's catalogue searchable — WITHOUT exposing any
    internal URLs or infrastructure detail."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        flag = await conn.fetchval(
            "SELECT enabled FROM feature_flags WHERE key = 'assistant_enabled'"
        )
    s = get_settings()
    docs, degraded = await _tenant_docs(p.tenant_id)
    return {
        "assistant_enabled": bool(flag) if flag is not None else True,
        "llm_configured": bool(s.llm_url),
        "docs_indexed": docs,
        "search_degraded": degraded,
    }


@router.post("/search-test")
async def search_test(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """Live search test from the dashboard: runs the SAME hybrid retrieval the
    widget uses, scoped to the signed-in store. Degrades (200 + flag) when the
    search cluster is unreachable."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    query = str(payload.get("query", "")).strip()
    if not query:
        return error_response(422, "invalid_request", "Field 'query' is required.")
    try:
        size = min(50, max(1, int(payload.get("size") or 10)))
    except (TypeError, ValueError):
        size = 10
    from ..runtime import get_search_service

    try:
        result = await get_search_service().search(p.tenant_id, query, size=size)
    except Exception:  # noqa: BLE001 - ES down: degrade, don't crash
        return {"query": query, "results": [], "total": 0, "degraded": True}
    return {"query": query, **result, "degraded": False}


def _syn_key(tenant: str) -> str:
    return f"synonyms:{tenant}"


@router.get("/synonyms")
async def get_synonyms(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    redis = get_redis()
    raw = await redis.get(_syn_key(p.tenant_id)) if redis is not None else None
    return {"synonyms": raw.splitlines() if raw else []}


@router.post("/synonyms")
async def set_synonyms(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    lines = payload.get("synonyms", [])
    if not isinstance(lines, list):
        return error_response(422, "invalid_request", "Field 'synonyms' must be a list.")
    redis = get_redis()
    if redis is not None:
        await redis.set(_syn_key(p.tenant_id), "\n".join(str(x) for x in lines))
    return {"count": len(lines), "status": "saved"}


@router.get("/zero-results")
async def zero_results(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    terms, degraded = await _es_or_default(
        _agg.zero_result_terms(get_es_client(), p.tenant_id), []
    )
    return {"terms": terms, "degraded": degraded}
