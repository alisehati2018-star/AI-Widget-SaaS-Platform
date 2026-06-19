"""Conversational memory — two cheap tiers (M7: REQ-M7-006, blueprint §7.3).

Session memory (recent turns) lives in Redis for the life of a conversation.
Long-term memory (returning-shopper preferences) lives in Elasticsearch as just
another index. Both are summarised/truncated aggressively so they never bloat
the prompt or the cost.
"""

from __future__ import annotations

import json
from typing import Any

from acip_core.config import get_settings
from acip_core.logging import get_logger

log = get_logger("assistant.memory")

SESSION_TTL = 3600  # 1h conversation window
MAX_SESSION_TURNS = 12


class SessionMemory:
    """Recent turns for a single conversation, in Redis."""

    def __init__(self, redis) -> None:
        self._redis = redis

    def _key(self, tenant_id: str, session_id: str) -> str:
        return f"chatmem:{tenant_id}:{session_id}"

    async def history(self, tenant_id: str, session_id: str) -> list[dict]:
        if self._redis is None:
            return []
        try:
            key = self._key(tenant_id, session_id)
            raw = await self._redis.lrange(key, 0, MAX_SESSION_TURNS - 1)
            return [json.loads(x) for x in reversed(raw)]
        except Exception:  # noqa: BLE001
            return []

    async def append(self, tenant_id: str, session_id: str, role: str, content: str) -> None:
        if self._redis is None:
            return
        key = self._key(tenant_id, session_id)
        try:
            await self._redis.lpush(key, json.dumps({"role": role, "content": content}))
            await self._redis.ltrim(key, 0, MAX_SESSION_TURNS - 1)
            await self._redis.expire(key, SESSION_TTL)
        except Exception:  # noqa: BLE001
            pass


class LongTermMemory:
    """Returning-shopper preferences in an Elasticsearch index (tenant-scoped)."""

    def __init__(self, es) -> None:
        self._es = es

    @property
    def _index(self) -> str:
        return f"{get_settings().es_index_prefix}-chatmem"

    async def remember(self, tenant_id: str, shopper_id: str, summary: str) -> None:
        if self._es is None:
            return
        doc = {"tenant_id": tenant_id, "shopper_id": shopper_id, "summary": summary}
        try:
            await self._es.index(index=self._index, id=f"{tenant_id}:{shopper_id}", document=doc)
        except Exception as exc:  # noqa: BLE001
            log.warning("memory.longterm_failed", error=str(exc))

    async def recall(self, tenant_id: str, shopper_id: str) -> str | None:
        if self._es is None:
            return None
        try:
            resp = await self._es.get(index=self._index, id=f"{tenant_id}:{shopper_id}")
            src: dict[str, Any] = resp.get("_source", {})
            # Isolation: never return another tenant's memory.
            if src.get("tenant_id") != tenant_id:
                return None
            return src.get("summary")
        except Exception:  # noqa: BLE001
            return None
