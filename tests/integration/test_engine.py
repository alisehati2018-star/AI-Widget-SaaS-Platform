"""Phase 6 (completion roadmap) — smart engine: graceful 503s + bulk fixture.

Two independent gates:

* **PG-gated** (``live_client``): with Elasticsearch DOWN, the public
  ``/v1/search`` / ``/v1/suggest`` / ``/v1/chat`` endpoints must answer a clean
  **503 with a stable error code** (``search_unavailable`` / ``index_not_ready``
  / ``assistant_unavailable``) instead of a raw 500 — the widget shows a retry
  hint. Skipped automatically when ES is actually reachable.

* **ES-gated** (``es_client``): the 100-product Persian fixture flows through
  the REAL sync pipeline (normalize → upsert) and a Persian query round-trips
  to the expected product. Skipped without a live cluster.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

import pytest

from .conftest import ADMIN_TOKEN

_HDR = {"x-admin-token": ADMIN_TOKEN}
FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "catalog_fa.json"


def _es_reachable() -> bool:
    import httpx
    from acip_core.config import get_settings

    try:
        return httpx.get(get_settings().es_host, timeout=2).status_code < 500
    except Exception:  # noqa: BLE001
        return False


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


async def _issue_widget_key(store: str) -> str:
    """Insert a tenant + widget api_key straight into PG (same path as seed)."""
    import asyncpg
    from acip_core.config import get_settings

    from api.deps import hash_key

    raw = "acip_itest_" + uuid.uuid4().hex
    conn = await asyncpg.connect(dsn=get_settings().pg_dsn, timeout=5)
    try:
        tenant_id = await conn.fetchval(
            "INSERT INTO tenants (slug, name) VALUES ($1, $2) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            f"p6-{int(time.time() * 1000)}-{store}",
            f"P6 {store}",
        )
        await conn.execute(
            "INSERT INTO api_keys (tenant_id, key_hash, scope, label) VALUES ($1, $2, $3, $4)",
            tenant_id,
            hash_key(raw),
            "widget",
            "p6 itest",
        )
    finally:
        await conn.close()
    return raw


# --------------------------------------------------------------------------- #
# Graceful 503 (never 500) on the public surface while ES is down              #
# --------------------------------------------------------------------------- #
def test_v1_degrades_to_503_when_es_down(live_client):
    if _es_reachable():
        pytest.skip("ES is up; the degraded path needs the cluster DOWN.")
    key = _run(_issue_widget_key("deg503"))
    hdr = {"x-api-key": key}

    r = live_client.post("/v1/search", json={"query": "گوشی سامسونگ"}, headers=hdr)
    assert r.status_code == 503, r.text
    assert r.json()["error"]["code"] in {"search_unavailable", "index_not_ready"}

    r = live_client.get("/v1/suggest", params={"q": "گوشی"}, headers=hdr)
    assert r.status_code == 503, r.text
    assert r.json()["error"]["code"] in {"search_unavailable", "index_not_ready"}

    r = live_client.post("/v1/chat", json={"message": "یک گوشی خوب میخوام"}, headers=hdr)
    assert r.status_code == 503, r.text
    assert r.json()["error"]["code"] == "assistant_unavailable"

    # No key → auth error, not a degradation response.
    assert live_client.post("/v1/search", json={"query": "x"}).status_code == 401


# --------------------------------------------------------------------------- #
# Bulk fixture round-trips through the real pipeline (ES-gated)                #
# --------------------------------------------------------------------------- #
def test_fixture_ingest_and_persian_search(es_client):
    from acip_search.index_admin import index_body
    from acip_search.query import build_hybrid_query
    from acip_sync.ingest import doc_id
    from acip_sync.normalize import normalize_product

    index = f"acip-itest-p6-{uuid.uuid4().hex[:8]}"
    tenant = f"t-p6-{uuid.uuid4().hex[:8]}"
    es_client.indices.create(index=index, body=index_body(dims=8))
    try:
        products = json.loads(FIXTURE.read_text(encoding="utf-8"))
        assert len(products) == 100
        for raw in products[:20]:  # phones + a few laptops: enough for relevance
            p = normalize_product(tenant, "rest", raw)
            es_client.index(index=index, id=doc_id(tenant, p.product_id), document=p.to_doc())
        es_client.indices.refresh(index=index)

        q = build_hybrid_query(tenant, text="گوشی سامسونگ", query_vector=None)
        resp = es_client.search(index=index, body=q)
        hits = [h["_source"]["product_id"] for h in resp["hits"]["hits"]]
        assert hits, "Persian brand query must return results"
        assert hits[0] in {"p-001", "p-002", "p-008"}  # the Samsung phones

        # ZWNJ-variant query still matches (analyzer, not luck).
        q = build_hybrid_query(tenant, text="لپتاپ", query_vector=None)
        resp = es_client.search(index=index, body=q)
        assert resp["hits"]["hits"], "spelling variant must not zero-result"
    finally:
        es_client.indices.delete(index=index, ignore=[404])
