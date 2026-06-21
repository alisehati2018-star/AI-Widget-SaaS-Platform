"""Audit logging (M11: REQ-M11-007, blueprint §9.5).

Append-only record of admin actions, key issuance, and money-moving agent tool
calls. Best-effort write to the control-plane `audit_log` table; an audit
failure is logged but never blocks the action it records (the action's own
transaction is authoritative).
"""

from __future__ import annotations

from typing import Any

from acip_core.logging import get_logger

log = get_logger("audit")


async def audit(pg_pool, *, actor: str, action: str, tenant_id: str | None = None,
                detail: dict[str, Any] | None = None) -> None:
    if pg_pool is None:
        return
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO audit_log (tenant_id, actor, action, detail) "
                "VALUES ($1, $2, $3, $4::jsonb)",
                tenant_id, actor, action, detail or {},
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("audit.write_failed", action=action, error=str(exc))
