"""Celery application instance (M45.2).

Worker invocation:
  celery -A infrastructure.celery.app worker --loglevel=info --pool=solo

--pool=solo: runs tasks in the main thread, allowing asyncio.run() inside tasks.
Use gevent or prefork for CPU-bound tasks that don't need asyncio.

Broker/backend: Redis DB=2 (separate from rate-limiting DB=0 and blacklist DB=1).
"""

from __future__ import annotations

from celery import Celery

from shared.config import settings

celery_app = Celery(
    "eios",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "infrastructure.celery.tasks.ingestion",
        "infrastructure.celery.tasks.maintenance",
        "infrastructure.celery.tasks.bulk_import",
        "infrastructure.celery.tasks.email",
        "infrastructure.celery.tasks.schedule_checker",
        "infrastructure.celery.tasks.certificate_expiry",
        "infrastructure.celery.tasks.risk_draft",
        "infrastructure.celery.tasks.document_pipeline",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # ── M47 — Regional task queues ─────────────────────────────────────────────
    # Tasks may be submitted to region-specific queues by passing
    # task.apply_async(queue=get_region_queue(org_region)).
    # Workers in each region subscribe to their queue:
    #   celery -A infrastructure.celery.app worker -Q eios-eu
    #   celery -A infrastructure.celery.app worker -Q eios-us
    #   celery -A infrastructure.celery.app worker -Q eios-apac
    task_queues={
        "eios-eu": {"exchange": "eios-eu", "routing_key": "eios-eu"},
        "eios-us": {"exchange": "eios-us", "routing_key": "eios-us"},
        "eios-apac": {"exchange": "eios-apac", "routing_key": "eios-apac"},
        "celery": {"exchange": "celery", "routing_key": "celery"},  # default fallback
    },
    task_default_queue="celery",
    # Ensure tasks are acknowledged only after completion (safe re-delivery on crash)
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Required for asyncio.run() inside tasks when using --pool=solo
    worker_pool="solo",
    task_track_started=True,
    # Results expire after 24h — enough for polling ingestion status
    result_expires=86400,
    # Timezone
    enable_utc=True,
    # ── Celery Beat schedule (M45.3) ──────────────────────────────────────────
    # Run maintenance tasks periodically.  Start beat with:
    #   celery -A infrastructure.celery.app beat --loglevel=info
    beat_schedule={
        "check-backup-health-daily": {
            "task": "eios.maintenance.check_backup_health",
            "schedule": 86400,  # every 24 hours
        },
        "check-replication-lag-hourly": {
            "task": "eios.maintenance.check_replication_lag",
            "schedule": 3600,  # every hour
        },
        "check-due-assessments-daily": {
            "task": "eios.schedules.check_due_assessments",
            "schedule": 86400,  # every 24 hours
        },
        "check-certificate-expiry-daily": {
            "task": "eios.certificates.check_expiry",
            "schedule": 86400,  # every 24 hours
        },
        "refresh-document-sources-twice-daily": {
            "task": "eios.documents.refresh_scheduled",
            "schedule": 43200,  # every 12 hours
        },
    },
)
