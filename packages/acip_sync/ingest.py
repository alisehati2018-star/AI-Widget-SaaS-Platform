"""Idempotent ingest into Elasticsearch (M3: REQ-M3-001/003/004).

Upserts are idempotent and guarded against out-of-order writes: the document id
is deterministic (`{tenant_id}:{product_id}`) and writes use the source
`updated_at` as an external version, so re-delivering an old event is a no-op and
re-delivering the same event never corrupts the index. Deletes are tombstoned
so removed products vanish promptly.
"""

from __future__ import annotations

from datetime import datetime

from acip_core.config import get_settings
from acip_core.logging import get_logger

from .normalize import CanonicalProduct

log = get_logger("ingest")


def doc_id(tenant_id: str, product_id: str) -> str:
    return f"{tenant_id}:{product_id}"


def _version_from(updated_at: str | None) -> int | None:
    """Derive a monotonic external version from an ISO timestamp (epoch seconds)."""
    if not updated_at:
        return None
    try:
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return int(ts.timestamp())
    except (ValueError, TypeError):
        return None


async def upsert_product(
    es, product: CanonicalProduct, embedding: list[float] | None = None
) -> None:
    """Idempotent upsert with an external-version guard against stale writes."""
    s = get_settings()
    body = product.to_doc()
    if embedding is not None:
        body["embedding"] = embedding
    _id = doc_id(product.tenant_id, product.product_id)
    version = _version_from(product.updated_at)
    kwargs: dict = {"index": s.catalogue_alias, "id": _id, "document": body}
    if version is not None:
        kwargs.update(version=version, version_type="external_gte")
    try:
        await es.index(**kwargs)
    except Exception as exc:  # noqa: BLE001
        # A version conflict means a newer doc already won — safe to ignore.
        if "version_conflict" in str(exc).lower():
            log.info("ingest.stale_skipped", id=_id)
            return
        raise
    log.info("ingest.upserted", id=_id, has_vector=embedding is not None)


async def tombstone_product(es, tenant_id: str, product_id: str) -> None:
    """Propagate a delete so the product leaves search promptly (REQ-M3-004)."""
    s = get_settings()
    _id = doc_id(tenant_id, product_id)
    try:
        await es.delete(index=s.catalogue_alias, id=_id)
        log.info("ingest.tombstoned", id=_id)
    except Exception as exc:  # noqa: BLE001
        if "not_found" in str(exc).lower() or "404" in str(exc):
            return
        raise
