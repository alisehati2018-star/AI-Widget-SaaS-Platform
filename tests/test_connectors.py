"""Unit tests for product webhook connector parsing (M3: REQ-M3-007/008).

Locks in the envelope shape the shipped plugins actually send —
``{"event": "upsert"|"delete", "product": {...}}`` — for both OpenCart and
WooCommerce, matching `acip_sync.orders.parse_order_event`'s order envelope.
"""

from __future__ import annotations

from acip_sync.connectors.base import EventType, get_connector
from acip_sync.connectors.opencart import OpenCartConnector
from acip_sync.connectors.woo import WooConnector


def test_opencart_connector_parses_upsert_and_delete():
    c = OpenCartConnector()
    event = c.parse({"event": "upsert", "product": {"product_id": 42, "name": "کفش"}})
    assert event.type == EventType.UPSERT and event.product_id == "42"

    event = c.parse({"event": "delete", "product": {"product_id": 42}})
    assert event.type == EventType.DELETE and event.product_id == "42"


def test_woocommerce_connector_parses_upsert_and_delete():
    """The ACIP plugin wraps its push exactly like OpenCart's connector, not
    WooCommerce's native flat webhook shape — the connector must unwrap it."""
    c = WooConnector()
    event = c.parse({"event": "upsert", "product": {"id": 7, "name": "ساعت"}})
    assert event.type == EventType.UPSERT and event.product_id == "7"
    assert event.raw == {"id": 7, "name": "ساعت"}

    event = c.parse({"event": "delete", "product": {"id": 7}})
    assert event.type == EventType.DELETE and event.product_id == "7"


def test_get_connector_dispatches_by_source():
    assert isinstance(get_connector("opencart"), OpenCartConnector)
    assert isinstance(get_connector("woocommerce"), WooConnector)
    assert isinstance(get_connector("woo"), WooConnector)
