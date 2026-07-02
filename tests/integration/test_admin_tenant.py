"""Phase 1 (completion roadmap) — admin tenant-management flows.

End-to-end over HTTP against a live Postgres (same harness as
``test_pg_flows``): tenant detail profile, operator-issued keys + revoke,
manual credit adjustments, manual plan changes, operator notes, tenant list
filtering/pagination, and the overview trend series. Skipped when PG is down.
"""

from __future__ import annotations

import time

from .conftest import ADMIN_TOKEN

_HDR = {"x-admin-token": ADMIN_TOKEN}


def _create_tenant(client, prefix="p1"):
    slug = f"{prefix}-{int(time.time() * 1000)}"
    r = client.post(
        "/admin/tenants", json={"slug": slug, "name": f"Store {slug}"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["api_key"].startswith("acip_")
    return body["tenant_id"], slug


def test_tenant_detail_profile(live_client):
    tid, slug = _create_tenant(live_client, "det")
    r = live_client.get(f"/admin/tenants/{tid}", headers=_HDR)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["slug"] == slug
    assert d["status"] == "active"
    assert d["subscription"]["status"] == "none"  # provisioned directly, no sub yet
    assert d["credits"] == {"used": 0.0, "granted": 0.0, "cap": None, "within_plan": True}
    # The provisioning key is listed, masked (no hash/raw material in response).
    assert len(d["api_keys"]) == 1
    assert d["api_keys"][0]["label"] == "provisioned"
    assert "key_hash" not in d["api_keys"][0] and "api_key" not in d["api_keys"][0]
    assert d["sync_state"] == [] and d["team_size"] == 0
    # Unknown / malformed ids are a clean 404, not a 500.
    assert live_client.get("/admin/tenants/not-a-uuid", headers=_HDR).status_code == 404
    assert (
        live_client.get(
            "/admin/tenants/00000000-0000-0000-0000-000000000000", headers=_HDR
        ).status_code
        == 404
    )


def test_key_issue_and_revoke(live_client):
    tid, _ = _create_tenant(live_client, "key")
    r = live_client.post(
        f"/admin/tenants/{tid}/keys", json={"scope": "sync", "label": "ci sync"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    issued = r.json()
    assert issued["api_key"].startswith("acip_") and issued["scope"] == "sync"

    keys = live_client.get(f"/admin/tenants/{tid}/keys", headers=_HDR).json()["keys"]
    assert len(keys) == 2  # provisioned + issued
    assert {k["scope"] for k in keys} == {"widget", "sync"}

    r = live_client.post(f"/admin/tenants/{tid}/keys/{issued['id']}/revoke", headers=_HDR)
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    keys = live_client.get(f"/admin/tenants/{tid}/keys", headers=_HDR).json()["keys"]
    revoked = next(k for k in keys if k["id"] == issued["id"])
    assert revoked["revoked"] is True
    # Bad scope is rejected.
    r = live_client.post(f"/admin/tenants/{tid}/keys", json={"scope": "admin"}, headers=_HDR)
    assert r.status_code == 422


def test_manual_credit_adjustment(live_client):
    tid, _ = _create_tenant(live_client, "cr")
    r = live_client.post(
        f"/admin/tenants/{tid}/credits",
        json={"delta": 500, "reason": "goodwill grant"},
        headers=_HDR,
    )
    assert r.status_code == 200, r.text
    assert r.json()["credits"]["granted"] == 500.0
    # A deduction shows up as spend.
    r = live_client.post(f"/admin/tenants/{tid}/credits", json={"delta": -120}, headers=_HDR)
    assert r.status_code == 200
    assert r.json()["credits"] == {"used": 120.0, "granted": 500.0}
    # Zero delta is rejected.
    r = live_client.post(f"/admin/tenants/{tid}/credits", json={"delta": 0}, headers=_HDR)
    assert r.status_code == 422


def test_manual_plan_change(live_client):
    tid, _ = _create_tenant(live_client, "pl")
    r = live_client.patch(
        f"/admin/tenants/{tid}/plan",
        json={"plan_code": "starter", "status": "active", "period_days": 30},
        headers=_HDR,
    )
    assert r.status_code == 200, r.text
    d = live_client.get(f"/admin/tenants/{tid}", headers=_HDR).json()
    assert d["subscription"]["plan_code"] == "starter"
    assert d["subscription"]["status"] == "active"
    assert d["subscription"]["current_period_end"] is not None
    assert d["credits"]["cap"] == 50000.0  # starter's monthly cap now applies
    # Changing again upserts (unique subscription per tenant), not duplicates.
    r = live_client.patch(
        f"/admin/tenants/{tid}/plan", json={"plan_code": "pro"}, headers=_HDR
    )
    assert r.status_code == 200
    d = live_client.get(f"/admin/tenants/{tid}", headers=_HDR).json()
    assert d["subscription"]["plan_code"] == "pro"
    # Unknown plan → 404, bad status → 422.
    assert (
        live_client.patch(
            f"/admin/tenants/{tid}/plan", json={"plan_code": "nope"}, headers=_HDR
        ).status_code
        == 404
    )
    assert (
        live_client.patch(
            f"/admin/tenants/{tid}/plan",
            json={"plan_code": "pro", "status": "weird"},
            headers=_HDR,
        ).status_code
        == 422
    )


def test_operator_notes_roundtrip(live_client):
    tid, _ = _create_tenant(live_client, "nt")
    r = live_client.patch(
        f"/admin/tenants/{tid}/notes", json={"notes": "پیگیری فاکتور آذر"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    d = live_client.get(f"/admin/tenants/{tid}", headers=_HDR).json()
    assert d["admin_notes"] == "پیگیری فاکتور آذر"


def test_tenant_list_filter_and_pagination(live_client):
    tid, slug = _create_tenant(live_client, "ls")
    # Substring search by slug finds exactly this tenant.
    r = live_client.get(f"/admin/tenants?q={slug}", headers=_HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1 and body["tenants"][0]["id"] == tid
    # Status filter: the fresh tenant is active; searching suspended finds none.
    r = live_client.get(f"/admin/tenants?q={slug}&status=suspended", headers=_HDR)
    assert r.json()["total"] == 0
    # Pagination contract: limit is respected and total is stable.
    r = live_client.get("/admin/tenants?limit=1&offset=0", headers=_HDR)
    body = r.json()
    assert len(body["tenants"]) == 1 and body["total"] >= 1 and body["limit"] == 1


def test_overview_trends_shape(live_client):
    _create_tenant(live_client, "ov")  # guarantees at least one signup today
    r = live_client.get("/admin/overview", headers=_HDR)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("tenants", "users", "active_subscriptions", "past_due_subscriptions", "mrr"):
        assert k in d
    assert d["days"] == 30
    assert len(d["trends"]["signups"]) == 30
    assert len(d["trends"]["usage"]) == 30
    assert len(d["trends"]["revenue"]) == 30
    assert len(d["trends"]["failed_payments"]) == 30
    # Today's bucket (last point) includes the tenant we just created.
    assert d["trends"]["signups"][-1]["signups"] >= 1
    assert d["totals"]["signups"] >= 1
    # The days param is honoured and clamped.
    week = live_client.get("/admin/overview?days=7", headers=_HDR).json()
    assert len(week["trends"]["signups"]) == 7
    assert live_client.get("/admin/overview?days=500", headers=_HDR).json()["days"] == 90


def test_admin_endpoints_reject_without_auth(live_client):
    tid, _ = _create_tenant(live_client, "az")
    for method, path, body in [
        ("get", f"/admin/tenants/{tid}", None),
        ("get", f"/admin/tenants/{tid}/keys", None),
        ("post", f"/admin/tenants/{tid}/keys", {"scope": "widget"}),
        ("post", f"/admin/tenants/{tid}/credits", {"delta": 5}),
        ("patch", f"/admin/tenants/{tid}/plan", {"plan_code": "free"}),
        ("patch", f"/admin/tenants/{tid}/notes", {"notes": "x"}),
    ]:
        fn = getattr(live_client, method)
        r = fn(path, json=body) if body is not None else fn(path)
        assert r.status_code == 401, f"{method} {path} -> {r.status_code}"
