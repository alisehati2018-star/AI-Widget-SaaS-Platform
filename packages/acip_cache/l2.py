"""L2 semantic cache scaffold (M6: REQ-M6-003).

Embeds the query and compares it (cosine) against recently cached
question/answer vectors for the tenant; a hit above the per-tenant threshold
returns the stored answer, catching paraphrases. Phase 1 ships the mechanism +
threshold knob (validated against a holdout to avoid wrong-answer collisions);
the assistant wires it as the L2 layer in Phase 2. Backed by Redis for the
foundation; can move to an ES vector cache index later.
"""

from __future__ import annotations

import json
import math

from acip_core.config import get_settings


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class L2SemanticCache:
    def __init__(self, redis, threshold: float | None = None, max_entries: int = 500) -> None:
        self._redis = redis
        self._threshold = (
            threshold if threshold is not None else get_settings().semantic_cache_threshold
        )
        self._max = max_entries

    def _key(self, tenant_id: str) -> str:
        return f"l2:{tenant_id}"

    async def lookup(self, tenant_id: str, query_vector: list[float]) -> dict | None:
        """Return the cached answer if a stored entry exceeds the threshold."""
        if self._redis is None:
            return None
        try:
            entries = await self._redis.lrange(self._key(tenant_id), 0, self._max - 1)
        except Exception:  # noqa: BLE001
            return None
        best, best_score = None, 0.0
        for raw in entries:
            entry = json.loads(raw)
            score = cosine(query_vector, entry.get("vector", []))
            if score > best_score:
                best, best_score = entry, score
        if best is not None and best_score >= self._threshold:
            return {"answer": best.get("answer"), "score": best_score}
        return None

    async def store(self, tenant_id: str, query_vector: list[float], answer) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.lpush(
                self._key(tenant_id), json.dumps({"vector": query_vector, "answer": answer})
            )
            await self._redis.ltrim(self._key(tenant_id), 0, self._max - 1)
        except Exception:  # noqa: BLE001
            pass
