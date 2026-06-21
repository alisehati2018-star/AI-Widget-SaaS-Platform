"""Celery application bootstrap.

Runs sync ingestion, reconciliation, and batch embeddings (M3/M4). Phase 1 adds
the sync/embedding tasks (in `worker.tasks`) and a periodic reconciliation
beat schedule — the self-healing safety net (REQ-M3-002).
"""

from __future__ import annotations

from acip_core.config import get_settings
from celery import Celery

settings = get_settings()

celery_app = Celery(
    "acip",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks"],
)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,           # idempotency-friendly; guarded upserts in M3
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Reconciliation cadence; tenants are enumerated by the task in M11/M3.
        "reconcile-sync": {
            "task": "acip.sync.reconcile_tenant",
            "schedule": 900.0,  # every 15 minutes
            "args": ("__all__", "rest"),
        },
        # Billing period-end processing (downgrade cancelled, mark past_due).
        "billing-renewals": {
            "task": "acip.billing.process_renewals",
            "schedule": 86400.0,  # daily
        },
        # Dunning reminders to past-due subscriptions.
        "billing-dunning": {
            "task": "acip.billing.run_dunning",
            "schedule": 86400.0,  # daily
        },
    },
)


@celery_app.task(name="acip.health.ping")
def ping() -> str:
    """Liveness task used to confirm broker + worker round-trip."""
    return "pong"
