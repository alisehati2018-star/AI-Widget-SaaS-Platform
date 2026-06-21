"""Phase D — security headers + CSRF middleware (hermetic, via TestClient)."""

from __future__ import annotations

from acip_core.middleware import CsrfMiddleware, SecurityHeadersMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CsrfMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=True)

    @app.get("/g")
    def g():
        return {"ok": True}

    @app.post("/p")
    def p():
        return {"ok": True}

    return app


def test_security_headers_present():
    client = TestClient(_app())
    r = client.get("/g")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in r.headers
    assert "strict-transport-security" in r.headers  # hsts=True


def test_csrf_exempts_bearer_and_no_cookie():
    client = TestClient(_app())
    # No cookie at all → not CSRF-applicable.
    assert client.post("/p").status_code == 200
    # Bearer present → exempt even with a cookie.
    r = client.post("/p", headers={"authorization": "Bearer x"}, cookies={"vitrin_access": "t"})
    assert r.status_code == 200


def test_csrf_blocks_cookie_without_token_and_allows_with_match():
    client = TestClient(_app())
    # Cookie-authenticated unsafe request without CSRF header → 403.
    r = client.post("/p", cookies={"vitrin_access": "t"})
    assert r.status_code == 403
    # Double-submit match → allowed.
    r2 = client.post(
        "/p",
        cookies={"vitrin_access": "t", "vitrin_csrf": "abc"},
        headers={"x-csrf-token": "abc"},
    )
    assert r2.status_code == 200
