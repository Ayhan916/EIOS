"""Document Intelligence Pipeline — Celery task.

Runs every 12 hours via Celery Beat. Iterates all active document sources
across all organizations and triggers ingestion based on each source's
configured schedule (daily / weekly / monthly / manual).

Design:
  - manual sources are always skipped.
  - schedule-based cooldown prevents re-fetching before the interval elapses.
  - Each source runs in its own DB session so one failure does not block others.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)

SCHEDULE_INTERVALS: dict[str, timedelta] = {
    "daily": timedelta(hours=23),
    "weekly": timedelta(days=6),
    "monthly": timedelta(days=29),
}


@celery_app.task(
    bind=True,
    name="eios.documents.refresh_scheduled",
    max_retries=2,
    default_retry_delay=600,
)
def refresh_scheduled_documents_task(self) -> dict[str, object]:
    """Refresh all due document sources based on their schedule."""
    try:
        return asyncio.run(_run_refresh())
    except Exception as exc:
        logger.error("document_refresh_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_refresh() -> dict[str, object]:
    from sqlalchemy import select  # noqa: PLC0415

    from application.rag.document_ingestion import ingest_source  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.models.document_pipeline import (  # noqa: PLC0415
        DocumentSourceModel,
    )

    now = datetime.now(UTC)
    ingested = 0
    skipped = 0
    errors = 0

    # Load all active sources in a read-only pass
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(DocumentSourceModel).where(DocumentSourceModel.is_active.is_(True))
        )
        sources = list(result.scalars().all())
        # Detach from session so we can open per-source sessions below
        source_snapshots = [
            {
                "id": s.id,
                "schedule": s.schedule,
                "last_fetched_at": s.last_fetched_at,
            }
            for s in sources
        ]

    for snap in source_snapshots:
        if snap["schedule"] == "manual":
            skipped += 1
            continue

        interval = SCHEDULE_INTERVALS.get(snap["schedule"])
        if interval and snap["last_fetched_at"]:
            elapsed = now - snap["last_fetched_at"].replace(tzinfo=UTC) if snap["last_fetched_at"].tzinfo is None else now - snap["last_fetched_at"]
            if elapsed < interval:
                skipped += 1
                logger.debug(
                    "document_source_skipped_cooldown",
                    source_id=snap["id"],
                    elapsed_h=round(elapsed.total_seconds() / 3600, 1),
                )
                continue

        try:
            async with AsyncSessionFactory() as session, session.begin():
                fresh = (
                    await session.execute(
                        select(DocumentSourceModel).where(
                            DocumentSourceModel.id == snap["id"]
                        )
                    )
                ).scalar_one()
                stats = await ingest_source(fresh, session)
                ingested += 1
                logger.info(
                    "document_source_ingested",
                    source_id=snap["id"],
                    stats=stats,
                )
        except Exception as exc:
            logger.error(
                "document_source_ingest_error",
                source_id=snap["id"],
                error=str(exc),
            )
            errors += 1

    return {
        "ingested": ingested,
        "skipped": skipped,
        "errors": errors,
        "run_at": now.isoformat(),
    }
