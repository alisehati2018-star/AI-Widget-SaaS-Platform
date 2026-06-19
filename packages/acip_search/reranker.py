"""Cross-encoder reranker client (M5: REQ-M5-006).

Optional and eval-gated (default off until the golden set proves the NDCG gain
justifies the latency). Scores only the fused top-k. Used when reranking is
performed application-side rather than via ES `text_similarity_reranker`.
Degrades to a no-op (returns the input order) if the reranker is unavailable
(REQ-M5-009).
"""

from __future__ import annotations

import httpx
from acip_core.config import get_settings
from acip_core.logging import get_logger

log = get_logger("reranker")


class Reranker:
    def __init__(self) -> None:
        self._url = get_settings().reranker_url.rstrip("/")

    async def rerank(self, query: str, docs: list[str], top_n: int | None = None) -> list[int]:
        """Return doc indices ordered best-first. Falls back to identity order."""
        if not docs:
            return []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._url}/rerank",
                    json={"query": query, "texts": docs, "return_text": False},
                )
                resp.raise_for_status()
                results = resp.json()  # [{"index": i, "score": s}, ...]
            order = [r["index"] for r in sorted(results, key=lambda r: r["score"], reverse=True)]
        except Exception as exc:  # noqa: BLE001 - degrade to un-reranked
            log.warning("reranker.unavailable", error=str(exc))
            order = list(range(len(docs)))
        return order[: top_n or len(order)]
