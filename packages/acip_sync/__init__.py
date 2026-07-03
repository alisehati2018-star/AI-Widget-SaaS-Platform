"""Data sync & store integration (M3).

Two-track sync: event-driven webhooks as the fast path, periodic delta
reconciliation as the self-healing safety net. Idempotent upserts, tombstone
deletes, a dead-letter queue, and pluggable connectors (OpenCart, WooCommerce,
custom REST) keep the index correct even if every webhook is lost.
"""

from .fetch import fetch_changed_since, fetch_opencart_changed, fetch_woo_changed
from .ingest import doc_id, tombstone_product, upsert_product
from .normalize import CanonicalProduct, normalize_product
from .reconcile import ReconcileResult, reconcile

__all__ = [
    "CanonicalProduct",
    "normalize_product",
    "upsert_product",
    "tombstone_product",
    "doc_id",
    "reconcile",
    "ReconcileResult",
    "fetch_changed_since",
    "fetch_woo_changed",
    "fetch_opencart_changed",
]
