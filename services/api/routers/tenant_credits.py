"""Store-owner dashboard — credit balance/usage history + tenant audit log."""

from __future__ import annotations

from acip_billing.ledger import plan_status, usage_summary
from acip_core.clients import get_pg_pool
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/credits")
async def credits(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    usage = await usage_summary(pool, p.tenant_id)
    status = await plan_status(pool, p.tenant_id)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT delta, rung, reason, created_at FROM credit_ledger "
            "WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 100",
            p.tenant_id,
        )
    return {
        "used": usage["used"],
        "granted": usage["granted"],
        "balance": status.get("balance", 0.0),
        "cap": status.get("cap"),
        "within_plan": status.get("within_plan", True),
        "ledger": [
            {
                "delta": float(r["delta"]),
                "rung": r["rung"],
                "reason": r["reason"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
    }


@router.get("/audit")
async def tenant_audit(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT actor, action, detail, created_at FROM audit_log "
            "WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 100",
            p.tenant_id,
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
