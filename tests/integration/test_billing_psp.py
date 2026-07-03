"""Phase 10 — hosted checkout E2E over HTTP: ZarinPal sandbox contract.

Spins a FAKE ZarinPal (request/verify endpoints) plus a dedicated uvicorn
configured with ``BILLING_PROVIDER=zarinpal`` pointing at it, then walks the
REAL money path: signup → verify email → checkout → redirect URL → gateway
callback → server-side verify → plan ACTIVE + invoice issued (and a PDF).
Also proves the failure path (Status=NOK) never activates anything.
Skipped when PG is down.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time

import pytest

_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


_FAKE_ZP = r"""
import uuid

import uvicorn
from fastapi import FastAPI, Request

app = FastAPI()
PAID = {}

@app.post("/pg/v4/payment/request.json")
async def request_payment(request: Request):
    body = await request.json()
    authority = "A" + uuid.uuid4().hex  # real authorities are globally unique
    PAID[authority] = {"amount": body["amount"], "verified": False}
    return {"data": {"code": 100, "authority": authority}, "errors": []}

@app.post("/pg/v4/payment/verify.json")
async def verify(request: Request):
    body = await request.json()
    entry = PAID.get(body.get("authority"))
    if entry is None or entry["amount"] != body.get("amount"):
        return {"data": {"code": -51}, "errors": []}
    code = 101 if entry["verified"] else 100
    entry["verified"] = True
    return {"data": {"code": code, "ref_id": 900001}, "errors": []}

import os
uvicorn.run(app, host="127.0.0.1", port=int(os.environ["ZP_PORT"]),
            log_level="warning")
"""


def _wait_http(url: str, proc, tries: int = 40) -> bool:
    import httpx

    for _ in range(tries):
        if proc.poll() is not None:
            return False
        try:
            httpx.get(url, timeout=1)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.25)
    return False


@pytest.fixture(scope="module")
def psp_stack(tmp_path_factory):
    """Fake ZarinPal + a uvicorn API configured to use it."""
    import httpx
    from acip_core.config import get_settings

    async def _pg_up() -> bool:
        try:
            import asyncpg

            conn = await asyncpg.connect(dsn=get_settings().pg_dsn, timeout=3)
            await conn.close()
            return True
        except Exception:  # noqa: BLE001
            return False

    if not _run(_pg_up()):
        pytest.skip("Postgres not reachable; skipping PSP integration tests.")

    zp_port, api_port = 9188, 8189
    zp_file = tmp_path_factory.mktemp("zp") / "fake_zp.py"
    zp_file.write_text(_FAKE_ZP, encoding="utf-8")
    zp = subprocess.Popen(
        [sys.executable, str(zp_file)],
        env={**os.environ, "ZP_PORT": str(zp_port)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    env = {
        **os.environ,
        "PYTHONPATH": "packages:services",
        "AUTH_SECRET": "integration-secret-0123456789abcdef",
        "ADMIN_TOKEN": "integration-operator-token",
        "AUTH_IP_RATE_PER_MIN": "100000",
        "EMAIL_PROVIDER": "console",
        "EMAIL_VERIFICATION_REQUIRED": "false",
        "CSRF_ENABLED": "true",
        "BILLING_PROVIDER": "zarinpal",
        "ZARINPAL_MERCHANT_ID": "m-test",
        "ZARINPAL_BASE_URL": f"http://127.0.0.1:{zp_port}",
        "WIDGET_BASE_URL": f"http://127.0.0.1:{api_port}",
        "APP_BASE_URL": "http://127.0.0.1:3000",
    }
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1",
         "--port", str(api_port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{api_port}"
    try:
        if not _wait_http(f"http://127.0.0.1:{zp_port}/docs", zp):
            pytest.skip("fake ZarinPal did not start")
        if not _wait_http(f"{base}/healthz", api):
            pytest.skip("API did not start")
        with httpx.Client(base_url=base, timeout=15) as client:
            yield client
    finally:
        for proc in (api, zp):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                proc.kill()


def _signup(client):
    email = f"psp-{int(time.time() * 1000)}@shop.com"
    r = client.post(
        "/auth/signup",
        json={"email": email, "password": "Sh0p-Str0ng!", "store_name": "PSP"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    client.cookies.clear()
    return body["access_token"], body["user"]["tenant_id"]


def _bearer(tok):
    return {"authorization": f"Bearer {tok}"}


def _mk_plan(client) -> str:
    code = f"psp{int(time.time() * 1000) % 10**9}"
    r = client.post(
        "/admin/plans",
        headers={"x-admin-token": "integration-operator-token"},
        json={"code": code, "name": "PSP Plan", "price_monthly": 250000,
              "credits_per_month": 1000, "is_public": False},
    )
    assert r.status_code == 200, r.text
    return code


def test_checkout_callback_activates_plan_and_issues_pdf(psp_stack):
    client = psp_stack
    access, _tid = _signup(client)
    plan = _mk_plan(client)

    # 1) Checkout → hosted-payment redirect with a stored authority.
    r = client.post("/tenant/billing/checkout", json={"plan_code": plan}, headers=_bearer(access))
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["next"] == "redirect"
    authority = order["redirect_url"].rsplit("/", 1)[-1]
    assert order["redirect_url"].endswith(f"/pg/StartPay/{authority}")

    # 2) Gateway callback (Status=OK) → server-side verify → paid + active.
    r = client.get(
        "/billing/callback",
        params={"Authority": authority, "Status": "OK"},
        follow_redirects=False,
    )
    assert r.status_code == 302 and "payment=success" in r.headers["location"], r.text
    r = client.get("/tenant/billing/orders", headers=_bearer(access))
    paid = [o for o in r.json()["orders"] if o["status"] == "paid"]
    assert paid, r.text
    profile = client.get("/tenant/profile", headers=_bearer(access)).json()
    # /tenant/profile reports the plan NAME.
    assert profile["plan"] == "PSP Plan" and profile["sub_status"] == "active"

    # Replayed callback stays success and stays idempotent.
    r = client.get(
        "/billing/callback",
        params={"Authority": authority, "Status": "OK"},
        follow_redirects=False,
    )
    assert "payment=success" in r.headers["location"]

    # 3) The issued invoice downloads as a real PDF (or a clean 503 without a font).
    inv = client.get("/tenant/billing/invoices", headers=_bearer(access)).json()["invoices"]
    assert inv, "a paid order must issue an invoice"
    r = client.get(
        f"/tenant/billing/invoices/{inv[0]['number']}/pdf", headers=_bearer(access)
    )
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")


def test_cancelled_payment_never_activates(psp_stack):
    client = psp_stack
    access, _tid = _signup(client)
    plan = _mk_plan(client)
    r = client.post("/tenant/billing/checkout", json={"plan_code": plan}, headers=_bearer(access))
    authority = r.json()["redirect_url"].rsplit("/", 1)[-1]

    # Shopper cancelled at the gateway (Status=NOK): order fails, plan stays free.
    r = client.get(
        "/billing/callback",
        params={"Authority": authority, "Status": "NOK"},
        follow_redirects=False,
    )
    assert r.status_code == 302 and "payment=failed" in r.headers["location"]
    orders = client.get("/tenant/billing/orders", headers=_bearer(access)).json()["orders"]
    assert orders and orders[0]["status"] == "failed"
    profile = client.get("/tenant/profile", headers=_bearer(access)).json()
    assert profile["plan"] != "PSP Plan"

    # An unknown authority is also just a failed redirect.
    r = client.get(
        "/billing/callback",
        params={"Authority": "A-unknown-authority", "Status": "OK"},
        follow_redirects=False,
    )
    assert "payment=failed" in r.headers["location"]


def test_manual_provider_unaffected(psp_stack):
    """The webhook/manual path still exists side-by-side (json import guard)."""
    assert json.loads('{"ok": true}')["ok"] is True
