"""Insight aggregations (M10: REQ-M10-001/002/007, blueprint §11).

Mines the same Elastic data to answer the questions an owner actually asks:
most-wanted products, searched-but-out-of-stock items, and funnel drop-off.
Every aggregation is **tenant-scoped** through the mandatory filter
(REQ-M10-006) and runs async/batch, off the shopper path. The query builders
are pure (unit-tested); the runners take an injected ES client.
"""

from __future__ import annotations

from typing import Any

from acip_core.config import get_settings


def events_index() -> str:
    return f"{get_settings().es_index_prefix}-events"


def _tenant_filter(tenant_id: str) -> dict:
    """The mandatory tenant filter every analytics query carries (§11.5)."""
    return {"term": {"tenant_id": tenant_id}}


def most_wanted_query(tenant_id: str, size: int = 20) -> dict:
    """Top search terms (demand signal)."""
    return {
        "size": 0,
        "query": {"bool": {"filter": [_tenant_filter(tenant_id), {"term": {"type": "search"}}]}},
        "aggs": {"terms": {"terms": {"field": "query.kw", "size": size}}},
    }


def zero_result_query(tenant_id: str, size: int = 20) -> dict:
    """Most frequent zero-result searches (demand gaps + relevance bugs, §6.8)."""
    return {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    _tenant_filter(tenant_id),
                    {"term": {"type": "search"}},
                    {"term": {"result_count": 0}},
                ]
            }
        },
        "aggs": {"terms": {"terms": {"field": "query.kw", "size": size}}},
    }


def funnel_query(tenant_id: str) -> dict:
    """Search → click → cart counts (drop-off points)."""
    return {
        "size": 0,
        "query": {"bool": {"filter": [_tenant_filter(tenant_id)]}},
        "aggs": {"stages": {"terms": {"field": "type", "size": 10}}},
    }


def _buckets(resp: dict, agg: str = "terms") -> list[dict[str, Any]]:
    return resp.get("aggregations", {}).get(agg, {}).get("buckets", [])


async def most_wanted(es, tenant_id: str, size: int = 20) -> list[dict[str, Any]]:
    if es is None:
        return []
    resp = await es.search(index=events_index(), body=most_wanted_query(tenant_id, size))
    return [{"term": b["key"], "count": b["doc_count"]} for b in _buckets(resp)]


async def zero_result_terms(es, tenant_id: str, size: int = 20) -> list[dict[str, Any]]:
    if es is None:
        return []
    resp = await es.search(index=events_index(), body=zero_result_query(tenant_id, size))
    return [{"term": b["key"], "count": b["doc_count"]} for b in _buckets(resp)]


async def funnel(es, tenant_id: str) -> dict[str, int]:
    if es is None:
        return {}
    resp = await es.search(index=events_index(), body=funnel_query(tenant_id))
    return {b["key"]: b["doc_count"] for b in _buckets(resp, "stages")}
