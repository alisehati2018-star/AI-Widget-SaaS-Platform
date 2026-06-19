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


def test_v1_search_not_implemented_envelope():
    resp = client.post("/v1/search")
    assert resp.status_code == 501
    body = resp.json()
    assert body["error"]["code"] == "not_implemented"
    assert "request_id" in body["error"]
