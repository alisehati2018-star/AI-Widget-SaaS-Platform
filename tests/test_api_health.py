"""Smoke tests for the API foundation (REQ-M12-003): app builds, health works,
trace id is echoed, and unimplemented endpoints return the 501 envelope."""

from __future__ import annotations

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_healthz_ok():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_trace_id_header_echoed():
    resp = client.get("/healthz", headers={"x-request-id": "test-trace-123"})
    assert resp.headers.get("x-request-id") == "test-trace-123"


def test_trace_id_generated_when_absent():
    resp = client.get("/healthz")
    assert resp.headers.get("x-request-id")


def test_v1_search_requires_api_key():
    # Phase 1: /v1/search is implemented and tenant-scoped. Without a key it must
    # reject before touching any datastore (isolation: no tenant -> no query).
    resp = client.post("/v1/search", json={"query": "گوشی"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "unauthorized"
    assert "request_id" in body["error"]


def test_v1_chat_still_not_implemented():
    # Chat is Phase 2 (M7) — still a 501 contract skeleton.
    resp = client.post("/v1/chat")
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "not_implemented"
