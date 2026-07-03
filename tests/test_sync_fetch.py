"""Hermetic tests for the Phase-7 pull path: store fetchers + reconciliation.

Uses httpx.MockTransport as the "store" — no network, no ES. Verifies paging,
auth placement (query vs basic vs token header), watermark round-tripping
without timezone shifts, and that reconcile() repairs through the real
normalize→upsert pipeline with the rich embedding text.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from acip_sync.fetch import (
    fetch_changed_since,
    fetch_opencart_changed,
    fetch_woo_changed,
)
from acip_sync.reconcile import reconcile


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


async def _collect(it):
    return [x async for x in it]


# --------------------------------------------------------------------------- #
# WooCommerce fetcher                                                          #
# --------------------------------------------------------------------------- #
def _woo_transport(pages: list[list[dict]], seen: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        page = int(request.url.params.get("page", "1"))
        body = pages[page - 1] if page <= len(pages) else []
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


def test_woo_fetch_pages_until_short_page():
    pages = [[{"id": i} for i in range(3)], [{"id": 99}]]
    seen: list[httpx.Request] = []
    client = httpx.AsyncClient(transport=_woo_transport(pages, seen))
    got = _run(
        _collect(
            fetch_woo_changed(
                "http://store.local", "ck_x", "cs_y",
                since="2026-06-01T00:00:00+00:00", page_size=3, client=client,
            )
        )
    )
    assert [p["id"] for p in got] == [0, 1, 2, 99]
    assert len(seen) == 2  # second page was short → stop
    first = seen[0].url.params
    assert first["modified_after"] == "2026-06-01T00:00:00+00:00"
    assert first["dates_are_gmt"] == "true"
    assert first["orderby"] == "modified"
    # http → credentials must travel as query params (Woo rule).
    assert first["consumer_key"] == "ck_x" and first["consumer_secret"] == "cs_y"
    assert "authorization" not in {k.lower() for k in seen[0].headers}


def test_woo_fetch_uses_basic_auth_over_https():
    seen: list[httpx.Request] = []
    client = httpx.AsyncClient(transport=_woo_transport([[]], seen))
    _run(_collect(fetch_woo_changed("https://store.local", "ck", "cs", client=client)))
    assert seen[0].headers.get("authorization", "").startswith("Basic ")
    assert "consumer_key" not in seen[0].url.params


# --------------------------------------------------------------------------- #
# OpenCart fetcher                                                             #
# --------------------------------------------------------------------------- #
def test_opencart_fetch_pages_via_more_flag_and_token_header():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(200, json={"products": [{"product_id": 1}], "more": True})
        return httpx.Response(200, json={"products": [{"product_id": 2}], "more": False})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    got = _run(
        _collect(
            fetch_opencart_changed(
                "http://oc.local", "tok-123",
                since="2026-06-01T10:30:00+00:00", client=client,
            )
        )
    )
    assert [p["product_id"] for p in got] == [1, 2]
    assert len(seen) == 2
    assert seen[0].headers["x-acip-token"] == "tok-123"
    assert seen[0].url.params["route"] == "extension/module/acip/export"
    # Bare wall-clock digits — PHP must not be given an offset to shift.
    assert seen[0].url.params["since"] == "2026-06-01 10:30:00"


def test_opencart_fetch_raises_on_forbidden():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(403, json={"error": "forbidden"}))
    )
    with pytest.raises(httpx.HTTPStatusError):
        _run(_collect(fetch_opencart_changed("http://oc.local", "bad", client=client)))


# --------------------------------------------------------------------------- #
# Dispatch: which tenants have something to pull                               #
# --------------------------------------------------------------------------- #
def test_fetch_changed_since_dispatch():
    woo = {"store_url": "http://s", "woo_consumer_key": "a", "woo_consumer_secret": "b"}
    oc = {"store_url": "http://s", "oc_export_token": "t"}
    assert fetch_changed_since("woocommerce", woo, None) is not None
    assert fetch_changed_since("opencart", oc, None) is not None
    # push-only / unconfigured tenants → nothing to pull
    assert fetch_changed_since("rest", woo, None) is None
    assert fetch_changed_since("woocommerce", {"store_url": "http://s"}, None) is None
    assert fetch_changed_since("opencart", {"store_url": "http://s"}, None) is None
    assert fetch_changed_since("opencart", {"oc_export_token": "t"}, None) is None  # no url


# --------------------------------------------------------------------------- #
# Reconcile: repairs through the real pipeline, computes the watermark         #
# --------------------------------------------------------------------------- #
class _StubES:
    def __init__(self):
        self.docs: list[dict] = []

    async def index(self, **kwargs):
        self.docs.append(kwargs)


async def _changed():
    yield {"product_id": 1, "name": "کفش نایکی", "manufacturer": "نایکی",
           "categories": ["کفش"], "price": "100", "quantity": 3,
           "date_modified": "2026-06-02 09:00:00"}
    yield {"product_id": 2, "name": "کفش آدیداس", "price": "90", "quantity": 0,
           "date_modified": "2026-06-03 08:00:00"}


def test_reconcile_repairs_and_watermarks():
    es = _StubES()
    embedded: list[str] = []

    async def embed(text: str):
        embedded.append(text)
        return [0.1] * 4

    result = _run(reconcile(es, "t1", "opencart", _changed(), embed=embed))
    assert result.repaired == 2
    assert result.high_watermark == "2026-06-03 08:00:00"
    assert len(es.docs) == 2
    doc = es.docs[0]["document"]
    assert doc["tenant_id"] == "t1" and doc["title"] == "کفش نایکی"
    assert doc["brand"] == "نایکی" and doc["embedding"] == [0.1] * 4
    # Rich embedding text: brand + categories embedded with the product.
    assert "برند: نایکی" in embedded[0] and "دسته‌بندی: کفش" in embedded[0]


def test_reconcile_survives_embed_failure():
    es = _StubES()

    async def embed(_text: str):
        raise RuntimeError("TEI down")

    result = _run(reconcile(es, "t1", "opencart", _changed(), embed=embed))
    assert result.repaired == 2
    assert all("embedding" not in d["document"] for d in es.docs)
