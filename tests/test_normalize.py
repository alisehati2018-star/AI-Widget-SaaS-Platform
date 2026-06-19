"""Unit tests for connector payload normalization (M3: REQ-M3-010)."""

from __future__ import annotations

from acip_sync.normalize import normalize_product


def test_opencart_normalization():
    raw = {
        "product_id": 42,
        "name": "کفش ورزشی",
        "description": "راحت",
        "manufacturer": "Nike",
        "categories": ["کفش"],
        "price": "199.9",
        "quantity": 5,
        "date_modified": "2026-01-01T00:00:00Z",
    }
    p = normalize_product("t1", "opencart", raw)
    assert p.product_id == "42"
    assert p.title == "کفش ورزشی"
    assert p.brand == "Nike"
    assert p.price == 199.9
    assert p.in_stock is True
    assert p.tenant_id == "t1"


def test_woocommerce_normalization_out_of_stock():
    raw = {
        "id": 7,
        "name": "ساعت",
        "stock_status": "outofstock",
        "price": "50",
        "categories": [{"name": "اکسسوری"}],
        "attributes": [{"name": "رنگ", "options": ["مشکی"]}],
    }
    p = normalize_product("t1", "woocommerce", raw)
    assert p.product_id == "7"
    assert p.in_stock is False
    assert p.categories == ["اکسسوری"]
    assert p.attributes == {"رنگ": ["مشکی"]}


def test_rest_canonical_and_doc_drops_nones():
    raw = {"id": "x1", "title": "تیشرت", "in_stock": True}
    p = normalize_product("t1", "rest", raw)
    doc = p.to_doc()
    assert doc["product_id"] == "x1"
    assert doc["tenant_id"] == "t1"
    # None-valued fields (e.g. price/brand) are dropped from the doc.
    assert "price" not in doc and "brand" not in doc
