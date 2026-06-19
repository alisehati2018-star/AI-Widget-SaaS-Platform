"""Datastore client factories (lazy singletons) for the Elastic spine,
PostgreSQL control plane, and Redis cache/queue."""

from .elasticsearch import es_ready, get_es_client
from .postgres import get_pg_pool, pg_ready
from .redis import get_redis, redis_ready

__all__ = [
    "get_es_client",
    "es_ready",
    "get_pg_pool",
    "pg_ready",
    "get_redis",
    "redis_ready",
]
