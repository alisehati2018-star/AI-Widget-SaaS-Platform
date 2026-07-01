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

    @app.post("/admin/p")
    def admin_p():
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


def test_csrf_protects_the_admin_cookie_pair_on_admin_paths():
    """/admin/* paths are checked against the admin cookie pair
    (vitrin_admin_access/vitrin_admin_csrf) — a fully separate identity plane
    from the customer one, with the same double-submit protection."""
    client = TestClient(_app())
    # Admin cookie present, no CSRF header → 403.
    r = client.post("/admin/p", cookies={"vitrin_admin_access": "t"})
    assert r.status_code == 403
    # Double-submit match on the admin pair → allowed.
    r2 = client.post(
        "/admin/p",
        cookies={"vitrin_admin_access": "t", "vitrin_admin_csrf": "xyz"},
        headers={"x-csrf-token": "xyz"},
    )
    assert r2.status_code == 200


def test_csrf_admin_and_customer_cookies_do_not_cross_contaminate():
    """A stale/unrelated cookie from the *other* plane must never affect the
    check for the plane the path actually belongs to: a customer path only
    ever looks at the customer pair, an admin path only at the admin pair."""
    client = TestClient(_app())
    # Valid customer double-submit on a non-admin path; a mismatched, unrelated
    # admin cookie present in the same browser must not cause a 403.
    r = client.post(
        "/p",
        cookies={"vitrin_access": "t", "vitrin_csrf": "abc", "vitrin_admin_access": "other"},
        headers={"x-csrf-token": "abc"},
    )
    assert r.status_code == 200
    # And the reverse: a valid admin double-submit on an admin path must not be
    # blocked by an unrelated, mismatched customer cookie.
    r2 = client.post(
        "/admin/p",
        cookies={"vitrin_admin_access": "t", "vitrin_admin_csrf": "xyz", "vitrin_access": "other"},
        headers={"x-csrf-token": "xyz"},
    )
    assert r2.status_code == 200
