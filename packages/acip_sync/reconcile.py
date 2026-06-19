"""Delta reconciliation — the self-healing safety net (M3: REQ-M3-002/012).

Periodically compares the store's `updated_at` watermark against what the index
has and repairs anything a missed or out-of-order webhook left stale. Also
performs the initial backfill. Because reconciliation converges regardless of
webhook delivery, the system is correct even if every webhook is lost.

Phase 1 provides the reconciliation engine + watermark bookkeeping; the
store-side fetch is provided by a connector's `fetch_changed_since`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from acip_core.logging import get_logger

from .ingest import upsert_product
from .normalize import normalize_product

log = get_logger("reconcile")


@dataclass
class ReconcileResult:
    scanned: int = 0
    repaired: int = 0
    high_watermark: str | None = None


async def reconcile(
    es,
    tenant_id: str,
    source: str,
    changed: AsyncIterator[dict],
    embed=None,
) -> ReconcileResult:
    """Reindex everything the connector reports as changed since the watermark.

    `changed` yields raw store payloads; `embed` is an optional async callable
    (text) -> vector for re-embedding when text changes.
    """
    result = ReconcileResult()
    async for raw in changed:
        product = normalize_product(tenant_id, source, raw)
        vector = None
        if embed is not None and product.title:
            try:
                vector = await embed(f"{product.title}\n{product.description}")
            except Exception:  # noqa: BLE001 - embedding optional during repair
                vector = None
        await upsert_product(es, product, embedding=vector)
        result.scanned += 1
        result.repaired += 1
        wm = result.high_watermark
        if product.updated_at and (wm is None or product.updated_at > wm):
            result.high_watermark = product.updated_at
    log.info(
        "reconcile.done",
        tenant_id=tenant_id,
        source=source,
        scanned=result.scanned,
        watermark=result.high_watermark,
    )
    return result
