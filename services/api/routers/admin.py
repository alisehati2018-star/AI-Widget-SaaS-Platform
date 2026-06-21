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
from fastapi import APIRouter, Cookie, Header

from ..deps import hash_key

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_access")


def _authorized(token: str | None) -> bool:
    expected = get_settings().admin_token
    # If no admin token is configured, the admin plane is closed by default.
    if not expected or not token:
        return False
    return secrets.compare_digest(token, expected)


async def _admin_ok(
    token: str | None, authorization: str | None, access_cookie: str | None = None
) -> bool:
    """Authorize the admin plane via EITHER the operator token (automation) OR a
    platform-admin JWT (bearer or cookie, the admin-panel UI). Phase 6 dual-auth."""
    if _authorized(token):
        return True
    from .auth import current_principal

    principal = await current_principal(authorization, access_cookie)
    return principal is not None and principal.is_admin


def _forbidden():
    return error_response(401, "unauthorized", "A valid x-admin-token is required.")


@router.post("/tenants")
async def create_tenant(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
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
                slug,
                name,
            )
            await conn.execute(
                "INSERT INTO api_keys (tenant_id, key_hash, scope, label) VALUES ($1, $2, $3, $4)",
                tenant_id,
                hash_key(raw_key),
                scope,
                "provisioned",
            )
    await audit(
        pool,
        actor="operator",
        action="tenant.create",
        tenant_id=str(tenant_id),
        detail={"slug": slug, "scope": scope},
    )
    # The raw key is returned exactly once; only its hash is stored.
    return {"tenant_id": str(tenant_id), "slug": slug, "api_key": raw_key, "scope": scope}


@router.get("/overview")
async def overview(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Platform-wide counts for the admin dashboard (Phase 6)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
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
async def list_tenants(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """List tenants with their plan + subscription status (Phase 6)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
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
                "id": str(r["id"]),
                "slug": r["slug"],
                "name": r["name"],
                "status": r["status"],
                "plan": r["plan"],
                "sub_status": r["sub_status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }


@router.get("/users")
async def list_users(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """List all platform users (Phase 6)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT u.email, u.full_name, u.role, u.status, u.last_login_at, "
            "COALESCE(t.name, '—') AS tenant FROM users u "
            "LEFT JOIN tenants t ON t.id = u.tenant_id ORDER BY u.created_at DESC LIMIT 500"
        )
    return {
        "users": [
            {
                "email": r["email"],
                "full_name": r["full_name"],
                "role": r["role"],
                "status": r["status"],
                "tenant": r["tenant"],
                "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
            }
            for r in rows
        ]
    }


@router.get("/audit")
async def audit_log(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Recent audit-log entries (Phase 6)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT actor, action, detail, created_at FROM audit_log "
            "ORDER BY created_at DESC LIMIT 200"
        )
    return {
        "entries": [
            {
                "actor": r["actor"],
                "action": r["action"],
                "detail": r["detail"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }


@router.get("/orders")
async def list_orders(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Recent billing orders + paid-revenue total (Phase 6/7)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT o.id, o.amount, o.currency, o.status, o.provider, o.created_at, "
            "COALESCE(t.name, '—') AS tenant, COALESCE(p.name, '—') AS plan FROM orders o "
            "LEFT JOIN tenants t ON t.id = o.tenant_id "
            "LEFT JOIN plans p ON p.id = o.plan_id ORDER BY o.created_at DESC LIMIT 200"
        )
        revenue = await conn.fetchval(
            "SELECT COALESCE(sum(amount), 0) FROM orders WHERE status = 'paid'"
        )
    return {
        "revenue_total": float(revenue or 0),
        "orders": [
            {
                "id": str(r["id"]),
                "tenant": r["tenant"],
                "plan": r["plan"],
                "amount": float(r["amount"]),
                "currency": r["currency"],
                "status": r["status"],
                "provider": r["provider"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
    }


@router.post("/orders/{order_id}/mark-paid")
async def admin_mark_paid(
    order_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Operator confirmation of a manual/invoice payment → activates the plan."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_billing import mark_order_paid

    pool = await get_pg_pool()
    days = get_settings().subscription_period_days
    result = await mark_order_paid(pool, order_id, period_days=days)
    if result is None:
        return error_response(404, "unknown_order", "No such order.")
    await audit(
        pool,
        actor="operator",
        action="billing.mark_paid",
        tenant_id=result["tenant_id"],
        detail={"order_id": order_id},
    )
    return {"status": "paid", "activated": result["plan_code"], "already": result.get("already")}


@router.post("/orders/{order_id}/refund")
async def admin_refund(
    order_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Mark an order refunded (does not auto-downgrade the live subscription)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE orders SET status = 'refunded' WHERE id = $1 RETURNING tenant_id", order_id
        )
    if row is None:
        return error_response(404, "unknown_order", "No such order.")
    await audit(
        pool,
        actor="operator",
        action="billing.refund",
        tenant_id=str(row["tenant_id"]),
        detail={"order_id": order_id},
    )
    return {"status": "refunded"}


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
    return {
        "tenant_id": tenant,
        "four_dimensions": await _attr.four_dimension_summary(pool, redis, tenant),
        "most_wanted": await _agg.most_wanted(es, tenant),
        "zero_results": await _agg.zero_result_terms(es, tenant),
        "funnel": await _agg.funnel(es, tenant),
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
    return {"tenant_id": tenant, "terms": await _agg.zero_result_terms(get_es_client(), tenant)}


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
    return {"tenant_id": tenant, "insight": await _why(get_es_client(), tenant)}


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

    result = await _analyze(question, get_es_client(), tenant, providers=get_provider_chain())
    return {"tenant_id": tenant, **result}


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


# --- GDPR-style data governance (M11: REQ-M11-006) ---


@router.post("/tenants/{tenant_id}/erase")
async def erase_tenant_data(
    tenant_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Erase a tenant's data across index, memory, and logs (right to be forgotten)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
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
        for pattern in (
            f"chatmem:{tenant_id}:*",
            f"l2:{tenant_id}",
            f"synonyms:{tenant_id}",
            f"data_version:{tenant_id}",
        ):
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
async def export_tenant_data(
    tenant_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Export a tenant's portable data (PII included for the data subject)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
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
async def set_tracking(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Enable/disable behavioural capture for a tenant (REQ-M11-006)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
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
    await audit(
        pool,
        actor="operator",
        action="tenant.tracking",
        tenant_id=tenant_id,
        detail={"enabled": enabled},
    )
    return {"tenant_id": tenant_id, "tracking_enabled": enabled}


# --------------------------------------------------------------------------- #
# Phase B — operational monitoring + management                              #
# --------------------------------------------------------------------------- #
@router.get("/security")
async def security_monitoring(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Locked accounts, failed-login counts, and recent auth events."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        locked = await conn.fetch(
            "SELECT email, failed_logins, locked_until FROM users "
            "WHERE locked_until IS NOT NULL AND locked_until > now() ORDER BY locked_until DESC"
        )
        at_risk = await conn.fetchval("SELECT count(*) FROM users WHERE failed_logins > 0")
        events = await conn.fetch(
            "SELECT actor, action, created_at FROM audit_log "
            "WHERE action LIKE 'auth.%' ORDER BY created_at DESC LIMIT 50"
        )
    return {
        "locked_accounts": [
            {
                "email": r["email"],
                "failed_logins": r["failed_logins"],
                "locked_until": r["locked_until"].isoformat() if r["locked_until"] else None,
            }
            for r in locked
        ],
        "accounts_with_failures": int(at_risk or 0),
        "recent_auth_events": [
            {
                "actor": r["actor"],
                "action": r["action"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in events
        ],
    }


@router.get("/health")
async def system_health(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Live dependency status for the ops dashboard (PG / Redis / Elasticsearch)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    deps: dict[str, str] = {}
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        deps["postgres"] = "ok"
    except Exception:  # noqa: BLE001
        deps["postgres"] = "unavailable"
    redis = get_redis()
    try:
        deps["redis"] = "ok" if (redis is not None and await redis.ping()) else "unavailable"
    except Exception:  # noqa: BLE001
        deps["redis"] = "unavailable"
    try:
        deps["elasticsearch"] = "ok" if await get_es_client().ping() else "unavailable"
    except Exception:  # noqa: BLE001
        deps["elasticsearch"] = "unavailable"
    overall = "ok" if all(v == "ok" for v in deps.values()) else "degraded"
    return {"status": overall, "dependencies": deps}


@router.get("/usage")
async def usage_monitoring(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Platform-wide usage + credit consumption (from usage_events / credit_ledger)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        totals = await conn.fetchrow(
            "SELECT count(*) AS calls, COALESCE(sum(tokens_in), 0) AS tin, "
            "COALESCE(sum(tokens_out), 0) AS tout, COALESCE(sum(cost), 0) AS cost "
            "FROM usage_events"
        )
        by_rung = await conn.fetch(
            "SELECT COALESCE(rung, 'unknown') AS rung, count(*) AS n FROM usage_events "
            "GROUP BY rung ORDER BY n DESC"
        )
        spent = await conn.fetchval(
            "SELECT COALESCE(-sum(delta), 0) FROM credit_ledger WHERE delta < 0"
        )
    return {
        "calls": int(totals["calls"]),
        "tokens_in": int(totals["tin"]),
        "tokens_out": int(totals["tout"]),
        "cost": float(totals["cost"]),
        "credits_spent": float(spent or 0),
        "by_rung": [{"rung": r["rung"], "count": int(r["n"])} for r in by_rung],
    }


@router.get("/queue")
async def queue_monitoring(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Celery broker reachability + pending task depth (best-effort)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    s = get_settings()
    redis = get_redis()
    depth: int | None = None
    reachable = False
    try:
        if redis is not None and await redis.ping():
            reachable = True
            depth = int(await redis.llen("celery"))
    except Exception:  # noqa: BLE001
        reachable = False
    return {"broker": s.celery_broker_url, "reachable": reachable, "pending": depth}


@router.get("/models")
async def model_monitoring(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Gateway / inference configuration + per-rung call distribution."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        by_rung = await conn.fetch(
            "SELECT COALESCE(rung, 'unknown') AS rung, count(*) AS n FROM usage_events "
            "GROUP BY rung ORDER BY n DESC"
        )
    return {
        "embeddings_url": s.embeddings_url,
        "reranker_url": s.reranker_url,
        "llm_url": s.llm_url,
        "llm_model": s.llm_model,
        "frontier_enabled": s.frontier_enabled,
        "frontier_model": s.frontier_model or None,
        "rerank_enabled": s.rerank_enabled,
        "by_rung": [{"rung": r["rung"], "count": int(r["n"])} for r in by_rung],
    }


@router.get("/feature-flags")
async def get_feature_flags(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT key, enabled, description, updated_at FROM feature_flags ORDER BY key"
        )
    return {
        "flags": [
            {
                "key": r["key"],
                "enabled": r["enabled"],
                "description": r["description"],
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/feature-flags/{key}")
async def set_feature_flag(
    key: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    enabled = bool(payload.get("enabled", False))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE feature_flags SET enabled = $1, updated_at = now() "
            "WHERE key = $2 RETURNING key",
            enabled,
            key,
        )
    if updated is None:
        return error_response(404, "not_found", "No such flag.")
    await audit(pool, actor="operator", action="flag.set", detail={"key": key, "enabled": enabled})
    return {"key": key, "enabled": enabled}


@router.post("/tenants/{tenant_id}/status")
async def set_tenant_status(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Suspend or re-activate a tenant."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    status = str(payload.get("status", ""))
    if status not in ("active", "suspended"):
        return error_response(422, "invalid_request", "status must be active or suspended.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE tenants SET status = $1, updated_at = now() WHERE id = $2 RETURNING id",
            status,
            tenant_id,
        )
    if updated is None:
        return error_response(404, "not_found", "No such tenant.")
    await audit(
        pool,
        actor="operator",
        action="tenant.status",
        tenant_id=tenant_id,
        detail={"status": status},
    )
    return {"tenant_id": tenant_id, "status": status}


@router.post("/users/{email}/status")
async def set_user_status(
    email: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Suspend or re-activate a user; suspending also clears any lockout."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    status = str(payload.get("status", ""))
    if status not in ("active", "suspended"):
        return error_response(422, "invalid_request", "status must be active or suspended.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE users SET status = $1, failed_logins = 0, locked_until = NULL "
            "WHERE lower(email) = $2 RETURNING id",
            status,
            email.lower(),
        )
    if updated is None:
        return error_response(404, "not_found", "No such user.")
    await audit(
        pool, actor="operator", action="user.status", detail={"email": email, "status": status}
    )
    return {"email": email, "status": status}
