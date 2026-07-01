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
            "SELECT u.email, u.full_name, u.role, u.status, u.last_login_at, u.tenant_id, "
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
                "has_tenant": r["tenant_id"] is not None,
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

    from .billing import _email_invoice

    pool = await get_pg_pool()
    days = get_settings().subscription_period_days
    result = await mark_order_paid(pool, order_id, period_days=days)
    if result is None:
        return error_response(404, "unknown_order", "No such order.")
    if not result.get("already"):
        await _email_invoice(pool, result)
    await audit(
        pool,
        actor="operator",
        action="billing.mark_paid",
        tenant_id=result["tenant_id"],
        detail={"order_id": order_id, "kind": result["kind"]},
    )
    return {
        "status": "paid",
        "kind": result["kind"],
        "activated": result.get("plan_code"),
        "invoice_number": result.get("invoice_number"),
        "already": result.get("already"),
    }


@router.post("/billing/run-renewals")
async def run_renewals(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Period-end processing: downgrade cancelled subs, mark others past_due."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_billing import process_renewals

    pool = await get_pg_pool()
    result = await process_renewals(pool, trial_plan_code=get_settings().trial_plan_code)
    await audit(pool, actor="operator", action="billing.run_renewals", detail=result)
    return result


@router.post("/billing/run-dunning")
async def run_dunning(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Email every past-due subscription a payment reminder."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_billing import list_past_due
    from acip_notify import dunning_email, send_email

    pool = await get_pg_pool()
    due = await list_past_due(pool)
    sent = 0
    for row in due:
        if row["email"]:
            subject, text, html = dunning_email(
                row["plan"] or "your plan", row["amount"], row["currency"] or "USD"
            )
            await send_email(row["email"], subject, text, html)
            sent += 1
    await audit(
        pool,
        actor="operator",
        action="billing.run_dunning",
        detail={"past_due": len(due), "emailed": sent},
    )
    return {"past_due": len(due), "emailed": sent}


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


@router.post("/users/{email}/role")
async def set_user_role(
    email: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Change a user's platform role. Promoting to platform_admin clears their
    tenant (a platform admin owns no single tenant); demoting a platform_admin
    to a store role requires them to already have a tenant on record."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    role = str(payload.get("role", ""))
    if role not in ("platform_admin", "store_owner", "store_staff"):
        return error_response(
            422, "invalid_request", "role must be platform_admin, store_owner, or store_staff."
        )
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, tenant_id FROM users WHERE lower(email) = $1", email.lower()
        )
        if row is None:
            return error_response(404, "not_found", "No such user.")
        if role == "platform_admin":
            await conn.execute(
                "UPDATE users SET role = $1, tenant_id = NULL WHERE id = $2", role, row["id"]
            )
        else:
            if row["tenant_id"] is None:
                return error_response(
                    422, "no_tenant", "This user has no tenant to assign a store role to."
                )
            await conn.execute("UPDATE users SET role = $1 WHERE id = $2", role, row["id"])
    await audit(pool, actor="operator", action="user.role", detail={"email": email, "role": role})
    return {"email": email, "role": role}


# --------------------------------------------------------------------------- #
# Elasticsearch control panel (M2/M9) — operator-plane index management.       #
# Non-destructive reads + guarded create/reindex/alias/delete operations so an #
# operator can fully control the cluster from the admin dashboard.             #
# --------------------------------------------------------------------------- #
@router.get("/es/health")
async def es_health(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_search import index_admin as ia

    es = get_es_client()
    try:
        health = await ia.cluster_health(es)
    except Exception as exc:  # noqa: BLE001 - surface a clean "unreachable" state
        return {"reachable": False, "error": str(exc)}
    return {"reachable": True, **health}


@router.get("/es/indices")
async def es_indices(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_search import index_admin as ia

    es = get_es_client()
    s = get_settings()
    return {
        "alias": s.catalogue_alias,
        "indices": await ia.list_indices(es),
        "aliases": await ia.list_aliases(es),
    }


@router.get("/es/mapping")
async def es_mapping(
    index: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_search import index_admin as ia

    try:
        return {"index": index, **await ia.get_mapping_and_settings(get_es_client(), index)}
    except Exception as exc:  # noqa: BLE001
        return error_response(404, "not_found", f"Index not found: {exc}")


@router.get("/es/tenant-count")
async def es_tenant_count(
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """How many catalogue docs a given store has indexed (sync verification)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_search import index_admin as ia

    return {"tenant_id": tenant, "docs": await ia.tenant_doc_count(get_es_client(), tenant)}


@router.post("/es/ensure-index")
async def es_ensure_index(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Idempotently create the catalogue index behind the read alias."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    from acip_search import index_admin as ia

    try:
        result = await ia.ensure_catalogue_index(get_es_client())
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(await get_pg_pool(), actor="operator", action="es.ensure_index", detail=result)
    return result


@router.post("/es/reindex")
async def es_reindex(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Build a fresh index, reindex into it, then swap the read alias (zero
    downtime, instant rollback by re-pointing the alias)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    source = str(payload.get("source_index", "")).strip()
    if not source:
        return error_response(422, "invalid_request", "Field 'source_index' is required.")
    from acip_search import index_admin as ia

    try:
        new_index = await ia.reindex_and_swap(get_es_client(), source)
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(
        await get_pg_pool(),
        actor="operator",
        action="es.reindex",
        detail={"source": source, "new_index": new_index},
    )
    return {"status": "reindexed", "source_index": source, "new_index": new_index}


@router.post("/es/alias")
async def es_alias(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Atomically point the read alias at a chosen index (manual rollback/swap)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    to_index = str(payload.get("index", "")).strip()
    if not to_index:
        return error_response(422, "invalid_request", "Field 'index' is required.")
    alias = str(payload.get("alias") or get_settings().catalogue_alias)
    from acip_search import index_admin as ia

    try:
        await ia.point_alias(get_es_client(), alias, to_index)
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(
        await get_pg_pool(),
        actor="operator",
        action="es.alias_swap",
        detail={"alias": alias, "index": to_index},
    )
    return {"status": "swapped", "alias": alias, "index": to_index}


@router.post("/es/delete-index")
async def es_delete_index(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Delete a concrete index (e.g. an old version after a successful swap).

    Refuses to delete an index that the read alias currently points at."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    index = str(payload.get("index", "")).strip()
    if not index:
        return error_response(422, "invalid_request", "Field 'index' is required.")
    from acip_search import index_admin as ia

    es = get_es_client()
    live = {a["index"] for a in await ia.list_aliases(es)}
    if index in live:
        return error_response(
            409, "alias_in_use", "This index is live behind an alias; swap the alias first."
        )
    try:
        await ia.delete_index(es, index)
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(await get_pg_pool(), actor="operator", action="es.delete_index",
                detail={"index": index})
    return {"status": "deleted", "index": index}


# --------------------------------------------------------------------------- #
# Agent test console (M7/M9) — run the RAG assistant against a chosen store's   #
# data with operator auth (no per-tenant widget key needed).                   #
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Plan management (M11) — operators edit pricing/credits/limits of plans.       #
# --------------------------------------------------------------------------- #
@router.get("/plans")
async def list_plans(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, code, name, description, price_monthly, currency, credits_per_month, "
            "monthly_credit_cap, rate_limit_per_min, is_public, sort_order, features "
            "FROM plans ORDER BY sort_order ASC, price_monthly ASC"
        )
    return {
        "plans": [
            {
                "id": str(r["id"]),
                "code": r["code"],
                "name": r["name"],
                "description": r["description"],
                "price_monthly": float(r["price_monthly"]),
                "currency": r["currency"],
                "credits_per_month": float(r["credits_per_month"]),
                "monthly_credit_cap": float(r["monthly_credit_cap"]),
                "rate_limit_per_min": r["rate_limit_per_min"],
                "is_public": r["is_public"],
                "sort_order": r["sort_order"],
                "features": r["features"],
            }
            for r in rows
        ]
    }


@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Edit a plan's pricing, included credits, caps, limits and visibility."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    columns = {
        "name": str,
        "description": str,
        "price_monthly": float,
        "currency": str,
        "credits_per_month": float,
        "monthly_credit_cap": float,
        "rate_limit_per_min": int,
        "is_public": bool,
        "sort_order": int,
    }
    sets: list[str] = []
    values: list[Any] = []
    for col, caster in columns.items():
        if col in payload:
            try:
                values.append(caster(payload[col]))
            except (TypeError, ValueError):
                return error_response(422, "invalid_request", f"Invalid value for '{col}'.")
            sets.append(f"{col} = ${len(values)}")
    if not sets:
        return error_response(422, "invalid_request", "No editable fields supplied.")
    values.append(plan_id)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            f"UPDATE plans SET {', '.join(sets)} WHERE id = ${len(values)}::uuid RETURNING id",
            *values,
        )
    if updated is None:
        return error_response(404, "not_found", "No such plan.")
    await audit(pool, actor="operator", action="plan.update",
                detail={"plan_id": plan_id, "fields": list(payload.keys())})
    return {"plan_id": plan_id, "status": "updated"}


# --------------------------------------------------------------------------- #
# Widget global defaults (M8) — platform-wide widget configuration set by the   #
# operator; per-store overrides live in the tenant settings.                   #
# --------------------------------------------------------------------------- #
_WIDGET_DEFAULTS_KEY = "widget:global_defaults"


@router.get("/widget-defaults")
async def get_widget_defaults(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import json

    redis = get_redis()
    raw = await redis.get(_WIDGET_DEFAULTS_KEY) if redis is not None else None
    defaults = json.loads(raw) if raw else _default_widget_config()
    return {"defaults": defaults}


@router.post("/widget-defaults")
async def set_widget_defaults(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import json

    allowed = {
        "primary_color",
        "chat_enabled",
        "search_enabled",
        "position",
        "platform_brand",
        "max_results",
        "greeting",
    }
    defaults = {**_default_widget_config(), **{k: v for k, v in payload.items() if k in allowed}}
    redis = get_redis()
    if redis is not None:
        await redis.set(_WIDGET_DEFAULTS_KEY, json.dumps(defaults))
    await audit(await get_pg_pool(), actor="operator", action="widget.defaults", detail=defaults)
    return {"status": "saved", "defaults": defaults}


def _default_widget_config() -> dict[str, Any]:
    return {
        "primary_color": "#1A7A4B",
        "chat_enabled": True,
        "search_enabled": True,
        "position": "bottom-right",
        "platform_brand": True,
        "max_results": 12,
        "greeting": "سلام! چطور می‌تونم در پیدا کردن محصول کمکتون کنم؟",
    }
