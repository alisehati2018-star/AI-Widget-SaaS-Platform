"""The central, tenant-scoped hybrid query builder (M5 + M11-001).

This is the **single chokepoint** every read path goes through. It fuses a BM25
lexical leg and a kNN vector leg with RRF, and stamps the **mandatory
`tenant_id` term filter onto BOTH legs** (ACORN prunes on it). It refuses to
build a query without a `tenant_id` — the isolation invariant enforced in code,
not convention (blueprint §9, Appendix B). An optional `text_similarity_reranker`
wraps the fused top-k only.
"""

from __future__ import annotations

from typing import Any

# Field boosts (Appendix B): exact title/brand matches dominate description.
_FIELDS = ["title^3", "brand^2", "description"]
_SOURCE = ["product_id", "title", "brand", "price", "in_stock", "categories"]


class MissingTenantError(ValueError):
    """Raised if a query is built without a tenant_id (isolation invariant)."""


def _normalise_filters(tenant_id: str, filters: dict[str, Any] | None) -> list[dict]:
    """Build the filter clause list, ALWAYS led by the tenant_id term."""
    clauses: list[dict] = [{"term": {"tenant_id": tenant_id}}]
    if not filters:
        return clauses
    if (cats := filters.get("categories")) is not None:
        clauses.append({"terms": {"categories": cats if isinstance(cats, list) else [cats]}})
    if (brand := filters.get("brand")) is not None:
        clauses.append({"term": {"brand": brand}})
    if (in_stock := filters.get("in_stock")) is not None:
        clauses.append({"term": {"in_stock": bool(in_stock)}})
    price = filters.get("price")
    if isinstance(price, dict) and (price.get("gte") is not None or price.get("lte") is not None):
        rng = {k: price[k] for k in ("gte", "lte") if price.get(k) is not None}
        clauses.append({"range": {"price": rng}})
    return clauses


def build_hybrid_query(
    tenant_id: str,
    *,
    text: str,
    query_vector: list[float] | None = None,
    filters: dict[str, Any] | None = None,
    size: int = 20,
    rerank: bool = False,
    rerank_window: int = 50,
    rerank_inference_id: str = "store-reranker",
    rank_constant: int = 60,
    rank_window: int = 100,
    knn_k: int = 100,
    knn_num_candidates: int = 200,
) -> dict:
    """Return the ES request body for a tenant-scoped hybrid search.

    If `query_vector` is None (e.g. the embedding service is down), the kNN leg
    is omitted and the query degrades to BM25 only (REQ-M5-009) — still
    tenant-filtered.
    """
    if not tenant_id:
        raise MissingTenantError("tenant_id is required on every query (isolation invariant)")

    filter_clauses = _normalise_filters(tenant_id, filters)

    bm25 = {
        "standard": {
            "query": {
                "bool": {
                    "must": [
                        {"multi_match": {"query": text, "fields": _FIELDS, "type": "best_fields"}}
                    ],
                    "filter": filter_clauses,
                }
            }
        }
    }

    retrievers: list[dict] = [bm25]
    if query_vector is not None:
        retrievers.append(
            {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_vector,
                    "k": knn_k,
                    "num_candidates": knn_num_candidates,
                    "filter": filter_clauses,  # ACORN: same tenant filter on the vector leg
                }
            }
        )

    # With a single leg (vector unavailable) RRF is unnecessary; use it directly.
    if len(retrievers) == 1:
        inner: dict = retrievers[0]
    else:
        inner = {
            "rrf": {
                "retrievers": retrievers,
                "rank_constant": rank_constant,
                "rank_window_size": rank_window,
            }
        }

    if rerank:
        inner = {
            "text_similarity_reranker": {
                "retriever": inner,
                "rank_window_size": rerank_window,
                "field": "title",
                "inference_id": rerank_inference_id,
                "inference_text": text,
            }
        }

    return {"retriever": inner, "size": size, "_source": _SOURCE}


def query_has_tenant_filter(body: dict, tenant_id: str) -> bool:
    """Test helper: assert the tenant term filter is present on every leg."""
    found_legs = 0
    filtered_legs = 0

    def _walk(node: Any) -> None:
        nonlocal found_legs, filtered_legs
        if isinstance(node, dict):
            if "standard" in node:
                found_legs += 1
                clauses = node["standard"]["query"]["bool"].get("filter", [])
                if {"term": {"tenant_id": tenant_id}} in clauses:
                    filtered_legs += 1
            if "knn" in node:
                found_legs += 1
                clauses = node["knn"].get("filter", [])
                if {"term": {"tenant_id": tenant_id}} in clauses:
                    filtered_legs += 1
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(body)
    return found_legs > 0 and found_legs == filtered_legs
