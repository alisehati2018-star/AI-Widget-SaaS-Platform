"""Celery tasks — sync ingestion, reconciliation, batch embedding (M3/M4).

The fast path (`process_webhook_event`) and bulk backfill normalise → embed →
idempotently upsert (or tombstone), bump the tenant data version to invalidate
caches (REQ-M6-005), and park poison events to the DLQ (REQ-M3-005). Async work
runs inside the sync Celery task via `asyncio.run`.
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from typing import Any

from acip_cache.data_version import bump_data_version
from acip_core.clients import get_es_client, get_redis
from acip_core.logging import get_logger
from acip_embedding import get_embedding_client
from acip_sync.dlq import park
from acip_sync.ingest import tombstone_product, upsert_product
from acip_sync.normalize import normalize_product
from acip_sync.order_ingest import tombstone_order, upsert_order
from acip_sync.orders import normalize_order
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
    # Embed the rich text (title + brand + categories + attributes + description)
    # so brand/category are indexed semantically with the product, not just as
    # BM25 keyword fields.
    vector = await _embed_text(product.embedding_text()) if product.title else None
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
            raise self.retry(countdown=2**self.request.retries, exc=exc)
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


async def _apply_order_upsert(tenant_id: str, source: str, raw: dict) -> None:
    es = get_es_client()
    order = normalize_order(tenant_id, source, raw)
    await upsert_order(es, order)


@celery_app.task(name="acip.sync.process_order_webhook_event", bind=True, max_retries=3)
def process_order_webhook_event(
    self, tenant_id: str, source: str, event_type: str, order_id: str, raw: dict[str, Any]
) -> str:
    """Real-time order push (order add / status change / cancel)."""
    try:
        if event_type == "delete":
            _run(tombstone_order(get_es_client(), tenant_id, order_id))
        else:
            _run(_apply_order_upsert(tenant_id, source, raw))
        return "ok"
    except Retry:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("task.order_webhook_failed", error=str(exc), order_id=order_id)
        try:
            raise self.retry(countdown=2**self.request.retries, exc=exc)
        except MaxRetriesExceededError:
            event = {"source": source, "order_id": order_id, "raw": raw}
            _run(park(get_redis(), tenant_id, event, str(exc)))
            return "deadlettered"


@celery_app.task(name="acip.sync.bulk_import_orders")
def bulk_import_orders(tenant_id: str, source: str, orders: list[dict]) -> int:
    """Initial order-history backfill."""
    count = 0
    for raw in orders:
        try:
            _run(_apply_order_upsert(tenant_id, source, raw))
            count += 1
        except Exception as exc:  # noqa: BLE001
            _run(park(get_redis(), tenant_id, {"source": source, "raw": raw}, str(exc)))
    log.info("task.bulk_import_orders", tenant_id=tenant_id, imported=count)
    return count


async def _record_sync(tenant_id: str, source: str, status: str, watermark=None) -> None:
    from acip_core.clients import get_pg_pool

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sync_state (tenant_id, source, last_run_at, last_status, high_watermark) "
            "VALUES ($1::uuid, $2, now(), $3, $4) "
            "ON CONFLICT (tenant_id, source) "
            "DO UPDATE SET last_run_at = now(), last_status = $3, "
            "high_watermark = COALESCE($4, sync_state.high_watermark)",
            tenant_id,
            source,
            status,
            watermark,
        )


def _parse_ts(value: str | None):
    """ISO-8601 (incl. trailing Z) → aware datetime, or None."""
    if not value:
        return None
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


async def _reconcile_one(tenant_id: str, source: str) -> str:
    """Pull everything the store reports changed since the watermark and
    repair the index (M3: REQ-M3-002/012). Custom REST tenants push instead —
    for them the run just records an 'ok' heartbeat."""
    import json as _json

    from acip_core.clients import get_pg_pool
    from acip_sync.fetch import fetch_changed_since
    from acip_sync.reconcile import reconcile

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT settings FROM tenants WHERE id = $1::uuid", tenant_id)
        wm = await conn.fetchval(
            "SELECT high_watermark FROM sync_state WHERE tenant_id = $1::uuid AND source = $2",
            tenant_id,
            source,
        )
    if row is None:
        return "unknown_tenant"
    settings = row["settings"] or {}
    if isinstance(settings, str):
        try:
            settings = _json.loads(settings)
        except ValueError:
            settings = {}

    since = wm.isoformat() if wm is not None else None
    changed = fetch_changed_since(source, settings, since)
    if changed is None:
        # Nothing to pull (push-only integration or credentials not set yet).
        await _record_sync(tenant_id, source, "ok")
        return "ok"

    try:
        result = await reconcile(get_es_client(), tenant_id, source, changed, embed=_embed_text)
    except Exception as exc:  # noqa: BLE001 - store/ES unreachable: record, don't crash
        log.warning("task.reconcile_failed", tenant_id=tenant_id, source=source, error=str(exc))
        await _record_sync(tenant_id, source, "error")
        return "error"

    if result.repaired:
        await bump_data_version(get_redis(), tenant_id)
    await _record_sync(tenant_id, source, "ok", _parse_ts(result.high_watermark))
    log.info("task.reconcile_done", tenant_id=tenant_id, source=source, repaired=result.repaired)
    return f"ok:{result.repaired}"


async def _reconcile_all() -> str:
    """Beat entrypoint: reconcile every active tenant with a connected store."""
    from acip_core.clients import get_pg_pool

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, settings->>'platform' AS platform FROM tenants "
            "WHERE status = 'active' AND settings->>'platform' IN ('opencart', 'woocommerce')"
        )
    done = 0
    for r in rows:
        try:
            await _reconcile_one(str(r["id"]), str(r["platform"]))
            done += 1
        except Exception as exc:  # noqa: BLE001 - one bad tenant must not stop the sweep
            log.warning("task.reconcile_tenant_failed", tenant_id=str(r["id"]), error=str(exc))
    return f"swept:{done}/{len(rows)}"


@celery_app.task(name="acip.sync.reconcile_tenant")
def reconcile_tenant(tenant_id: str, source: str = "rest") -> str:
    """Delta reconciliation (REQ-M3-002/012) — beat sweep or single-tenant run.

    ``tenant_id="__all__"`` (the beat schedule) enumerates active tenants with
    a connected OpenCart/WooCommerce store and reconciles each from its own
    watermark. A concrete tenant id (dashboard "sync now") reconciles just that
    store. Failures are recorded in ``sync_state`` — never raised into beat.
    """
    log.info("task.reconcile", tenant_id=tenant_id, source=source)
    try:
        if tenant_id == "__all__":
            return _run(_reconcile_all())
        return _run(_reconcile_one(tenant_id, source))
    except Exception as exc:  # noqa: BLE001 - PG down: log, don't crash the beat
        log.warning("task.reconcile_record_failed", error=str(exc))
        return "failed"


@celery_app.task(name="acip.embed.batch")
def batch_embed(texts: list[str]) -> int:
    vectors = _run(get_embedding_client(redis=get_redis()).embed(texts))
    return len(vectors)


# --- Scheduled billing jobs (Phase F) ---------------------------------------- #
@celery_app.task(name="acip.billing.process_renewals")
def process_renewals_task() -> dict[str, int]:
    """Period-end processing: downgrade cancelled subs, mark others past_due."""
    from acip_billing import process_renewals
    from acip_core.clients import get_pg_pool
    from acip_core.config import get_settings

    async def _go():
        pool = await get_pg_pool()
        return await process_renewals(pool, trial_plan_code=get_settings().trial_plan_code)

    result = _run(_go())
    log.info("task.process_renewals", **result)
    return result


@celery_app.task(name="acip.billing.run_dunning")
def run_dunning_task() -> int:
    """Email every past-due subscription a payment reminder."""
    from acip_billing import list_past_due
    from acip_core.clients import get_pg_pool
    from acip_notify import dunning_email, send_email

    async def _go():
        pool = await get_pg_pool()
        due = await list_past_due(pool)
        sent = 0
        for row in due:
            if row["email"]:
                subject, text, html = dunning_email(
                    row["plan"] or "your plan", row["amount"], row["currency"] or "USD"
                )
                await send_email(row["email"], subject, text, html)
                sent += 1
        return sent

    sent = _run(_go())
    log.info("task.run_dunning", emailed=sent)
    return sent
