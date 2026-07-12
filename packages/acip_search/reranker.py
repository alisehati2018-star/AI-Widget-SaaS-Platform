"""Cross-encoder reranker clients (M5: REQ-M5-006).

Application-side reranking of the fused top-k, used when the admin binds a
`rerank` task chain in the AI routing registry (the alternative — ES-side
`text_similarity_reranker` — stays available via RERANK_ENABLED and needs an
inference endpoint on the cluster). Optional and eval-gated. Always degrades
to a no-op (input order) when unavailable (REQ-M5-009).

Wire protocols:
- ``tei``    — local TEI ``POST /rerank {"query","texts"}`` →
               ``[{"index","score"}]``
- ``cohere`` — vendor ``POST /rerank {"model","query","documents","top_n"}`` →
               ``{"results":[{"index","relevance_score"}]}`` (the de facto
               standard Cohere/Jina/Voyage expose)
"""

from __future__ import annotations

import httpx
from acip_core.config import get_settings
from acip_core.logging import get_logger

log = get_logger("reranker")


async def _rerank_call(
    *, base_url: str, wire: str, model: str, api_key: str | None,
    query: str, docs: list[str],
) -> list[int]:
    """One reranker HTTP call → doc indices ordered best-first. Raises on error."""
    headers = {"authorization": f"Bearer {api_key}"} if api_key else {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        if wire == "cohere":
            resp = await client.post(
                f"{base_url.rstrip('/')}/rerank",
                json={"model": model, "query": query, "documents": docs, "top_n": len(docs)},
                headers=headers,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            scored = [(r["index"], float(r.get("relevance_score", 0.0))) for r in results]
        else:  # tei
            resp = await client.post(
                f"{base_url.rstrip('/')}/rerank",
                json={"query": query, "texts": docs, "return_text": False},
                headers=headers,
            )
            resp.raise_for_status()
            scored = [(r["index"], float(r.get("score", 0.0))) for r in resp.json()]
    return [i for i, _ in sorted(scored, key=lambda t: t[1], reverse=True)]


class Reranker:
    """Single env-configured TEI reranker (legacy path)."""

    def __init__(self) -> None:
        self._url = get_settings().reranker_url.rstrip("/")

    async def rerank(self, query: str, docs: list[str], top_n: int | None = None) -> list[int]:
        """Return doc indices ordered best-first. Falls back to identity order."""
        if not docs:
            return []
        try:
            order = await _rerank_call(
                base_url=self._url, wire="tei", model=get_settings().reranker_model,
                api_key=None, query=query, docs=docs,
            )
        except Exception as exc:  # noqa: BLE001 - degrade to un-reranked
            log.warning("reranker.unavailable", error=str(exc))
            order = list(range(len(docs)))
        return order[: top_n or len(order)]


class ChainedReranker:
    """Registry-routed reranker: tries the admin-bound `rerank` chain in order
    (per-provider retry/backoff), degrading to identity order if every
    endpoint fails. Mirrors `ChainedEmbeddingClient`."""

    def __init__(self, registry) -> None:
        self._registry = registry

    async def has_chain(self) -> bool:
        """True only when the admin explicitly bound a rerank chain in the
        registry (NOT the env fallback) — binding is the opt-in signal for
        app-side reranking, so existing env-only deployments keep their
        current behavior."""
        snap = await self._registry.snapshot()
        return bool(snap.rerank_endpoints)

    async def rerank(self, query: str, docs: list[str], top_n: int | None = None) -> list[int]:
        if not docs:
            return []
        from acip_gateway.retry import call_with_retry

        endpoints = await self._registry.rerank_endpoints()
        for ep in endpoints:

            async def _call(ep=ep) -> list[int]:
                return await _rerank_call(
                    base_url=ep.base_url, wire=ep.wire, model=ep.model,
                    api_key=ep.api_key, query=query, docs=docs,
                )

            try:
                order = await call_with_retry(
                    _call, max_retries=ep.max_retries, backoff_ms=ep.retry_backoff_ms
                )
                return order[: top_n or len(order)]
            except Exception as exc:  # noqa: BLE001 - fail over to the next endpoint
                log.warning("reranker.endpoint_failed", model=ep.model, error=str(exc))
                continue
        log.warning("reranker.unavailable", error="all rerank endpoints failed")
        return list(range(len(docs)))[: top_n or len(docs)]
