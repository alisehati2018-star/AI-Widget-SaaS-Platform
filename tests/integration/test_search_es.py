"""ES-gated integration tests (M2/M5/M11-001).

Covers the analyzer collapsing ZWNJ/digit variants, an upsert→search round
trip, and the cross-tenant isolation invariant. Skipped without a live cluster.
"""

from __future__ import annotations

import uuid

import pytest
from acip_search.index_admin import index_body

INDEX = f"acip-itest-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def index(es_client):
    es_client.indices.create(index=INDEX, body=index_body(dims=8))
    yield INDEX
    es_client.indices.delete(index=INDEX, ignore=[404])


def _analyze_tokens(es_client, text: str) -> list[str]:
    resp = es_client.indices.analyze(index=INDEX, body={"analyzer": "fa_text", "text": text})
    return [t["token"] for t in resp["tokens"]]


def test_zwnj_variants_collapse(es_client, index):
    # "می‌روم" (with ZWNJ) and "میروم" (without) should tokenize identically.
    with_zwnj = _analyze_tokens(es_client, "می‌روم")
    without = _analyze_tokens(es_client, "میروم")
    assert with_zwnj == without


def test_digit_folding(es_client, index):
    # Persian digits fold to ASCII so model numbers match.
    assert _analyze_tokens(es_client, "۱۲۳") == _analyze_tokens(es_client, "123")


def test_upsert_and_tenant_isolation(es_client, index):
    docs = [
        ("t1:1", {"tenant_id": "t1", "product_id": "1", "title": "کفش نایک", "in_stock": True}),
        ("t2:1", {"tenant_id": "t2", "product_id": "1", "title": "کفش نایک", "in_stock": True}),
    ]
    for _id, body in docs:
        es_client.index(index=index, id=_id, document=body)
    es_client.indices.refresh(index=index)

    # Tenant-scoped search must never return another tenant's docs.
    from acip_search.query import build_hybrid_query

    q = build_hybrid_query("t1", text="کفش", query_vector=None)
    resp = es_client.search(index=index, body=q)
    tenants = {h["_source"]["tenant_id"] for h in resp["hits"]["hits"]}
    assert tenants == {"t1"}
