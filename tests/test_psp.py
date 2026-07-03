"""Hermetic tests for the ZarinPal provider and PDF invoices (Phase 10)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from acip_billing.invoice_pdf import render_invoice_pdf
from acip_billing.psp import PspError, ZarinPalProvider


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _provider(handler) -> ZarinPalProvider:
    return ZarinPalProvider(
        "m-123",
        "https://api.example/billing/callback",
        base_url="https://zp.local",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def test_request_payment_builds_startpay_redirect():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {"code": 100, "authority": "A0001"}})

    psp = _provider(handler)
    out = _run(psp.request_payment(250000.0, "پلن حرفه‌ای", email="o@shop.com"))
    assert out == {"authority": "A0001", "redirect_url": "https://zp.local/pg/StartPay/A0001"}
    import json

    body = json.loads(seen[0].read())
    assert body["merchant_id"] == "m-123" and body["amount"] == 250000
    assert body["callback_url"].endswith("/billing/callback")
    assert body["metadata"] == {"email": "o@shop.com"}


def test_request_payment_rejection_raises():
    def handler(_r: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"code": -9}, "errors": {"code": -9}})

    with pytest.raises(PspError):
        _run(_provider(handler).request_payment(1000, "x"))


def test_verify_accepts_100_and_101_and_rejects_others():
    codes = iter([100, 101, -51])

    def handler(_r: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"code": next(codes), "ref_id": 777}})

    psp = _provider(handler)
    assert _run(psp.verify("A1", 1000)) == {"ref_id": "777", "code": 100}
    assert _run(psp.verify("A1", 1000)) == {"ref_id": "777", "code": 101}
    assert _run(psp.verify("A1", 1000)) is None


def test_gateway_unreachable_raises_psp_error():
    def handler(_r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(PspError):
        _run(_provider(handler).verify("A1", 1000))


def test_invoice_pdf_renders_persian():
    pdf = render_invoice_pdf(
        number=42, store="فروشگاه تست", date="2026-07-03",
        description="اشتراک پلن حرفه‌ای", amount="1,000,000", currency="IRR",
        status_fa="پرداخت‌شده",
    )
    if pdf is None:
        pytest.skip("no Persian-capable font/engine on this machine")
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000
