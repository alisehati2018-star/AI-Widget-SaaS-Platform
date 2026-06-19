"""L1 exact cache (M6: REQ-M6-002).

Hash of (tenant_id + normalized text + data_version) → stored answer. Catches
verbatim repeats at ~0 cost. The data_version in the key means a sync-driven
bump (REQ-M6-005) transparently invalidates stale entries.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def cache_key(tenant_id: str, text: str, data_version: int) -> str:
    digest = hashlib.sha256(
        f"{tenant_id}\x1f{normalize_text(text)}\x1f{data_version}".encode()
    ).hexdigest()
    return f"l1:{tenant_id}:{digest}"


class L1ExactCache:
    def __init__(self, redis, ttl_seconds: int = 3600) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, tenant_id: str, text: str, data_version: int) -> Any | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(cache_key(tenant_id, text, data_version))
            return json.loads(raw) if raw else None
        except Exception:  # noqa: BLE001
            return None

    async def set(self, tenant_id: str, text: str, data_version: int, value: Any) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(
                cache_key(tenant_id, text, data_version), json.dumps(value), ex=self._ttl
            )
        except Exception:  # noqa: BLE001
            pass
