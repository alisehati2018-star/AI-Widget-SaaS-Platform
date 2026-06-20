"""Operator/admin API surface (blueprint §12, M9 + M11 control plane).

The admin plane is **auth-separated** from tenant APIs (§9.2): every endpoint
requires the operator token (`x-admin-token`), distinct from tenant API keys.
Phase 2 implements tenant/key provisioning, the analytics surfaces (four-
dimension summary, most-wanted, zero-result view), and tenant synonym
management. Full least-privilege RBAC + audit hardening is Phase 3 (M11).
"""

from __future__ import annotations

import secrets
from typing import Any

from acip_analytics import aggregations as _agg
from acip_analytics import analyze as _analyze
from acip_analytics import attribution as _attr
from acip_analytics import why_summary as _why
from acip_core.audit import audit
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter, Header

from ..deps import hash_key

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")


def _authorized(token: str | None) -> bool:
    expected = get_settings().admin_token
    # If no admin token is configured, the admin plane is closed by default.
    if not expected or not token:
        return False
    return secrets.compare_digest(token, expected)


async def _admin_ok(token: str | None, authorization: str | None) -> bool:
    """Authorize the admin plane via EITHER the operator token (automation) OR a
    platform-admin bearer JWT (the admin-panel UI). Phase 6 dual-auth."""
    if _authorized(token):
        return True
    from .auth import current_principal

    principal = await current_principal(authorization)
    return principal is not None and principal.is_admin


def _forbidden():
    return error_response(401, "unauthorized", "A valid x-admin-token is required.")


@router.post("/tenants")
async def create_tenant(payload: dict[str, Any], x_admin_token: str | None = _ADMIN):
    if not _authorized(x_admin_token):
        return _forbidden()
    slug = str(payload.get("slug", "")).strip()
    name = str(payload.get("name", slug)).strip()
    scope = str(payload.get("scope", "widget"))
    if not slug:
        return error_response(422, "invalid_request", "Field 'slug' is required.")
    raw_key = "acip_" + secrets.token_urlsafe(24)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            tenant_id = await conn.fetchval(
                "INSERT INTO tenants (slug, name) VALUES ($1, $2) "
                "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                slug, name,
            )
            await conn.execute(
                "INSERT INTO api_keys (tenant_id, key_hash, scope, label) "
                "VALUES ($1, $2, $3, $4)",
                tenant_id, hash_key(raw_key), scope, "provisioned",
            )
    await audit(pool, actor="operator", action="tenant.create", tenant_id=str(tenant_id),
                detail={"slug": slug, "scope": scope})
    # The raw key is returned exactly once; only its hash is stored.
    return {"tenant_id": str(tenant_id), "slug": slug, "api_key": raw_key, "scope": scope}


@router.get("/overview")
async def overview(x_admin_token: str | None = _ADMIN, authorization: str | None = _AUTHZ):
    """Platform-wide counts for the admin dashboard (Phase 6)."""
    if not await _admin_ok(x_admin_token, authorization):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        tenants = await conn.fetchval("SELECT count(*) FROM tenants")
        users = await conn.fetchval("SELECT count(*) FROM users")
        active_subs = await conn.fetchval(
            "SELECT count(*) FROM subscriptions WHERE status IN ('active', 'trialing')"
        )
        mrr = await conn.fetchval(
            "SELECT COALESCE(sum(p.price_monthly), 0) FROM subscriptions s "
            "JOIN plans p ON p.id = s.plan_id WHERE s.status = 'active'"
        )
    return {
        "tenants": int(tenants or 0),
        "users": int(users or 0),
        "active_subscriptions": int(active_subs or 0),
        "mrr": float(mrr or 0),
    }


@router.get("/tenants")
async def list_tenants(x_admin_token: str | None = _ADMIN, authorization: str | None = _AUTHZ):
    """List tenants with their plan + subscription status (Phase 6)."""
    if not await _admin_ok(x_admin_token, authorization):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT t.id, t.slug, t.name, t.status, t.created_at, "
            "COALESCE(p.name, '—') AS plan, COALESCE(s.status, 'none') AS sub_status "
            "FROM tenants t "
            "LEFT JOIN subscriptions s ON s.tenant_id = t.id "
            "LEFT JOIN plans p ON p.id = s.plan_id "
            "ORDER BY t.created_at DESC LIMIT 200"
        )
    return {
        "tenants": [
            {
                "id": str(r["id"]), "slug": r["slug"], "name": r["name"],
                "status": r["status"], "plan": r["plan"], "sub_status": r["sub_status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }


@router.get("/analytics")
async def analytics(tenant: str, x_admin_token: str | None = _ADMIN):
    if not _authorized(x_admin_token):
        return _forbidden()
    pool = await get_pg_pool()
    redis = get_redis()
    es = get_es_client()
    return {
        "tenant_id": tenant,
        "four_dimensions": await _attr.four_dimension_summary(pool, redis, tenant),
        "most_wanted": await _agg.most_wanted(es, tenant),
        "zero_results": await _agg.zero_result_terms(es, tenant),
        "funnel": await _agg.funnel(es, tenant),
    }


@router.get("/zero-results")
async def zero_results(tenant: str, x_admin_token: str | None = _ADMIN):
    if not _authorized(x_admin_token):
        return _forbidden()
    return {"tenant_id": tenant, "terms": await _agg.zero_result_terms(get_es_client(), tenant)}


@router.get("/insight")
async def insight(tenant: str, x_admin_token: str | None = _ADMIN):
    """Insight 'why' engine (M10: REQ-M10-002): demand gaps + funnel drop-off."""
    if not _authorized(x_admin_token):
        return _forbidden()
    return {"tenant_id": tenant, "insight": await _why(get_es_client(), tenant)}


@router.post("/analyst")
async def analyst(payload: dict[str, Any], tenant: str, x_admin_token: str | None = _ADMIN):
    """AI Business Analyst (M10: REQ-M10-003): NL question → grounded narration."""
    if not _authorized(x_admin_token):
        return _forbidden()
    question = str(payload.get("question", "")).strip()
    if not question:
        return error_response(422, "invalid_request", "Field 'question' is required.")
    from ..runtime import get_provider_chain

    result = await _analyze(question, get_es_client(), tenant, providers=get_provider_chain())
    return {"tenant_id": tenant, **result}


def _syn_key(tenant: str) -> str:
    return f"synonyms:{tenant}"


@router.get("/synonyms")
async def get_synonyms(tenant: str, x_admin_token: str | None = _ADMIN):
    if not _authorized(x_admin_token):
        return _forbidden()
    redis = get_redis()
    raw = await redis.get(_syn_key(tenant)) if redis is not None else None
    return {"tenant_id": tenant, "synonyms": raw.splitlines() if raw else []}


@router.post("/synonyms")
async def set_synonyms(payload: dict[str, Any], tenant: str, x_admin_token: str | None = _ADMIN):
    if not _authorized(x_admin_token):
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


# --- GDPR-style data governance (M11: REQ-M11-006) ---


@router.post("/tenants/{tenant_id}/erase")
async def erase_tenant_data(tenant_id: str, x_admin_token: str | None = _ADMIN):
    """Erase a tenant's data across index, memory, and logs (right to be forgotten)."""
    if not _authorized(x_admin_token):
        return _forbidden()
    s = get_settings()
    es = get_es_client()
    erased: dict[str, Any] = {}
    query = {"query": {"term": {"tenant_id": tenant_id}}}
    for index in (s.catalogue_alias, f"{s.es_index_prefix}-chatmem", f"{s.es_index_prefix}-events"):
        try:
            await es.delete_by_query(index=index, body=query, conflicts="proceed")
            erased[index] = "ok"
        except Exception:  # noqa: BLE001 - index may not exist yet
            erased[index] = "skipped"
    redis = get_redis()
    if redis is not None:
        for pattern in (f"chatmem:{tenant_id}:*", f"l2:{tenant_id}", f"synonyms:{tenant_id}",
                        f"data_version:{tenant_id}"):
            try:
                async for key in redis.scan_iter(match=pattern):
                    await redis.delete(key)
            except Exception:  # noqa: BLE001
                pass
    pool = await get_pg_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM leads WHERE tenant_id = $1", tenant_id)
    except Exception:  # noqa: BLE001
        pass
    await audit(pool, actor="operator", action="tenant.erase", tenant_id=tenant_id, detail=erased)
    return {"tenant_id": tenant_id, "erased": erased, "status": "erased"}


@router.get("/tenants/{tenant_id}/export")
async def export_tenant_data(tenant_id: str, x_admin_token: str | None = _ADMIN):
    """Export a tenant's portable data (PII included for the data subject)."""
    if not _authorized(x_admin_token):
        return _forbidden()
    pool = await get_pg_pool()
    leads: list[dict[str, Any]] = []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT email, phone, has_intent, source, created_at "
                "FROM leads WHERE tenant_id = $1",
                tenant_id,
            )
            leads = [dict(r) for r in rows]
    except Exception:  # noqa: BLE001
        leads = []
    return {"tenant_id": tenant_id, "leads": leads}


@router.post("/tenants/{tenant_id}/tracking")
async def set_tracking(tenant_id: str, payload: dict[str, Any], x_admin_token: str | None = _ADMIN):
    """Enable/disable behavioural capture for a tenant (REQ-M11-006)."""
    if not _authorized(x_admin_token):
        return _forbidden()
    enabled = bool(payload.get("enabled", True))
    pool = await get_pg_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE tenants SET tracking_enabled = $1 WHERE id = $2", enabled, tenant_id
            )
    except Exception:  # noqa: BLE001
        pass
    await audit(pool, actor="operator", action="tenant.tracking", tenant_id=tenant_id,
                detail={"enabled": enabled})
    return {"tenant_id": tenant_id, "tracking_enabled": enabled}
