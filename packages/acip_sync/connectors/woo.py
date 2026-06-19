"""WooCommerce connector (M3: REQ-M3-008).

WooCommerce signs webhooks with a base64 HMAC-SHA256 in `x-wc-webhook-signature`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from .base import Connector, EventType, WebhookEvent


class WooConnector(Connector):
    source = "woocommerce"

    def verify_signature(self, secret: str, body: bytes, signature: str | None) -> bool:
        if not secret or not signature:
            return False
        digest = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
        return hmac.compare_digest(digest, signature)

    def parse(self, payload: dict) -> WebhookEvent:
        # Woo sends the full product object; a delete arrives with status/action hints.
        action = str(payload.get("action") or payload.get("status") or "").lower()
        etype = EventType.DELETE if action in ("delete", "trash") else EventType.UPSERT
        product_id = str(payload.get("id") or "")
        return WebhookEvent(type=etype, source=self.source, product_id=product_id, raw=payload)
