"""Unit tests for order payload normalization + webhook envelope parsing."""

from __future__ import annotations

from acip_sync.orders import normalize_order, parse_order_event


def test_opencart_order_normalization():
    raw = {
        "order_id": 1007,
        "firstname": "علی",
        "lastname": "صحتی",
        "email": "ali@example.com",
        "total": "189000",
        "currency_code": "IRR",
        "order_status": "در حال پردازش",
        "date_added": "2026-07-01T09:00:00",
        "date_modified": "2026-07-01T09:00:00",
        "products": [{"product_id": 42, "name": "گوشی", "quantity": "1", "price": "189000"}],
    }
    o = normalize_order("t1", "opencart", raw)
    assert o.order_id == "1007"
    assert o.customer_name == "علی صحتی"
    assert o.customer_email == "ali@example.com"
    assert o.total == 189000.0
    assert o.currency == "IRR"
    assert len(o.items) == 1 and o.items[0].product_id == "42" and o.items[0].quantity == 1


def test_woocommerce_order_normalization():
    raw = {
        "id": 88,
        "status": "processing",
        "billing": {"email": "b@shop.com", "first_name": "سارا", "last_name": "احمدی"},
        "line_items": [{"product_id": 7, "name": "کیف", "quantity": 2, "price": "50"}],
        "total": "100",
        "currency": "USD",
        "date_created_gmt": "2026-07-01T09:00:00",
        "date_modified_gmt": "2026-07-01T09:30:00",
    }
    o = normalize_order("t1", "woocommerce", raw)
    assert o.order_id == "88"
    assert o.customer_name == "سارا احمدی"
    assert o.currency == "USD"
    assert o.items[0].quantity == 2


def test_rest_order_to_doc_drops_nones():
    raw = {"order_id": "x1", "status": "paid", "total": 10}
    o = normalize_order("t1", "rest", raw)
    doc = o.to_doc()
    assert doc["order_id"] == "x1" and doc["tenant_id"] == "t1"
    assert "customer_email" not in doc and "items" not in doc


def test_parse_order_event_upsert_and_delete_envelope():
    etype, order_id, order = parse_order_event(
        "opencart", {"event": "upsert", "order": {"order_id": 5, "total": 10}}
    )
    assert etype == "upsert" and order_id == "5" and order["total"] == 10

    etype, order_id, order = parse_order_event(
        "woocommerce", {"event": "delete", "order": {"id": 9}}
    )
    assert etype == "delete" and order_id == "9"


def test_parse_order_event_status_change_is_always_upsert():
    """A cancelled/refunded order stays in the index (status is just updated) —
    only an explicit `event: delete` tombstones the document."""
    etype, _order_id, order = parse_order_event(
        "woocommerce", {"event": "upsert", "order": {"id": 3, "status": "cancelled"}}
    )
    assert etype == "upsert" and order["status"] == "cancelled"
