"""Phase 2 (completion roadmap) — admin revenue/plans/inbox/operators flows.

End-to-end over HTTP against a live Postgres (same harness as
``test_admin_tenant``): plan create/delete lifecycle + public visibility,
platform invoice listing, the contact inbox triage flow, and operator
(admin user) CRUD with its self/last-admin safety rails. Skipped when PG
is down.
"""

from __future__ import annotations

import time

from .conftest import ADMIN_TOKEN

_HDR = {"x-admin-token": ADMIN_TOKEN}


def _stamp() -> str:
    return str(int(time.time() * 1000))


# --------------------------------------------------------------------------- #
# Plans CRUD                                                                   #
# --------------------------------------------------------------------------- #
def test_plan_create_public_visibility_and_delete(live_client):
    code = f"p2-{_stamp()}"
    r = live_client.post(
        "/admin/plans",
        json={
            "code": code,
            "name": "Phase2 Plan",
            "price_monthly": 49.5,
            "credits_per_month": 12000,
            "monthly_credit_cap": 20000,
            "is_public": True,
            "sort_order": 5,
        },
        headers=_HDR,
    )
    assert r.status_code == 200, r.text
    plan_id = r.json()["plan_id"]

    # Appears in the admin list with the submitted numbers.
    plans = live_client.get("/admin/plans", headers=_HDR).json()["plans"]
    mine = next(p for p in plans if p["code"] == code)
    assert mine["price_monthly"] == 49.5 and mine["credits_per_month"] == 12000.0

    # Acceptance: the new plan shows up on the PUBLIC /plans page data.
    public = live_client.get("/plans").json()["plans"]
    assert any(p["code"] == code for p in public)

    # Hidden plans disappear from the public list but stay in admin.
    live_client.patch(f"/admin/plans/{plan_id}", json={"is_public": False}, headers=_HDR)
    public = live_client.get("/plans").json()["plans"]
    assert not any(p["code"] == code for p in public)

    # Unused plan deletes cleanly; a second delete is a 404.
    assert live_client.delete(f"/admin/plans/{plan_id}", headers=_HDR).status_code == 200
    assert live_client.delete(f"/admin/plans/{plan_id}", headers=_HDR).status_code == 404


def test_plan_create_validation_and_conflicts(live_client):
    # Bad code / missing name are 422s.
    r = live_client.post("/admin/plans", json={"code": "UPPER!", "name": "x"}, headers=_HDR)
    assert r.status_code == 422
    r = live_client.post("/admin/plans", json={"code": f"ok-{_stamp()}"}, headers=_HDR)
    assert r.status_code == 422
    # Duplicate code is a 409.
    code = f"dup-{_stamp()}"
    assert (
        live_client.post(
            "/admin/plans", json={"code": code, "name": "A"}, headers=_HDR
        ).status_code
        == 200
    )
    r = live_client.post("/admin/plans", json={"code": code, "name": "B"}, headers=_HDR)
    assert r.status_code == 409
    # Clean up the survivor.
    plans = live_client.get("/admin/plans", headers=_HDR).json()["plans"]
    pid = next(p["id"] for p in plans if p["code"] == code)
    live_client.delete(f"/admin/plans/{pid}", headers=_HDR)


def test_plan_in_use_cannot_be_deleted(live_client):
    code = f"used-{_stamp()}"
    plan_id = live_client.post(
        "/admin/plans", json={"code": code, "name": "Used"}, headers=_HDR
    ).json()["plan_id"]
    slug = f"pu-{_stamp()}"
    tid = live_client.post(
        "/admin/tenants", json={"slug": slug, "name": slug}, headers=_HDR
    ).json()["tenant_id"]
    r = live_client.patch(f"/admin/tenants/{tid}/plan", json={"plan_code": code}, headers=_HDR)
    assert r.status_code == 200, r.text
    r = live_client.delete(f"/admin/plans/{plan_id}", headers=_HDR)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "plan_in_use"


# --------------------------------------------------------------------------- #
# Invoices                                                                     #
# --------------------------------------------------------------------------- #
def test_invoice_listing_and_summary(live_client):
    r = live_client.get("/admin/invoices", headers=_HDR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"invoices", "total", "paid_amount", "paid_count", "limit", "offset"}
    for inv in body["invoices"]:
        assert set(inv) >= {
            "id", "number", "tenant_slug", "tenant_name",
            "description", "amount", "currency", "status", "created_at",
        }
    # Status filter narrows to paid rows only.
    paid = live_client.get("/admin/invoices", params={"status": "paid"}, headers=_HDR).json()
    assert all(i["status"] == "paid" for i in paid["invoices"])
    # A nonsense tenant search returns an empty, well-formed page.
    none = live_client.get(
        "/admin/invoices", params={"q": "no-such-tenant-xyz"}, headers=_HDR
    ).json()
    assert none["total"] == 0 and none["invoices"] == []


# --------------------------------------------------------------------------- #
# Contact inbox                                                                #
# --------------------------------------------------------------------------- #
def test_contact_inbox_triage_flow(live_client):
    email = f"visitor-{_stamp()}@example.com"
    r = live_client.post(
        "/contact", json={"name": "بازدیدکننده", "email": email, "message": "سوال دربارهٔ پلن‌ها"}
    )
    assert r.status_code == 200, r.text

    # The submission lands in the admin inbox as status=new.
    inbox = live_client.get("/admin/contact", params={"q": email}, headers=_HDR).json()
    assert inbox["total"] == 1
    msg = inbox["messages"][0]
    assert msg["status"] == "new" and msg["message"] == "سوال دربارهٔ پلن‌ها"

    # Triage: mark read + attach an operator note.
    r = live_client.patch(
        f"/admin/contact/{msg['id']}",
        json={"status": "read", "admin_note": "پاسخ داده شد از طریق ایمیل"},
        headers=_HDR,
    )
    assert r.status_code == 200, r.text
    after = live_client.get("/admin/contact", params={"q": email}, headers=_HDR).json()
    assert after["messages"][0]["status"] == "read"
    assert after["messages"][0]["admin_note"] == "پاسخ داده شد از طریق ایمیل"
    assert after["messages"][0]["updated_at"] is not None

    # Status filter + global counts stay consistent.
    unread = live_client.get(
        "/admin/contact", params={"status": "new", "q": email}, headers=_HDR
    ).json()
    assert unread["total"] == 0
    assert set(inbox["counts"]) == {"all", "new", "read", "resolved"}

    # Bad status value and unknown id are clean errors.
    assert (
        live_client.patch(
            f"/admin/contact/{msg['id']}", json={"status": "junk"}, headers=_HDR
        ).status_code
        == 422
    )
    assert (
        live_client.patch(
            "/admin/contact/999999999", json={"status": "read"}, headers=_HDR
        ).status_code
        == 404
    )


# --------------------------------------------------------------------------- #
# Operators (admin_users CRUD)                                                 #
# --------------------------------------------------------------------------- #
_PASSWORD = "Str0ng!Passw0rd-p2"


def _create_operator(client, tag: str) -> tuple[str, str]:
    email = f"op-{tag}-{_stamp()}@vitrin.test"
    r = client.post(
        "/admin/operators",
        json={"email": email, "password": _PASSWORD, "full_name": f"Operator {tag}"},
        headers=_HDR,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"], email


def test_operator_crud_without_bootstrap(live_client):
    # Acceptance: a second admin is created WITHOUT /admin/auth/bootstrap.
    op_id, email = _create_operator(live_client, "crud")
    ops = live_client.get("/admin/operators", headers=_HDR).json()["operators"]
    mine = next(o for o in ops if o["id"] == op_id)
    assert mine["email"] == email and mine["status"] == "active" and mine["sessions"] == 0

    # The new operator can actually sign in on the admin plane.
    r = live_client.post("/admin/auth/login", json={"email": email, "password": _PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "platform_admin"
    # Drop the session cookies the login set — the rest of the test drives the
    # operator-token path, and lingering auth cookies would trip CSRF checks.
    live_client.cookies.clear()

    # Rename sticks.
    r = live_client.patch(
        f"/admin/operators/{op_id}", json={"full_name": "نام جدید"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    ops = live_client.get("/admin/operators", headers=_HDR).json()["operators"]
    assert next(o for o in ops if o["id"] == op_id)["full_name"] == "نام جدید"

    # Suspend revokes live sessions and blocks login; re-activate restores it.
    r = live_client.post(
        f"/admin/operators/{op_id}/status", json={"status": "suspended"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    r = live_client.post("/admin/auth/login", json={"email": email, "password": _PASSWORD})
    assert r.status_code == 403
    live_client.cookies.clear()
    ops = live_client.get("/admin/operators", headers=_HDR).json()["operators"]
    assert next(o for o in ops if o["id"] == op_id)["sessions"] == 0
    live_client.post(f"/admin/operators/{op_id}/status", json={"status": "active"}, headers=_HDR)

    # Delete removes the account entirely.
    assert live_client.delete(f"/admin/operators/{op_id}", headers=_HDR).status_code == 200
    ops = live_client.get("/admin/operators", headers=_HDR).json()["operators"]
    assert not any(o["id"] == op_id for o in ops)
    assert live_client.delete(f"/admin/operators/{op_id}", headers=_HDR).status_code == 404


def test_operator_safety_rails(live_client):
    # Weak password / bad email rejected; duplicate email is a 409.
    r = live_client.post(
        "/admin/operators", json={"email": "not-an-email", "password": _PASSWORD}, headers=_HDR
    )
    assert r.status_code == 422
    op_id, email = _create_operator(live_client, "rails")
    r = live_client.post(
        "/admin/operators", json={"email": email, "password": _PASSWORD}, headers=_HDR
    )
    assert r.status_code == 409
    r = live_client.post(
        "/admin/operators", json={"email": f"w-{_stamp()}@vitrin.test", "password": "123"},
        headers=_HDR,
    )
    assert r.status_code == 422

    # A signed-in admin cannot suspend or delete THEMSELF.
    r = live_client.post("/admin/auth/login", json={"email": email, "password": _PASSWORD})
    bearer = {"authorization": f"Bearer {r.json()['access_token']}"}
    live_client.cookies.clear()
    r = live_client.post(
        f"/admin/operators/{op_id}/status", json={"status": "suspended"}, headers=bearer
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "self_action"
    r = live_client.delete(f"/admin/operators/{op_id}", headers=bearer)
    assert r.status_code == 409 and r.json()["error"]["code"] == "self_action"

    # The /admin/operators surface itself requires admin auth.
    assert live_client.get("/admin/operators").status_code == 401

    live_client.delete(f"/admin/operators/{op_id}", headers=_HDR)


def test_last_active_admin_is_protected(live_client):
    """With exactly one active admin left, suspend/delete must be refused."""
    op_id, _ = _create_operator(live_client, "last")
    ops = live_client.get("/admin/operators", headers=_HDR).json()["operators"]
    # Suspend every OTHER active admin so ours is the last one standing.
    others = [o for o in ops if o["id"] != op_id and o["status"] == "active"]
    try:
        for o in others:
            r = live_client.post(
                f"/admin/operators/{o['id']}/status", json={"status": "suspended"}, headers=_HDR
            )
            assert r.status_code == 200, r.text
        r = live_client.post(
            f"/admin/operators/{op_id}/status", json={"status": "suspended"}, headers=_HDR
        )
        assert r.status_code == 409 and r.json()["error"]["code"] == "last_admin"
        r = live_client.delete(f"/admin/operators/{op_id}", headers=_HDR)
        assert r.status_code == 409 and r.json()["error"]["code"] == "last_admin"
    finally:
        for o in others:
            live_client.post(
                f"/admin/operators/{o['id']}/status", json={"status": "active"}, headers=_HDR
            )
        live_client.delete(f"/admin/operators/{op_id}", headers=_HDR)
