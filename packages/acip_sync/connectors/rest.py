"""Generic REST connector for non-standard carts (M3: REQ-M3-009)."""

from __future__ import annotations

from .base import Connector, EventType, WebhookEvent


class RestConnector(Connector):
    source = "rest"

    def parse(self, payload: dict) -> WebhookEvent:
        is_delete = str(payload.get("op", "upsert")).lower() == "delete"
        etype = EventType.DELETE if is_delete else EventType.UPSERT
        product = payload.get("product", payload)
        product_id = str(product.get("product_id") or product.get("id") or "")
        return WebhookEvent(type=etype, source=self.source, product_id=product_id, raw=product)
