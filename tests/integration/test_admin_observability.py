"""Phase 3 (completion roadmap) — admin observability & security flows.

End-to-end over HTTP against a live Postgres (same harness as
``test_admin_tenant``): audit filters + cursor, usage filters + CSV export,
queue worker introspection shape, manual account unlock on both identity
planes, and the degraded (never 500) behaviour of the ES-backed analytics
endpoints. Skipped when PG is down.
"""

from __future__ import annotations

import asyncio
import time

from .conftest import ADMIN_TOKEN

_HDR = {"x-admin-token": ADMIN_TOKEN}


def _stamp() -> str:
    return str(int(time.time() * 1000))


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


async def _sql(query: str, *args):
    import asyncpg
    from acip_core.config import get_settings

    conn = await asyncpg.connect(dsn=get_settings().pg_dsn, timeout=5)
    try:
        return await conn.fetchval(query, *args)
    finally:
        await conn.close()


def _create_tenant(client, prefix):
    slug = f"{prefix}-{_stamp()}"
    r = client.post(
        "/admin/tenants", json={"slug": slug, "name": f"Store {slug}"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    return r.json()["tenant_id"], slug


# --------------------------------------------------------------------------- #
# Audit browser                                                                #
# --------------------------------------------------------------------------- #
def test_audit_filters_and_cursor(live_client):
    tid, slug = _create_tenant(live_client, "aud")
    # Generate a few more tenant-scoped audit rows.
    live_client.patch(f"/admin/tenants/{tid}/notes", json={"notes": "x"}, headers=_HDR)
    live_client.post(
        f"/admin/tenants/{tid}/credits", json={"delta": 10, "reason": "t"}, headers=_HDR
    )

    # Tenant filter: every returned row belongs to our tenant.
    r = live_client.get("/admin/audit", params={"tenant": slug}, headers=_HDR)
    assert r.status_code == 200, r.text
    entries = r.json()["entries"]
    assert len(entries) >= 3
    assert all(e["tenant"] == slug for e in entries)

    # Action-prefix filter narrows to tenant.* rows only.
    r = live_client.get(
        "/admin/audit", params={"tenant": slug, "action": "tenant.credit"}, headers=_HDR
    )
    acts = {e["action"] for e in r.json()["entries"]}
    assert acts == {"tenant.credit_adjust"}

    # Actor filter + a date window that must contain today's rows.
    from datetime import date, timedelta

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = live_client.get(
        "/admin/audit",
        params={"tenant": slug, "actor": "operator", "date_from": today, "date_to": today},
        headers=_HDR,
    )
    assert len(r.json()["entries"]) >= 3
    # An empty future window returns nothing.
    r = live_client.get(
        "/admin/audit", params={"tenant": slug, "date_from": tomorrow}, headers=_HDR
    )
    assert r.json()["entries"] == []
    # Malformed dates are a clean 422.
    assert (
        live_client.get("/admin/audit", params={"date_from": "junk"}, headers=_HDR).status_code
        == 422
    )

    # Keyset cursor: page of 1 yields a cursor; the next page starts below it.
    r = live_client.get(
        "/admin/audit", params={"tenant": slug, "limit": 1}, headers=_HDR
    ).json()
    assert len(r["entries"]) == 1 and r["next_cursor"] is not None
    r2 = live_client.get(
        "/admin/audit",
        params={"tenant": slug, "limit": 1, "cursor": r["next_cursor"]},
        headers=_HDR,
    ).json()
    assert r2["entries"] and r2["entries"][0]["id"] < r["entries"][0]["id"]


# --------------------------------------------------------------------------- #
# Usage monitoring + CSV export                                                #
# --------------------------------------------------------------------------- #
def test_usage_filters_and_csv_export(live_client):
    tid, slug = _create_tenant(live_client, "usg")
    _run(_sql(
        "INSERT INTO usage_events (tenant_id, route, rung, tokens_in, tokens_out, cost) "
        "VALUES ($1::uuid, '/v1/search', 'L1', 10, 5, 0.001) RETURNING id",
        tid,
    ))
    _run(_sql(
        "INSERT INTO usage_events (tenant_id, route, rung, tokens_in, tokens_out, cost) "
        "VALUES ($1::uuid, '/v1/chat', 'L3', 200, 80, 0.02) RETURNING id",
        tid,
    ))

    # Tenant filter isolates our two events; rung filter narrows to one.
    r = live_client.get("/admin/usage", params={"tenant": slug}, headers=_HDR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["calls"] == 2 and len(body["events"]) == 2
    assert {e["route"] for e in body["events"]} == {"/v1/search", "/v1/chat"}
    r = live_client.get(
        "/admin/usage", params={"tenant": slug, "rung": "L3"}, headers=_HDR
    ).json()
    assert r["calls"] == 1 and r["events"][0]["route"] == "/v1/chat"
    r = live_client.get(
        "/admin/usage", params={"tenant": slug, "route": "search"}, headers=_HDR
    ).json()
    assert r["calls"] == 1 and r["by_rung"] == [{"rung": "L1", "count": 1}]

    # CSV export honours the same filter and ships as a download.
    r = live_client.get(
        "/admin/usage", params={"tenant": slug, "fmt": "csv"}, headers=_HDR
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    lines = [ln for ln in r.text.strip().splitlines() if ln]
    assert lines[0].startswith("occurred_at,tenant,route,rung")
    assert len(lines) == 3  # header + our two events
    assert any("/v1/chat" in ln for ln in lines[1:])


# --------------------------------------------------------------------------- #
# Queue worker introspection                                                   #
# --------------------------------------------------------------------------- #
def test_queue_reports_broker_and_workers_shape(live_client):
    r = live_client.get("/admin/queue", headers=_HDR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"broker", "reachable", "pending", "workers"}
    assert isinstance(body["workers"], list)
    for w in body["workers"]:  # only present when a live worker answers
        assert set(w) >= {"name", "status", "active_tasks", "active_count", "registered"}


# --------------------------------------------------------------------------- #
# Manual unlock (both identity planes)                                         #
# --------------------------------------------------------------------------- #
def test_security_unlock_admin_plane(live_client):
    email = f"locked-{_stamp()}@vitrin.test"
    password = "Str0ng!Passw0rd-p3"
    r = live_client.post(
        "/admin/operators", json={"email": email, "password": password}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    # Lock the account artificially, as repeated failed logins would.
    _run(_sql(
        "UPDATE admin_users SET failed_logins = 9, "
        "locked_until = now() + interval '1 hour' WHERE email = $1 RETURNING id",
        email,
    ))
    r = live_client.post("/admin/auth/login", json={"email": email, "password": password})
    assert r.status_code == 429  # locked out

    # The lock shows up on the security page, tagged with its plane.
    sec = live_client.get("/admin/security", headers=_HDR).json()
    mine = [a for a in sec["locked_accounts"] if a["email"] == email]
    assert mine and mine[0]["plane"] == "admin"

    # Manual unlock → login works immediately.
    r = live_client.post(
        "/admin/security/unlock", json={"email": email, "plane": "admin"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    r = live_client.post("/admin/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    live_client.cookies.clear()

    # Unknown account and bad plane are clean errors.
    assert (
        live_client.post(
            "/admin/security/unlock",
            json={"email": "ghost@nowhere.test", "plane": "admin"},
            headers=_HDR,
        ).status_code
        == 404
    )
    assert (
        live_client.post(
            "/admin/security/unlock", json={"email": email, "plane": "junk"}, headers=_HDR
        ).status_code
        == 422
    )
    # Clean up the operator.
    ops = live_client.get("/admin/operators", headers=_HDR).json()["operators"]
    op_id = next(o["id"] for o in ops if o["email"] == email)
    live_client.delete(f"/admin/operators/{op_id}", headers=_HDR)


# --------------------------------------------------------------------------- #
# Degraded flags instead of 500 when Elasticsearch is down                     #
# --------------------------------------------------------------------------- #
def _es_reachable() -> bool:
    import httpx
    from acip_core.config import get_settings

    try:
        return httpx.get(get_settings().es_host, timeout=2).status_code < 500
    except Exception:  # noqa: BLE001
        return False


def test_analytics_degrade_instead_of_500(live_client):
    tid, _ = _create_tenant(live_client, "deg")
    es_up = _es_reachable()

    r = live_client.get("/admin/analytics", params={"tenant": tid}, headers=_HDR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"four_dimensions", "most_wanted", "zero_results", "funnel", "degraded"}
    r = live_client.get("/admin/insight", params={"tenant": tid}, headers=_HDR)
    assert r.status_code == 200, r.text
    assert "insight" in r.json() and "degraded" in r.json()
    r = live_client.get("/admin/zero-results", params={"tenant": tid}, headers=_HDR)
    assert r.status_code == 200, r.text
    r = live_client.post(
        "/admin/analyst", params={"tenant": tid}, json={"question": "پرفروش‌ها؟"}, headers=_HDR
    )
    assert r.status_code == 200, r.text
    assert "degraded" in r.json()

    if not es_up:
        # The acceptance case proper: ES down ⇒ flagged degraded, empty data.
        body = live_client.get(
            "/admin/analytics", params={"tenant": tid}, headers=_HDR
        ).json()
        assert body["degraded"] is True
        assert body["most_wanted"] == [] and body["zero_results"] == []


def test_health_reports_latency_and_history(live_client):
    r = live_client.get("/admin/health", headers=_HDR)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"status", "dependencies", "latency_ms", "history"}
    assert body["dependencies"]["postgres"] == "ok"
    assert isinstance(body["latency_ms"]["postgres"], int)
    # Two calls accumulate history samples (Redis-backed).
    r2 = live_client.get("/admin/health", headers=_HDR).json()
    if r2["dependencies"]["redis"] == "ok":
        assert len(r2["history"]) >= 2
        assert {"ts", "ok", "total", "pg_ms"} <= set(r2["history"][-1])


def test_models_ping_shape(live_client):
    r = live_client.post("/admin/models/ping", headers=_HDR)
    assert r.status_code == 200, r.text
    services = r.json()["services"]
    assert set(services) == {"embeddings", "reranker", "llm"}
    for info in services.values():
        assert {"configured", "reachable", "latency_ms"} <= set(info)
