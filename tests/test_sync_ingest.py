"""Unit tests for ingest idempotency helpers (M3: REQ-M3-001/003)."""

from __future__ import annotations

from acip_sync.ingest import _version_from, doc_id


def test_doc_id_is_deterministic_and_tenant_scoped():
    assert doc_id("t1", "42") == "t1:42"
    assert doc_id("t1", "42") != doc_id("t2", "42")


def test_version_from_iso_is_monotonic():
    v1 = _version_from("2026-01-01T00:00:00Z")
    v2 = _version_from("2026-01-02T00:00:00Z")
    assert v1 is not None and v2 is not None and v2 > v1


def test_version_from_handles_missing_and_bad():
    assert _version_from(None) is None
    assert _version_from("not-a-date") is None
