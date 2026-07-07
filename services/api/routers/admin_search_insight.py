"""Admin surface — search analytics, the insight/analyst engine, synonym
curation, and the operator agent-test console (run search/chat as a tenant
without needing that tenant's own widget key)."""

from __future__ import annotations

import secrets
from typing import Any

from acip_analytics import aggregations as _agg
from acip_analytics import analyze as _analyze
from acip_analytics import attribution as _attr
from acip_analytics import why_summary as _why
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])


async def _es_or_default(coro, default):
    """Run an ES-backed analytics call; on any cluster/transport failure return
    (default, degraded=True) so the admin surface degrades instead of 500ing."""
    try:
        return await coro, False
    except Exception:  # noqa: BLE001 - ES down/unreachable must not crash admin
        return default, True


@router.get("/analytics")
async def analytics(
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    redis = get_redis()
    es = get_es_client()
    most_wanted, d1 = await _es_or_default(_agg.most_wanted(es, tenant), [])
    zero, d2 = await _es_or_default(_agg.zero_result_terms(es, tenant), [])
    funnel, d3 = await _es_or_default(_agg.funnel(es, tenant), {})
    return {
        "tenant_id": tenant,
        "four_dimensions": await _attr.four_dimension_summary(pool, redis, tenant),
        "most_wanted": most_wanted,
        "zero_results": zero,
        "funnel": funnel,
        "degraded": d1 or d2 or d3,
    }


@router.get("/zero-results")
async def zero_results(
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    terms, degraded = await _es_or_default(
        _agg.zero_result_terms(get_es_client(), tenant), []
    )
    return {"tenant_id": tenant, "terms": terms, "degraded": degraded}


@router.get("/insight")
async def insight(
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Insight 'why' engine (M10: REQ-M10-002): demand gaps + funnel drop-off."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    empty: dict[str, Any] = {
        "demand_gaps": [], "funnel": {}, "dropoffs": [],
        "biggest_dropoff": None, "headline": "",
    }
    result, degraded = await _es_or_default(_why(get_es_client(), tenant), empty)
    return {"tenant_id": tenant, "insight": result, "degraded": degraded}


@router.post("/analyst")
async def analyst(
    payload: dict[str, Any],
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """AI Business Analyst (M10: REQ-M10-003): NL question → grounded narration."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    question = str(payload.get("question", "")).strip()
    if not question:
        return error_response(422, "invalid_request", "Field 'question' is required.")
    from ..runtime import get_provider_chain

    result, degraded = await _es_or_default(
        _analyze(question, get_es_client(), tenant, providers=get_provider_chain()),
        {"answer": "", "grounding": None, "narrated_by": "none"},
    )
    return {"tenant_id": tenant, **result, "degraded": degraded}


def _syn_key(tenant: str) -> str:
    return f"synonyms:{tenant}"


@router.get("/synonyms")
async def get_synonyms(
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    redis = get_redis()
    raw = await redis.get(_syn_key(tenant)) if redis is not None else None
    return {"tenant_id": tenant, "synonyms": raw.splitlines() if raw else []}


@router.post("/synonyms")
async def set_synonyms(
    payload: dict[str, Any],
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    lines = payload.get("synonyms", [])
    if not isinstance(lines, list):
        return error_response(422, "invalid_request", "Field 'synonyms' must be a list.")
    redis = get_redis()
    if redis is not None:
        await redis.set(_syn_key(tenant), "\n".join(str(x) for x in lines))
    # Live reload of the ES updateable synonym set is exercised in validation
    # (deferred). The curated list is persisted here as the source of truth.
    return {"tenant_id": tenant, "count": len(lines), "status": "saved"}


@router.post("/agent/test")
async def agent_test(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Send a message to the grounded assistant as a specific tenant and return
    the full turn (answer, rung, citations, latency) for operator testing."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    tenant_id = str(payload.get("tenant_id", "")).strip()
    message = str(payload.get("message", "")).strip()
    if not tenant_id:
        return error_response(422, "invalid_request", "Field 'tenant_id' is required.")
    if not message:
        return error_response(422, "invalid_request", "Field 'message' is required.")
    session_id = str(payload.get("session_id") or f"admin-test-{secrets.token_hex(6)}")
    from ..runtime import get_assistant

    try:
        result = await get_assistant().answer(tenant_id, session_id, message)
    except Exception as exc:  # noqa: BLE001 - report failures back to the console
        return error_response(500, "agent_error", str(exc))
    return {"tenant_id": tenant_id, "session_id": session_id, **result}


@router.post("/agent/search")
async def agent_search(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Run a raw hybrid search for a tenant (inspect retrieval before chat)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    tenant_id = str(payload.get("tenant_id", "")).strip()
    query = str(payload.get("query", "")).strip()
    if not tenant_id or not query:
        return error_response(422, "invalid_request", "tenant_id and query are required.")
    from ..runtime import get_search_service

    try:
        result = await get_search_service().search(
            tenant_id, query, filters=payload.get("filters"), size=payload.get("size")
        )
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "search_error", str(exc))
    return {"tenant_id": tenant_id, **result}
