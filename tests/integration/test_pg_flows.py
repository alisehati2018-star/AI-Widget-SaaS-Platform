"""PG-backed integration flows (Phase G, ES-free).

Automates the auth, tenant-isolation, RBAC, and billing-lifecycle validations
that were previously run by hand — executed over HTTP against a real uvicorn
subprocess on a live Postgres. Skipped when PG is unreachable (see
`live_client`). Elasticsearch-dependent search/RAG validation stays deferred.
"""

from __future__ import annotations

import hashlib
import hmac
import time

# Must match the conftest `live_client` server env.
_ADMIN = "integration-operator-token"
_WEBHOOK_SECRET = "integration-whsec"


def _signup(client, store="Itest"):
    email = f"it-{int(time.time() * 1000)}-{store}@shop.com".lower()
    r = client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "Sh0p-Str0ng!",
            "store_name": store,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Tests authenticate via explicit headers; drop the Set-Cookie session so a
    # persisted owner cookie can't shadow later x-admin-token calls (CSRF).
    client.cookies.clear()
    return email, body["access_token"], body.get("verify_token")


def _bearer(tok: str) -> dict:
    return {"authorization": f"Bearer {tok}"}


def test_signup_login_me(live_client):
    email, access, _ = _signup(live_client)
    me = live_client.get("/auth/me", headers=_bearer(access)).json()
    assert me["email"] == email
    assert me["role"] == "store_owner"
    # login returns a fresh token
    r = live_client.post("/auth/login", json={"email": email, "password": "Sh0p-Str0ng!"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_tenant_isolation_between_owners(live_client):
    _, a_access, _ = _signup(live_client, "Aco")
    _, b_access, _ = _signup(live_client, "Bco")
    a = live_client.get("/tenant/profile", headers=_bearer(a_access)).json()
    b = live_client.get("/tenant/profile", headers=_bearer(b_access)).json()
    # Each owner sees only their own distinct tenant.
    assert a["tenant_id"] != b["tenant_id"]
    assert a["name"] == "Aco" and b["name"] == "Bco"


def test_rbac_owner_blocked_from_admin(live_client):
    _, access, _ = _signup(live_client)
    assert live_client.get("/admin/overview", headers=_bearer(access)).status_code == 401
    # operator token works
    assert live_client.get("/admin/overview", headers={"x-admin-token": _ADMIN}).status_code == 200


def test_email_verification_gates_checkout(live_client):
    _, access, vtoken = _signup(live_client)
    # Before verification, checkout is blocked.
    r = live_client.post(
        "/tenant/billing/checkout", headers=_bearer(access), json={"plan_code": "starter"}
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_unverified"
    # Verify, then checkout works.
    assert live_client.post("/auth/verify-confirm", json={"token": vtoken}).status_code == 200
    r = live_client.post(
        "/tenant/billing/checkout", headers=_bearer(access), json={"plan_code": "starter"}
    )
    assert r.status_code == 200 and r.json()["amount"] == 49.0


def test_billing_lifecycle_end_to_end(live_client):
    email, access, vtoken = _signup(live_client, "Bill")
    live_client.post("/auth/verify-confirm", json={"token": vtoken})

    # checkout starter -> admin mark-paid -> active + invoice + credits
    order = live_client.post(
        "/tenant/billing/checkout", headers=_bearer(access), json={"plan_code": "starter"}
    ).json()
    paid = live_client.post(
        f"/admin/orders/{order['order_id']}/mark-paid", headers={"x-admin-token": _ADMIN}
    ).json()
    assert paid["status"] == "paid" and paid["kind"] == "subscription"
    assert paid["invoice_number"]
    prof = live_client.get("/tenant/profile", headers=_bearer(access)).json()
    assert prof["plan"] == "Starter" and prof["sub_status"] == "active"
    assert prof["credits"]["granted"] == 50000.0

    # proration preview for an upgrade
    pv = live_client.get("/tenant/billing/preview?plan_code=pro", headers=_bearer(access)).json()
    assert pv["base_price"] == 149.0 and 0 < pv["proration_credit"] <= 49.0

    # upgrade via signed webhook (prorated amount)
    order2 = live_client.post(
        "/tenant/billing/checkout", headers=_bearer(access), json={"plan_code": "pro"}
    ).json()
    assert order2["amount"] < 149.0
    body = f'{{"order_id":"{order2["order_id"]}","status":"paid"}}'.encode()
    sig = hmac.new(_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    wh = live_client.post(
        "/billing/webhook",
        content=body,
        headers={"x-billing-signature": sig, "content-type": "application/json"},
    )
    assert wh.status_code == 200 and wh.json()["activated"] == "pro"

    # credit top-up grants credits
    before = live_client.get("/tenant/credits", headers=_bearer(access)).json()["granted"]
    tu = live_client.post(
        "/tenant/billing/topup", headers=_bearer(access), json={"credits": 50000}
    ).json()
    assert tu["amount"] == 50.0
    live_client.post(f"/admin/orders/{tu['order_id']}/mark-paid", headers={"x-admin-token": _ADMIN})
    after = live_client.get("/tenant/credits", headers=_bearer(access)).json()["granted"]
    assert after - before == 50000.0

    # invoices recorded (starter + pro + topup)
    invs = live_client.get("/tenant/billing/invoices", headers=_bearer(access)).json()["invoices"]
    assert len(invs) >= 3

    # cancel + resume
    assert (
        live_client.post("/tenant/billing/cancel", headers=_bearer(access)).json()["status"]
        == "cancel_scheduled"
    )
    assert (
        live_client.post("/tenant/billing/resume", headers=_bearer(access)).json()["status"]
        == "resumed"
    )


def test_webhook_rejects_bad_signature(live_client):
    body = b'{"order_id":"x","status":"paid"}'
    r = live_client.post(
        "/billing/webhook",
        content=body,
        headers={"x-billing-signature": "deadbeef", "content-type": "application/json"},
    )
    assert r.status_code == 401
