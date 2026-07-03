"""Idempotent order ingest into Elasticsearch — sibling of `ingest.py`.

Same idempotency guarantee as the product pipeline: the document id is
deterministic (`{tenant_id}:{order_id}`) and writes use the source
`updated_at` as an external version, so a re-delivered or out-of-order event
never corrupts the index.
"""

from __future__ import annotations

from datetime import datetime

from acip_core.config import get_settings
from acip_core.logging import get_logger

from .orders import CanonicalOrder

log = get_logger("order_ingest")


def order_doc_id(tenant_id: str, order_id: str) -> str:
    return f"{tenant_id}:{order_id}"


def _version_from(updated_at: str | None) -> int | None:
    if not updated_at:
        return None
    try:
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return int(ts.timestamp())
    except (ValueError, TypeError):
        return None


async def upsert_order(es, order: CanonicalOrder) -> None:
    """Idempotent upsert with an external-version guard against stale writes."""
    s = get_settings()
    body = order.to_doc()
    _id = order_doc_id(order.tenant_id, order.order_id)
    version = _version_from(order.updated_at)
    kwargs: dict = {"index": s.orders_alias, "id": _id, "document": body}
    if version is not None:
        kwargs.update(version=version, version_type="external_gte")
    try:
        await es.index(**kwargs)
    except Exception as exc:  # noqa: BLE001
        if "version_conflict" in str(exc).lower():
            log.info("order_ingest.stale_skipped", id=_id)
            return
        raise
    log.info("order_ingest.upserted", id=_id)


async def tombstone_order(es, tenant_id: str, order_id: str) -> None:
    """Propagate a delete/cancel so the order leaves the index promptly."""
    s = get_settings()
    _id = order_doc_id(tenant_id, order_id)
    try:
        await es.delete(index=s.orders_alias, id=_id)
        log.info("order_ingest.tombstoned", id=_id)
    except Exception as exc:  # noqa: BLE001
        if "not_found" in str(exc).lower() or "404" in str(exc):
            return
        raise
