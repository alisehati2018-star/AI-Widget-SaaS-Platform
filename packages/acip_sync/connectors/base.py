"""Connector interface + webhook signature verification (M3, GAP-B6)."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from enum import StrEnum


class EventType(StrEnum):
    UPSERT = "upsert"
    DELETE = "delete"


@dataclass
class WebhookEvent:
    """A normalised intent extracted from a store webhook."""

    type: EventType
    source: str
    product_id: str
    raw: dict


class Connector:
    """Base connector. Subclasses parse a platform's payloads."""

    source: str = "rest"

    def verify_signature(self, secret: str, body: bytes, signature: str | None) -> bool:
        """HMAC-SHA256 verification; constant-time compare. Override per platform."""
        if not secret or not signature:
            return False
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature)

    def parse(self, payload: dict) -> WebhookEvent:
        raise NotImplementedError


def get_connector(source: str) -> Connector:
    src = source.lower()
    if src == "opencart":
        from .opencart import OpenCartConnector

        return OpenCartConnector()
    if src in ("woo", "woocommerce"):
        from .woo import WooConnector

        return WooConnector()
    from .rest import RestConnector

    return RestConnector()
