"""Store connectors (M3: REQ-M3-007/008/009).

Each connector parses its platform's webhook payloads and verifies the webhook
signature (closes GAP-B6), exposing a uniform interface to the ingest path.
"""

from .base import Connector, WebhookEvent, get_connector

__all__ = ["Connector", "WebhookEvent", "get_connector"]
