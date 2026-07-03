"""Hermetic tests for the /admin/* IP allowlist middleware (Phase 9, SE-3)."""

from __future__ import annotations

from acip_core.middleware import AdminIpAllowlistMiddleware
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def _app(allowlist: list[str]) -> Starlette:
    async def ok(_request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/admin/tenants", ok), Route("/v1/search", ok, methods=["GET"])])
    app.add_middleware(AdminIpAllowlistMiddleware, allowlist=allowlist)
    return app


def test_allowed_ip_passes_and_public_paths_unaffected():
    client = TestClient(_app(["10.0.0.0/8"]), client=("10.1.2.3", 50000))
    assert client.get("/admin/tenants").status_code == 200
    assert client.get("/v1/search").status_code == 200


def test_blocked_ip_gets_403_envelope_only_on_admin():
    client = TestClient(_app(["10.0.0.0/8"]), client=("203.0.113.9", 50000))
    r = client.get("/admin/tenants")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ip_not_allowed"
    # Shopper/public surface is never IP-gated.
    assert client.get("/v1/search").status_code == 200


def test_single_ip_and_bad_entry_fail_closed():
    client = TestClient(_app(["203.0.113.9"]), client=("203.0.113.9", 50000))
    assert client.get("/admin/tenants").status_code == 200
    # A typo'd allowlist entry must not open the door.
    client = TestClient(_app(["not-a-cidr"]), client=("203.0.113.9", 50000))
    assert client.get("/admin/tenants").status_code == 403


def test_empty_allowlist_disables_the_gate():
    client = TestClient(_app([]), client=("203.0.113.9", 50000))
    assert client.get("/admin/tenants").status_code == 200
