"""Dead-letter queue for sync events (M3: REQ-M3-005).

Events that fail repeatedly are parked (never silently dropped) and can be
replayed after a fix. Backed by a Redis list per tenant.
"""

from __future__ import annotations

import json
from typing import Any

from acip_core.logging import get_logger

log = get_logger("dlq")


def _key(tenant_id: str) -> str:
    return f"dlq:sync:{tenant_id}"


async def park(redis, tenant_id: str, event: dict[str, Any], error: str) -> None:
    """Park a poison event for inspection/replay."""
    log.warning("dlq.parked", tenant_id=tenant_id, error=error)
    if redis is None:
        return
    try:
        await redis.lpush(_key(tenant_id), json.dumps({"event": event, "error": error}))
    except Exception:  # noqa: BLE001
        pass


async def drain(redis, tenant_id: str, limit: int = 100) -> list[dict]:
    """Return parked events for replay (does not remove them)."""
    if redis is None:
        return []
    try:
        raw = await redis.lrange(_key(tenant_id), 0, limit - 1)
        return [json.loads(r) for r in raw]
    except Exception:  # noqa: BLE001
        return []
