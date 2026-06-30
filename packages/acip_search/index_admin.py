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


# --------------------------------------------------------------------------- #
# Read / inspect surface — powers the admin Elasticsearch control panel.       #
# Everything here is non-destructive and tenant-agnostic (operator plane).     #
# --------------------------------------------------------------------------- #
async def cluster_health(es) -> dict:
    """Cluster health + a small node summary for the admin dashboard."""
    health = await es.cluster.health()
    health = dict(health)
    try:
        stats = await es.cluster.stats()
        health["nodes_total"] = stats.get("nodes", {}).get("count", {}).get("total")
        health["es_version"] = stats.get("nodes", {}).get("versions", [None])[0]
        idx = stats.get("indices", {})
        health["docs_total"] = idx.get("docs", {}).get("count")
        health["store_size_bytes"] = idx.get("store", {}).get("size_in_bytes")
    except Exception:  # noqa: BLE001 - stats are best-effort enrichment
        pass
    return health


async def list_indices(es, pattern: str | None = None) -> list[dict]:
    """List indices (defaults to the project prefix) with doc count + size."""
    s = get_settings()
    pattern = pattern or f"{s.es_index_prefix}-*"
    try:
        rows = await es.cat.indices(index=pattern, format="json", bytes="b", h=(
            "index,health,status,docs.count,docs.deleted,store.size,pri,rep,creation.date.string"
        ))
    except Exception:  # noqa: BLE001 - no matching indices yet
        return []
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "index": r.get("index"),
                "health": r.get("health"),
                "status": r.get("status"),
                "docs": _to_int(r.get("docs.count")),
                "docs_deleted": _to_int(r.get("docs.deleted")),
                "size_bytes": _to_int(r.get("store.size")),
                "shards": _to_int(r.get("pri")),
                "replicas": _to_int(r.get("rep")),
                "created": r.get("creation.date.string"),
            }
        )
    return sorted(out, key=lambda x: x.get("index") or "")


async def list_aliases(es, pattern: str | None = None) -> list[dict]:
    """Map each alias to its backing index."""
    s = get_settings()
    pattern = pattern or f"{s.es_index_prefix}-*"
    try:
        rows = await es.cat.aliases(name=pattern, format="json", h="alias,index")
    except Exception:  # noqa: BLE001
        return []
    return [{"alias": r.get("alias"), "index": r.get("index")} for r in rows]


async def get_mapping_and_settings(es, index: str) -> dict:
    """Return the mapping + settings of a concrete index or alias."""
    mapping = await es.indices.get_mapping(index=index)
    settings = await es.indices.get_settings(index=index)
    return {"mapping": _unwrap(mapping), "settings": _unwrap(settings)}


async def tenant_doc_count(es, tenant_id: str, alias: str | None = None) -> int:
    """How many catalogue docs a given store has indexed (sync verification)."""
    s = get_settings()
    alias = alias or s.catalogue_alias
    try:
        res = await es.count(index=alias, body={"query": {"term": {"tenant_id": tenant_id}}})
        return int(res.get("count", 0))
    except Exception:  # noqa: BLE001 - index may not exist yet
        return 0


async def delete_index(es, index: str) -> None:
    """Delete a concrete index (e.g. an old version after an alias swap)."""
    await es.indices.delete(index=index)
    log.info("index.deleted", index=index)


async def ensure_catalogue_index(es, alias: str | None = None, **kwargs) -> dict:
    """Idempotently ensure a catalogue index exists behind the read alias.

    If the alias already resolves to an index, this is a no-op. Otherwise a fresh
    versioned index is created and the alias is pointed at it.
    """
    s = get_settings()
    alias = alias or s.catalogue_alias
    try:
        existing = await es.indices.get_alias(name=alias)
        if existing:
            return {"status": "exists", "alias": alias, "index": next(iter(existing))}
    except Exception:  # noqa: BLE001 - alias not created yet
        pass
    new_index = shared_index_name()
    await create_index(es, new_index, **kwargs)
    await point_alias(es, alias, new_index)
    return {"status": "created", "alias": alias, "index": new_index}


def _to_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _unwrap(resp):
    """ES async client may return an ObjectApiResponse; coerce to a plain dict."""
    return dict(resp.body) if hasattr(resp, "body") else dict(resp)
