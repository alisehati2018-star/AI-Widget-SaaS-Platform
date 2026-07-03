"""Unit tests for order ingest idempotency helpers (sibling of test_sync_ingest.py)."""

from __future__ import annotations

from acip_sync.order_ingest import _version_from, order_doc_id


def test_order_doc_id_is_deterministic_and_tenant_scoped():
    assert order_doc_id("t1", "1007") == "t1:1007"
    assert order_doc_id("t1", "1007") != order_doc_id("t2", "1007")


def test_order_version_from_iso_is_monotonic():
    v1 = _version_from("2026-01-01T00:00:00Z")
    v2 = _version_from("2026-01-02T00:00:00Z")
    assert v1 is not None and v2 is not None and v2 > v1


def test_order_version_from_handles_missing_and_bad():
    assert _version_from(None) is None
    assert _version_from("not-a-date") is None
