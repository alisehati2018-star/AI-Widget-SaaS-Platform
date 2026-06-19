"""Celery tasks — sync ingestion, reconciliation, batch embedding (M3/M4).

The fast path (`process_webhook_event`) and bulk backfill normalise → embed →
idempotently upsert (or tombstone), bump the tenant data version to invalidate
caches (REQ-M6-005), and park poison events to the DLQ (REQ-M3-005). Async work
runs inside the sync Celery task via `asyncio.run`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from acip_cache.data_version import bump_data_version
from acip_core.clients import get_es_client, get_redis
from acip_core.logging import get_logger
from acip_embedding import get_embedding_client
from acip_sync.dlq import park
from acip_sync.ingest import tombstone_product, upsert_product
from acip_sync.normalize import normalize_product
from celery.exceptions import MaxRetriesExceededError, Retry

from .celery_app import celery_app

log = get_logger("worker.tasks")

# A single, persistent event loop per worker process. The datastore clients
# (AsyncElasticsearch, redis.asyncio, httpx) are cached singletons bound to the
# loop at first use; `asyncio.run` would create — and then close — a new loop on
# every task, leaving those clients pinned to a closed loop and breaking the 2nd
# task onward. A long-lived loop keeps them valid for the process lifetime.
_loop: asyncio.AbstractEventLoop | None = None


def _run(coro):
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


async def _embed_text(text: str) -> list[float] | None:
    try:
        return await get_embedding_client(redis=get_redis()).embed_one(text)
    except Exception:  # noqa: BLE001 - embedding is optional; degrade to lexical doc
        return None


async def _apply_upsert(tenant_id: str, source: str, raw: dict) -> None:
    es = get_es_client()
    product = normalize_product(tenant_id, source, raw)
    vector = await _embed_text(f"{product.title}\n{product.description}") if product.title else None
    await upsert_product(es, product, embedding=vector)
    await bump_data_version(get_redis(), tenant_id)


@celery_app.task(name="acip.sync.process_webhook_event", bind=True, max_retries=3)
def process_webhook_event(
    self, tenant_id: str, source: str, event_type: str, product_id: str, raw: dict[str, Any]
) -> str:
    try:
        if event_type == "delete":
            _run(tombstone_product(get_es_client(), tenant_id, product_id))
            _run(bump_data_version(get_redis(), tenant_id))
        else:
            _run(_apply_upsert(tenant_id, source, raw))
        return "ok"
    except Retry:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("task.webhook_failed", error=str(exc), product_id=product_id)
        try:
            raise self.retry(countdown=2 ** self.request.retries, exc=exc)
        except MaxRetriesExceededError:
            event = {"source": source, "product_id": product_id, "raw": raw}
            _run(park(get_redis(), tenant_id, event, str(exc)))
            return "deadlettered"


@celery_app.task(name="acip.sync.bulk_import")
def bulk_import(tenant_id: str, source: str, products: list[dict]) -> int:
    """Initial backfill / bulk import (REQ-M3-002)."""
    count = 0
    for raw in products:
        try:
            _run(_apply_upsert(tenant_id, source, raw))
            count += 1
        except Exception as exc:  # noqa: BLE001
            _run(park(get_redis(), tenant_id, {"source": source, "raw": raw}, str(exc)))
    log.info("task.bulk_import", tenant_id=tenant_id, imported=count)
    return count


@celery_app.task(name="acip.sync.reconcile_tenant")
def reconcile_tenant(tenant_id: str, source: str = "rest") -> str:
    """Periodic delta reconciliation hook (REQ-M3-002/012).

    Phase 1 scaffolds the schedule + entry point; the store-side
    `fetch_changed_since` fetch is provided per-connector when a live store is
    configured. Without one this is a no-op that records its run.
    """
    log.info("task.reconcile", tenant_id=tenant_id, source=source)
    return "scheduled"


@celery_app.task(name="acip.embed.batch")
def batch_embed(texts: list[str]) -> int:
    vectors = _run(get_embedding_client(redis=get_redis()).embed(texts))
    return len(vectors)
