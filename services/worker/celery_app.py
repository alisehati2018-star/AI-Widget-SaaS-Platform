"""Celery application bootstrap (Phase 0 foundation).

The worker will run sync ingestion, reconciliation, batch embeddings, and
analytics (M3/M4/M10, Phases 1-3). Phase 0 establishes only the Celery app,
broker wiring, and a trivial health task — no business tasks.
"""

from __future__ import annotations

from acip_core.config import get_settings
from celery import Celery

settings = get_settings()

celery_app = Celery(
    "acip",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,           # idempotency-friendly; full guards land in M3
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="acip.health.ping")
def ping() -> str:
    """Liveness task used to confirm broker + worker round-trip."""
    return "pong"
