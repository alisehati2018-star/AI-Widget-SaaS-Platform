"""Every error leaving the API wears the standard envelope (code/message/
request_id) — including framework-raised validation and HTTP errors — and the
deep system-health endpoint aggregates every subsystem without ever raising."""

from __future__ import annotations

import pytest
from api.main import app

# Import via the same package name the app uses (services/api is on the path
# as `api`) so monkeypatching hits the module instance the routes call into.
from api.routers import admin_health_deep
from fastapi.testclient import TestClient

client = TestClient(app)


def _envelope(resp) -> dict:
    body = resp.json()
    assert set(body) == {"error"}, f"non-envelope error body: {body}"
    err = body["error"]
    assert set(err) >= {"code", "message", "request_id"}
    return err


def test_validation_error_wears_envelope():
    # A malformed JSON body fails FastAPI request validation before any
    # handler (or datastore) is touched; it used to leak the default
    # {"detail": [...]} shape instead of the envelope.
    resp = client.post(
        "/auth/login", content="not-json", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 422
    err = _envelope(resp)
    assert err["code"] == "validation_error"
    assert err["message"]  # parser summary, e.g. "JSON decode error"


def test_route_miss_404_wears_envelope():
    resp = client.get("/no/such/route")
    assert resp.status_code == 404
    assert _envelope(resp)["code"] == "not_found"


def test_method_not_allowed_wears_envelope():
    resp = client.delete("/healthz")
    assert resp.status_code == 405
    assert _envelope(resp)["code"] == "method_not_allowed"


# --- deep health -----------------------------------------------------------


async def test_probe_never_raises_and_reports_error():
    async def boom():
        raise RuntimeError("db exploded")

    out = await admin_health_deep._probe("postgres", boom)
    assert out["status"] == "error"
    assert out["latency_ms"] is None
    assert "db exploded" in out["detail"]["error"]


async def test_probe_ok_reports_latency_and_detail():
    async def fine():
        return {"migrations": "0020_x"}

    out = await admin_health_deep._probe("postgres", fine)
    assert out["status"] == "ok"
    assert out["latency_ms"] is not None
    assert out["detail"] == {"migrations": "0020_x"}


def test_deep_health_requires_admin():
    resp = client.get("/admin/health/deep")
    assert resp.status_code in (401, 403)
    assert "error" in resp.json()


def test_deep_health_aggregates_all_components(monkeypatch):
    async def ok(_name=None):
        return {}

    async def bad():
        raise RuntimeError("down")

    monkeypatch.setattr(admin_health_deep, "_check_postgres", ok)
    monkeypatch.setattr(admin_health_deep, "_check_redis", ok)
    monkeypatch.setattr(admin_health_deep, "_check_elasticsearch", bad)
    monkeypatch.setattr(admin_health_deep, "_check_queue", ok)
    monkeypatch.setattr(admin_health_deep, "_check_ai_registry", ok)

    from acip_core.config import get_settings

    token = get_settings().admin_token
    resp = client.get("/admin/health/deep", headers={"x-admin-token": token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"  # ES is down in this scenario
    by_name = {c["component"]: c for c in body["components"]}
    # Every probed subsystem plus the config-only integrations are present.
    assert set(by_name) == {
        "postgres", "redis", "elasticsearch", "queue",
        "ai_registry", "billing_psp", "email",
    }
    assert by_name["elasticsearch"]["status"] == "error"
    assert by_name["postgres"]["status"] == "ok"
    assert by_name["billing_psp"]["status"] in ("configured", "not_configured")


def test_deep_health_ok_when_all_probes_pass(monkeypatch):
    async def ok():
        return {"workers": 1}

    for name in (
        "_check_postgres", "_check_redis", "_check_elasticsearch",
        "_check_queue", "_check_ai_registry",
    ):
        monkeypatch.setattr(admin_health_deep, name, ok)

    from acip_core.config import get_settings

    resp = client.get(
        "/admin/health/deep",
        headers={"x-admin-token": get_settings().admin_token},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
