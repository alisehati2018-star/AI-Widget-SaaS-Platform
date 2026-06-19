"""Search service — orchestrates the hybrid retrieval path (M5).

Embeds the query (degrading to BM25-only if the embedding service is down —
REQ-M5-009), builds the tenant-scoped query (REQ-M11-001), executes it against
the catalogue alias, maps results, logs zero-results (REQ-M5-008), and records a
usage/metering event (REQ-M6-012). Latency target: p95 < 150 ms (REQ-M5-010).
"""

from __future__ import annotations

import time
from typing import Any

from acip_core.config import get_settings
from acip_core.logging import get_logger

from .query import build_hybrid_query
from .zero_result import log_zero_result

log = get_logger("search")


class SearchService:
    def __init__(self, es, embedding_client=None, redis=None, meter=None) -> None:
        self._es = es
        self._embed = embedding_client
        self._redis = redis
        self._meter = meter  # callable(tenant_id, route, **kwargs) or None
        self._s = get_settings()

    async def _query_vector(self, text: str) -> list[float] | None:
        if self._embed is None:
            return None
        try:
            return await self._embed.embed_one(text)
        except Exception:  # noqa: BLE001 - degrade to lexical (REQ-M5-009)
            log.warning("search.embedding_degraded")
            return None

    async def search(
        self,
        tenant_id: str,
        text: str,
        *,
        filters: dict[str, Any] | None = None,
        size: int | None = None,
        rerank: bool | None = None,
    ) -> dict:
        started = time.perf_counter()
        size = size or self._s.search_default_size
        rerank = self._s.rerank_enabled if rerank is None else rerank

        vector = await self._query_vector(text)
        body = build_hybrid_query(
            tenant_id,
            text=text,
            query_vector=vector,
            filters=filters,
            size=size,
            rerank=rerank,
            rerank_window=self._s.rerank_window,
            rerank_inference_id=self._s.reranker_model,
            rank_constant=self._s.rrf_rank_constant,
            rank_window=self._s.rrf_rank_window,
            knn_k=self._s.knn_k,
            knn_num_candidates=self._s.knn_num_candidates,
        )
        resp = await self._es.search(index=self._s.catalogue_alias, body=body)
        hits = resp["hits"]["hits"]
        results = [{**h["_source"], "score": h.get("_score")} for h in hits]

        if not results:
            await log_zero_result(self._redis, tenant_id, text)

        latency_ms = int((time.perf_counter() - started) * 1000)
        if self._meter is not None:
            await self._meter(
                tenant_id,
                route="search",
                rung="search",
                cache_outcome="miss",
                latency_ms=latency_ms,
                lexical_only=vector is None,
            )
        return {
            "results": results,
            "count": len(results),
            "lexical_only": vector is None,
            "latency_ms": latency_ms,
        }
