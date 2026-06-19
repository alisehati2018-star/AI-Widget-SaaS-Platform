"""Embedding client (M4: REQ-M4-001..006).

Talks to a Text-Embeddings-Inference (`/embed`) endpoint by default. The same
interface fronts any model, so a swap is config + reindex (REQ-M4-005). MRL
truncation (REQ-M4-003) trims vectors to the configured dimension and
re-normalises for cosine. A small Redis cache avoids re-embedding stable text
(REQ-M4-004). Failures raise `EmbeddingUnavailable` so callers can degrade
gracefully to lexical search (REQ-M5-009).
"""

from __future__ import annotations

import hashlib
import math

import httpx
from acip_core.config import Settings, get_settings
from acip_core.logging import get_logger

log = get_logger("embedding")


class EmbeddingUnavailable(RuntimeError):
    """Raised when the embedding backend cannot be reached or errors."""


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def truncate_mrl(vec: list[float], dims: int) -> list[float]:
    """Matryoshka truncation: keep the first `dims` components, re-normalise."""
    if dims <= 0 or dims >= len(vec):
        return vec
    return _l2_normalize(vec[:dims])


class EmbeddingClient:
    def __init__(self, settings: Settings | None = None, redis=None) -> None:
        self._s = settings or get_settings()
        self._redis = redis  # optional; lazy to keep this importable without Redis
        self._url = self._s.embeddings_url.rstrip("/")
        self._dims = self._s.embedding_dims

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{self._s.embedding_model}:{self._dims}:{digest}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts → list of vectors (MRL-truncated)."""
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self._url}/embed", json={"inputs": texts})
                resp.raise_for_status()
                raw = resp.json()
        except Exception as exc:  # noqa: BLE001 - normalise all backend errors
            log.warning("embedding.unavailable", error=str(exc))
            raise EmbeddingUnavailable(str(exc)) from exc
        # TEI returns a list of vectors aligned with inputs.
        return [truncate_mrl([float(x) for x in v], self._dims) for v in raw]

    async def embed_one(self, text: str) -> list[float]:
        """Embed a single text, using the Redis cache when available."""
        if self._redis is not None:
            key = self._cache_key(text)
            try:
                cached = await self._redis.lrange(key, 0, -1)
                if cached:
                    return [float(x) for x in cached]
            except Exception:  # noqa: BLE001 - cache is best-effort
                pass
        vec = (await self.embed([text]))[0]
        if self._redis is not None:
            try:
                key = self._cache_key(text)
                await self._redis.delete(key)
                await self._redis.rpush(key, *[str(x) for x in vec])
                await self._redis.expire(key, 86400)
            except Exception:  # noqa: BLE001
                pass
        return vec


_client: EmbeddingClient | None = None


def get_embedding_client(redis=None) -> EmbeddingClient:
    global _client
    if _client is None:
        _client = EmbeddingClient(redis=redis)
    return _client
