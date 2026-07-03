"""Payment-provider integrations (Phase 10).

The first real gateway is **ZarinPal** (v4 REST): checkout creates a payment
request and redirects the shopper to StartPay; ZarinPal calls back with an
``Authority``; the server VERIFIES the payment server-side before activating
anything — the redirect alone never grants access.

Sandbox: point ``ZARINPAL_BASE_URL`` at ``https://sandbox.zarinpal.com`` (the
API contract is identical). Tests point it at a local fake server.
"""

from __future__ import annotations

from typing import Any

import httpx
from acip_core.logging import get_logger

log = get_logger("billing.psp")

_TIMEOUT = 15.0


class PspError(Exception):
    """The gateway rejected the request or was unreachable."""


class ZarinPalProvider:
    name = "zarinpal"

    def __init__(
        self,
        merchant_id: str,
        callback_url: str,
        *,
        base_url: str = "https://payment.zarinpal.com",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._merchant = merchant_id
        self._callback = callback_url
        self._base = base_url.rstrip("/")
        self._client = client

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        own = self._client is None
        http = self._client or httpx.AsyncClient(timeout=_TIMEOUT)
        try:
            resp = await http.post(f"{self._base}{path}", json=body)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise PspError(f"zarinpal unreachable: {exc}") from exc
        finally:
            if own:
                await http.aclose()

    async def request_payment(
        self, amount: float, description: str, *, email: str | None = None
    ) -> dict[str, str]:
        """Create a payment and return {authority, redirect_url}."""
        body: dict[str, Any] = {
            "merchant_id": self._merchant,
            "amount": int(round(amount)),
            "callback_url": self._callback,
            "description": description[:255],
        }
        if email:
            body["metadata"] = {"email": email}
        data = (await self._post("/pg/v4/payment/request.json", body)).get("data") or {}
        if data.get("code") != 100 or not data.get("authority"):
            raise PspError(f"zarinpal request rejected: code={data.get('code')}")
        authority = str(data["authority"])
        return {
            "authority": authority,
            "redirect_url": f"{self._base}/pg/StartPay/{authority}",
        }

    async def verify(self, authority: str, amount: float) -> dict[str, Any] | None:
        """Server-side verification. Returns {ref_id, code} when the payment is
        settled (code 100, or 101 = already verified); None when it is not."""
        body = {
            "merchant_id": self._merchant,
            "amount": int(round(amount)),
            "authority": authority,
        }
        data = (await self._post("/pg/v4/payment/verify.json", body)).get("data") or {}
        code = data.get("code")
        if code in (100, 101):
            return {"ref_id": str(data.get("ref_id", "")), "code": int(code)}
        log.warning("psp.verify_rejected", authority=authority, code=code)
        return None
