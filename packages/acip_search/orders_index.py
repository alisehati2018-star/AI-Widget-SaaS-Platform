"""Order index lifecycle — sibling of `index_admin.py` for the orders alias.

Same alias-swap pattern as the catalogue index (M12-006): orders are addressed
through a read alias so the mapping can evolve without downtime.
"""

from __future__ import annotations

import time

from acip_core.config import get_settings
from acip_core.logging import get_logger

from .analyzer import ANALYSIS_SETTINGS
from .index_admin import point_alias
from .order_mapping import order_mapping

log = get_logger("orders_index")


def order_index_name(version: str | None = None) -> str:
    s = get_settings()
    version = version or time.strftime("%Y%m%d%H%M%S")
    return f"{s.es_index_prefix}-orders-{version}"


def order_index_body(shards: int | None = None, replicas: int | None = None) -> dict:
    s = get_settings()
    return {
        "settings": {
            "number_of_shards": shards if shards is not None else s.index_shards,
            "number_of_replicas": replicas if replicas is not None else s.index_replicas,
            **ANALYSIS_SETTINGS,
        },
        "mappings": order_mapping(),
    }


async def ensure_orders_index(es, alias: str | None = None) -> dict:
    """Idempotently ensure an orders index exists behind the read alias."""
    s = get_settings()
    alias = alias or s.orders_alias
    try:
        existing = await es.indices.get_alias(name=alias)
        if existing:
            return {"status": "exists", "alias": alias, "index": next(iter(existing))}
    except Exception:  # noqa: BLE001 - alias not created yet
        pass
    new_index = order_index_name()
    await es.indices.create(index=new_index, body=order_index_body())
    await point_alias(es, alias, new_index)
    log.info("orders_index.created", index=new_index)
    return {"status": "created", "alias": alias, "index": new_index}


async def tenant_order_count(es, tenant_id: str, alias: str | None = None) -> int:
    s = get_settings()
    alias = alias or s.orders_alias
    try:
        res = await es.count(index=alias, body={"query": {"term": {"tenant_id": tenant_id}}})
        return int(res.get("count", 0))
    except Exception:  # noqa: BLE001 - index may not exist yet
        return 0
