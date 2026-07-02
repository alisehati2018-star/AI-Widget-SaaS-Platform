"""Phase 5 (completion roadmap) — owner-dashboard flows.

End-to-end over HTTP against a live Postgres (same harness as
``test_pg_flows``): catalogue sync status + manual trigger, degraded (never
500) tenant analytics with ES down, and the printable HTML invoice. Skipped
when PG is down.
"""

from __future__ import annotations

import asyncio
import time

from .conftest import ADMIN_TOKEN

_HDR = {"x-admin-token": ADMIN_TOKEN}


def _signup(client, store="P5"):
    email = f"p5-{int(time.time() * 1000)}-{store}@shop.com".lower()
    r = client.post(
        "/auth/signup",
        json={"email": email, "password": "Sh0p-Str0ng!", "store_name": store},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    client.cookies.clear()
    return email, body["access_token"], body["user"]["tenant_id"]


def _bearer(tok: str) -> dict:
    return {"authorization": f"Bearer {tok}"}


async def _sql(query: str, *args):
    import asyncpg
    from acip_core.config import get_settings

    conn = await asyncpg.connect(dsn=get_settings().pg_dsn, timeout=5)
    try:
        return await conn.fetchval(query, *args)
    finally:
        await conn.close()


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --------------------------------------------------------------------------- #
# Sync status + manual trigger                                                 #
# --------------------------------------------------------------------------- #
def test_sync_status_and_trigger(live_client):
    _, access, _tid = _signup(live_client, "sync")

    # Fresh store: no sync rows yet; the ES doc count degrades (null) when the
    # cluster is unreachable but the endpoint still answers 200.
    r = live_client.get("/tenant/sync-status", headers=_bearer(access))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sources"] == []
    assert set(body) >= {"sources", "docs_indexed", "degraded"}

    # "Sync now" records the request immediately (queued/recorded), visible in
    # the status even if no worker is running.
    r = live_client.post(
        "/tenant/sync/trigger", json={"source": "opencart"}, headers=_bearer(access)
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("queued", "recorded")
    r = live_client.get("/tenant/sync-status", headers=_bearer(access))
    sources = r.json()["sources"]
    assert len(sources) == 1
    assert sources[0]["source"] == "opencart"
    assert sources[0]["last_status"] in ("queued", "ok")
    assert sources[0]["last_run_at"] is not None

    # Bad source is a clean 422; anonymous callers are rejected.
    assert (
        live_client.post(
            "/tenant/sync/trigger", json={"source": "junk"}, headers=_bearer(access)
        ).status_code
        == 422
    )
    assert live_client.post("/tenant/sync/trigger", json={}).status_code == 401
    assert live_client.get("/tenant/sync-status").status_code == 401


# --------------------------------------------------------------------------- #
# Degraded flags on the owner analytics surfaces (ES down ⇒ 200, not 500)      #
# --------------------------------------------------------------------------- #
def _es_reachable() -> bool:
    import httpx
    from acip_core.config import get_settings

    try:
        return httpx.get(get_settings().es_host, timeout=2).status_code < 500
    except Exception:  # noqa: BLE001
        return False


def test_owner_analytics_degrade_instead_of_500(live_client):
    _, access, _tid = _signup(live_client, "deg")
    r = live_client.get("/tenant/analytics", headers=_bearer(access))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"four_dimensions", "most_wanted", "zero_results", "funnel", "degraded"}
    r = live_client.get("/tenant/insight", headers=_bearer(access))
    assert r.status_code == 200, r.text
    assert "insight" in r.json() and "degraded" in r.json()
    r = live_client.get("/tenant/zero-results", headers=_bearer(access))
    assert r.status_code == 200, r.text
    assert "degraded" in r.json()

    if not _es_reachable():
        body = live_client.get("/tenant/analytics", headers=_bearer(access)).json()
        assert body["degraded"] is True
        assert body["most_wanted"] == [] and body["zero_results"] == []


# --------------------------------------------------------------------------- #
# Printable HTML invoice                                                       #
# --------------------------------------------------------------------------- #
def test_invoice_html_download(live_client):
    _, access, tid = _signup(live_client, "inv")
    number = _run(_sql(
        "INSERT INTO invoices (tenant_id, description, amount, currency, status) "
        "VALUES ($1::uuid, 'اشتراک ماهانهٔ پلن Pro', 149.00, 'USD', 'paid') RETURNING number",
        tid,
    ))

    # The invoice shows up in the tenant list and renders as standalone HTML.
    r = live_client.get("/tenant/billing/invoices", headers=_bearer(access))
    assert any(i["number"] == number for i in r.json()["invoices"])
    r = live_client.get(f"/tenant/billing/invoices/{number}/html", headers=_bearer(access))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/html")
    assert "اشتراک ماهانهٔ پلن Pro" in r.text and "پرداخت‌شده" in r.text

    # Another tenant cannot fetch it; unknown numbers 404.
    _, other_access, _ = _signup(live_client, "inv2")
    assert (
        live_client.get(
            f"/tenant/billing/invoices/{number}/html", headers=_bearer(other_access)
        ).status_code
        == 404
    )
    assert (
        live_client.get(
            "/tenant/billing/invoices/999999999/html", headers=_bearer(access)
        ).status_code
        == 404
    )
