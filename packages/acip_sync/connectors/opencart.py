"""OpenCart connector (M3: REQ-M3-007)."""

from __future__ import annotations

from .base import Connector, EventType, WebhookEvent


class OpenCartConnector(Connector):
    source = "opencart"

    def parse(self, payload: dict) -> WebhookEvent:
        event = str(payload.get("event", "upsert")).lower()
        etype = EventType.DELETE if "delete" in event else EventType.UPSERT
        product = payload.get("product", payload)
        product_id = str(product.get("product_id") or product.get("id") or "")
        return WebhookEvent(type=etype, source=self.source, product_id=product_id, raw=product)
