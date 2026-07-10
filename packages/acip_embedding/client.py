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


def cache_key(model: str, dims: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"emb:{model}:{dims}:{digest}"


async def cache_get(redis, key: str) -> list[float] | None:
    """Best-effort Redis lookup; any failure/absence is a cache miss."""
    if redis is None:
        return None
    try:
        cached = await redis.lrange(key, 0, -1)
        return [float(x) for x in cached] if cached else None
    except Exception:  # noqa: BLE001 - cache is best-effort
        return None


async def cache_set(redis, key: str, vec: list[float]) -> None:
    if redis is None:
        return
    try:
        await redis.delete(key)
        await redis.rpush(key, *[str(x) for x in vec])
        await redis.expire(key, 86400)
    except Exception:  # noqa: BLE001 - cache is best-effort
        pass


class EmbeddingClient:
    """Talks to one embedding endpoint. `wire="tei"` (default) speaks the
    self-hosted Text-Embeddings-Inference `/embed` protocol used by the local
    model; `wire="openai"` speaks the `/embeddings` OpenAI wire format used by
    admin-configured vendor embedding models (`ai_providers`/`ai_models`,
    `modality='embedding'`) — see `chained.py` for the multi-provider,
    failover-capable client built on top of this one."""

    def __init__(
        self,
        settings: Settings | None = None,
        redis=None,
        *,
        base_url: str | None = None,
        model: str | None = None,
        dims: int | None = None,
        api_key: str | None = None,
        wire: str = "tei",
    ) -> None:
        s = settings or get_settings()
        self._s = s
        self._redis = redis  # optional; lazy to keep this importable without Redis
        self._url = (base_url or s.embeddings_url).rstrip("/")
        self._model = model or s.embedding_model
        self._dims = dims if dims is not None else s.embedding_dims
        self._api_key = api_key
        self._wire = wire

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts → list of vectors (MRL-truncated)."""
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if self._wire == "openai":
                    headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
                    resp = await client.post(
                        f"{self._url}/embeddings",
                        json={"input": texts, "model": self._model},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    raw = [item["embedding"] for item in data["data"]]
                else:
                    resp = await client.post(f"{self._url}/embed", json={"inputs": texts})
                    resp.raise_for_status()
                    raw = resp.json()
        except Exception as exc:  # noqa: BLE001 - normalise all backend errors
            log.warning("embedding.unavailable", error=str(exc), wire=self._wire)
            raise EmbeddingUnavailable(str(exc)) from exc
        return [truncate_mrl([float(x) for x in v], self._dims) for v in raw]

    async def embed_one(self, text: str) -> list[float]:
        """Embed a single text, using the Redis cache when available."""
        key = cache_key(self._model, self._dims, text)
        cached = await cache_get(self._redis, key)
        if cached is not None:
            return cached
        vec = (await self.embed([text]))[0]
        await cache_set(self._redis, key, vec)
        return vec


_client: EmbeddingClient | None = None


def get_embedding_client(redis=None) -> EmbeddingClient:
    global _client
    if _client is None:
        _client = EmbeddingClient(redis=redis)
    return _client
