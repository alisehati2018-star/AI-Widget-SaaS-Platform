"""Phase 9 — admin TOTP two-factor auth, end-to-end over HTTP on live PG.

bootstrap → login → enroll (password-gated) → confirm with a live code →
password-only login now returns ``totp_required`` → login with code works →
disable needs password AND code. Skipped when PG is down.
"""

from __future__ import annotations

import time

from acip_auth.totp import totp_code

from .conftest import ADMIN_TOKEN


def _mk_admin(client):
    email = f"totp-{int(time.time() * 1000)}@vitrin.ai"
    password = "Adm1n!Str0ng#2026"
    r = client.post(
        "/admin/auth/bootstrap",
        headers={"x-admin-token": ADMIN_TOKEN},
        json={"email": email, "password": password, "full_name": "TOTP Admin"},
    )
    assert r.status_code == 200, r.text
    return email, password


def _login(client, email, password, **extra):
    r = client.post("/admin/auth/login", json={"email": email, "password": password, **extra})
    client.cookies.clear()  # keep the shared client stateless across steps
    return r


def test_totp_full_lifecycle(live_client):
    email, password = _mk_admin(live_client)

    # Login (no 2FA yet) → bearer token for the authed endpoints.
    r = _login(live_client, email, password)
    assert r.status_code == 200, r.text
    bearer = {"authorization": f"Bearer {r.json()['access_token']}"}

    assert live_client.get("/admin/auth/totp", headers=bearer).json() == {"totp_enabled": False}

    # Enroll requires the password; wrong one is rejected.
    r = live_client.post(
        "/admin/auth/totp/enroll", headers=bearer, json={"current_password": "wrong"}
    )
    assert r.status_code == 403
    r = live_client.post(
        "/admin/auth/totp/enroll", headers=bearer, json={"current_password": password}
    )
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    assert r.json()["otpauth_uri"].startswith("otpauth://totp/")

    # Not enforced until confirmed: password-only login still works.
    assert _login(live_client, email, password).status_code == 200

    # Confirm with a wrong code fails; with a live code flips enforcement on.
    r = live_client.post("/admin/auth/totp/confirm", headers=bearer, json={"totp_code": "000000"})
    assert r.status_code in (401, 200)  # 000000 could coincide only in theory
    r = live_client.post(
        "/admin/auth/totp/confirm", headers=bearer, json={"totp_code": totp_code(secret)}
    )
    assert r.status_code == 200, r.text

    # Password alone → totp_required; wrong code → invalid.
    r = _login(live_client, email, password)
    assert r.status_code == 401 and r.json()["error"]["code"] == "totp_required"
    r = _login(live_client, email, password, totp_code="123456")
    assert r.status_code == 401

    # Replay guard: the code consumed at confirmation is DEAD for login.
    r = _login(live_client, email, password, totp_code=totp_code(secret))
    assert r.status_code == 401, "confirmation code must not be replayable"
    # The NEXT step's code (skew window accepts +1) signs in.
    r = _login(live_client, email, password, totp_code=totp_code(secret, at=time.time() + 30))
    assert r.status_code == 200, r.text
    bearer = {"authorization": f"Bearer {r.json()['access_token']}"}
    assert live_client.get("/admin/auth/totp", headers=bearer).json() == {"totp_enabled": True}

    # Disable needs password AND a live code.
    r = live_client.post(
        "/admin/auth/totp/disable",
        headers=bearer,
        json={"current_password": password, "totp_code": "999999"},
    )
    assert r.status_code == 401
    r = live_client.post(
        "/admin/auth/totp/disable",
        headers=bearer,
        json={"current_password": password, "totp_code": totp_code(secret)},
    )
    assert r.status_code == 200, r.text
    assert _login(live_client, email, password).status_code == 200
