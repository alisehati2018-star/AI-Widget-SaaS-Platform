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
from acip_analytics import attribution as _attr
from acip_core.clients import get_pg_pool, get_redis
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter, Header

from ..deps import hash_key

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN = Header(default=None, alias="x-admin-token")


def _authorized(token: str | None) -> bool:
    expected = get_settings().admin_token
    # If no admin token is configured, the admin plane is closed by default.
    if not expected or not token:
        return False
    return secrets.compare_digest(token, expected)


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
    # The raw key is returned exactly once; only its hash is stored.
    return {"tenant_id": str(tenant_id), "slug": slug, "api_key": raw_key, "scope": scope}


@router.get("/analytics")
async def analytics(tenant: str, x_admin_token: str | None = _ADMIN):
    if not _authorized(x_admin_token):
        return _forbidden()
    pool = await get_pg_pool()
    redis = get_redis()
    from acip_core.clients import get_es_client

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
    from acip_core.clients import get_es_client

    return {"tenant_id": tenant, "terms": await _agg.zero_result_terms(get_es_client(), tenant)}


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
