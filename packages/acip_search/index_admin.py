"""Index lifecycle (M2: REQ-M2-009/010, M12-006).

Catalogue indices are addressed through a read **alias** so a schema/analyzer
change is a zero-downtime alias swap with instant rollback. Small tenants share
one index (+ routing + the tenant_id filter); large tenants can get a dedicated
index. Phase 1 defaults to the shared shape.
"""

from __future__ import annotations

import time

from acip_core.config import get_settings
from acip_core.logging import get_logger

from .analyzer import ANALYSIS_SETTINGS
from .mapping import catalogue_mapping

log = get_logger("index_admin")


def shared_index_name(version: str | None = None) -> str:
    s = get_settings()
    version = version or time.strftime("%Y%m%d%H%M%S")
    return f"{s.es_index_prefix}-catalogue-{version}"


def tenant_index_name(tenant_id: str, version: str | None = None) -> str:
    s = get_settings()
    version = version or time.strftime("%Y%m%d%H%M%S")
    return f"{s.es_index_prefix}-catalogue-{tenant_id}-{version}"


def index_body(
    dims: int | None = None, shards: int | None = None, replicas: int | None = None
) -> dict:
    s = get_settings()
    return {
        "settings": {
            "number_of_shards": shards if shards is not None else s.index_shards,
            "number_of_replicas": replicas if replicas is not None else s.index_replicas,
            **ANALYSIS_SETTINGS,
        },
        "mappings": catalogue_mapping(dims if dims is not None else s.embedding_dims),
    }


async def create_index(es, name: str, **kwargs) -> None:
    """Create a concrete index with the analyzer + mapping."""
    await es.indices.create(index=name, body=index_body(**kwargs))
    log.info("index.created", index=name)


async def point_alias(es, alias: str, to_index: str) -> None:
    """Atomically point `alias` at `to_index`, removing it from any other index."""
    actions = [{"add": {"index": to_index, "alias": alias}}]
    try:
        existing = await es.indices.get_alias(name=alias)
        for old in existing:
            if old != to_index:
                actions.insert(0, {"remove": {"index": old, "alias": alias}})
    except Exception:  # noqa: BLE001 - alias may not exist yet
        pass
    await es.indices.update_aliases(body={"actions": actions})
    log.info("alias.swapped", alias=alias, index=to_index)


async def reindex_and_swap(es, source_index: str, alias: str | None = None, **kwargs) -> str:
    """Build a fresh index, reindex into it, then swap the read alias (M12-006).

    Returns the new index name. The old index is retained for instant rollback.
    """
    s = get_settings()
    alias = alias or s.catalogue_alias
    new_index = shared_index_name()
    await create_index(es, new_index, **kwargs)
    await es.reindex(
        body={"source": {"index": source_index}, "dest": {"index": new_index}},
        wait_for_completion=True,
    )
    await point_alias(es, alias, new_index)
    return new_index
