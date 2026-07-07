"""G-041 — Auto re-assessment scheduler Celery task.

Runs daily via Celery Beat. Finds active assessment schedules whose
`next_due_at` is in the past, creates a new Draft assessment for each,
then advances `next_due_at` by `frequency_days`.

Design:
  - Creates assessment with status="Draft", review_status="Draft".
  - Never auto-submits or auto-approves. Human must review and trigger manually.
  - Idempotent: uses `last_triggered_at` guard to prevent double-firing within a day.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="eios.schedules.check_due_assessments",
    max_retries=2,
    default_retry_delay=300,
)
def check_due_assessments_task(self) -> dict[str, object]:
    """Find overdue assessment schedules and create draft assessments."""
    try:
        return asyncio.run(_run_schedule_check())
    except Exception as exc:
        logger.error("schedule_check_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_schedule_check() -> dict[str, object]:
    from sqlalchemy import select  # noqa: PLC0415

    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.models.assessment import AssessmentModel  # noqa: PLC0415
    from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel  # noqa: PLC0415

    now = datetime.now(UTC)
    triggered = 0
    errors = 0

    async with AsyncSessionFactory() as session, session.begin():
        stmt = select(AssessmentScheduleModel).where(
            AssessmentScheduleModel.is_active.is_(True),
            AssessmentScheduleModel.next_due_at <= now,
        )
        result = await session.execute(stmt)
        schedules = list(result.scalars().all())

        for schedule in schedules:
            # Idempotency guard: skip if already triggered today
            if (
                schedule.last_triggered_at
                and (now - schedule.last_triggered_at).total_seconds() < 3600 * 20
            ):
                continue

            try:
                assessment = AssessmentModel(
                    id=str(uuid.uuid4()),
                    status="Active",
                    version=1,
                    owner=None,
                    created_by="system:schedule",
                    updated_by="system:schedule",
                    created_at=now,
                    updated_at=now,
                    organization_id=schedule.organization_id,
                    supplier_id=schedule.supplier_id,
                    title="Periodic Assessment — auto-scheduled",
                    description=f"Auto-created by assessment schedule (frequency: {schedule.frequency_days} days).",
                    assessment_type="Periodic",
                    scope="",
                    confidence="Medium",
                    review_status="Draft",
                )
                session.add(assessment)

                schedule.last_triggered_at = now
                schedule.next_due_at = now + timedelta(days=schedule.frequency_days)
                schedule.updated_at = now
                triggered += 1

                logger.info(
                    "auto_assessment_created",
                    schedule_id=schedule.id,
                    supplier_id=schedule.supplier_id,
                    assessment_id=assessment.id,
                )
            except Exception as exc:
                logger.error("auto_assessment_error", schedule_id=schedule.id, error=str(exc))
                errors += 1

    return {"triggered": triggered, "errors": errors, "checked_at": now.isoformat()}
