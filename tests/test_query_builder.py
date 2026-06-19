"""Unit tests for the central tenant-scoped query builder (M5 + M11-001).

The isolation invariant lives here: no query body is producible without the
tenant filter on every retriever leg, and the builder refuses a missing tenant.
"""

from __future__ import annotations

import pytest
from acip_search.query import (
    MissingTenantError,
    build_hybrid_query,
    query_has_tenant_filter,
)


def test_missing_tenant_raises():
    with pytest.raises(MissingTenantError):
        build_hybrid_query("", text="کفش")


def test_hybrid_has_tenant_filter_on_both_legs():
    body = build_hybrid_query("t1", text="کفش", query_vector=[0.1] * 8)
    assert query_has_tenant_filter(body, "t1")
    # RRF fuses both legs.
    assert "rrf" in body["retriever"]
    assert len(body["retriever"]["rrf"]["retrievers"]) == 2


def test_lexical_only_when_no_vector_still_tenant_filtered():
    body = build_hybrid_query("t1", text="کفش", query_vector=None)
    assert query_has_tenant_filter(body, "t1")
    # Single leg -> no rrf wrapper, but the standard leg keeps the filter.
    assert "standard" in body["retriever"]


def test_field_boosts_present():
    body = build_hybrid_query("t1", text="نایک", query_vector=None)
    fields = body["retriever"]["standard"]["query"]["bool"]["must"][0]["multi_match"]["fields"]
    assert "title^3" in fields and "brand^2" in fields and "description" in fields


def test_rerank_wraps_fusion_and_keeps_filter():
    body = build_hybrid_query("t1", text="کفش", query_vector=[0.1] * 8, rerank=True)
    assert "text_similarity_reranker" in body["retriever"]
    assert query_has_tenant_filter(body, "t1")


def test_filters_applied_with_tenant():
    body = build_hybrid_query(
        "t1",
        text="کفش",
        query_vector=None,
        filters={"brand": "Nike", "in_stock": True, "price": {"gte": 10, "lte": 100}},
    )
    clauses = body["retriever"]["standard"]["query"]["bool"]["filter"]
    assert {"term": {"tenant_id": "t1"}} in clauses
    assert {"term": {"brand": "Nike"}} in clauses
    assert any("range" in c for c in clauses)


def test_other_tenant_filter_not_satisfied():
    body = build_hybrid_query("t1", text="کفش", query_vector=[0.1] * 8)
    # A different tenant's filter is NOT present -> isolation holds.
    assert not query_has_tenant_filter(body, "t2")
