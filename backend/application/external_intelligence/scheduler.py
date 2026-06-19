"""External Intelligence Scheduler — M34.1 / M34.2.

Runs as a background asyncio task inside the FastAPI lifespan.

Each connector has a configured refresh cadence (hours). The scheduler
wakes up every CHECK_INTERVAL_SECONDS, queries the last successful run
for each connector, and triggers a refresh if the connector is due.

M34.2 hardening:
  - H4: Uses DB-backed concurrency guard (status='running' lock)
  - H5: trigger_connector_refresh triggers benchmark refresh on success
  - M2: trigger_source persisted to connector_runs
  - M6: Updates scheduler heartbeat on each cycle
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from application.external_intelligence.scheduler_health import (
    record_cycle_completed,
    record_cycle_started,
    record_scheduler_stopped,
)

logger = structlog.get_logger(__name__)

_CHECK_INTERVAL_SECONDS = 3600
_STARTUP_DELAY_SECONDS = 60


async def run_intelligence_scheduler() -> None:
    """Main scheduler loop. Runs forever until cancelled."""
    logger.info("intelligence_scheduler_started")
    await asyncio.sleep(_STARTUP_DELAY_SECONDS)

    while True:
        try:
            record_cycle_started()
            await _run_due_connectors()
            record_cycle_completed()
        except asyncio.CancelledError:
            record_scheduler_stopped()
            logger.info("intelligence_scheduler_cancelled")
            raise
        except Exception as exc:
            logger.error("intelligence_scheduler_error", error=str(exc))

        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)


async def _run_due_connectors() -> None:
    """Check all connectors and run those that are due."""
    from application.external_intelligence.connectors import ALL_CONNECTORS
    from application.external_intelligence.freshness_service import assess_freshness
    from infrastructure.persistence.database import AsyncSessionFactory

    now = datetime.now(UTC)
    due = []

    async with AsyncSessionFactory() as session, session.begin():
        for connector_cls in ALL_CONNECTORS:
            connector = connector_cls()
            last_refresh = await _get_last_successful_refresh(connector.connector_name, session)
            freshness = assess_freshness(connector.connector_name, last_refresh, as_of=now)
            if freshness.hours_overdue > 0 or last_refresh is None:
                due.append(connector)

    if not due:
        logger.debug("intelligence_scheduler_nothing_due")
        return

    logger.info(
        "intelligence_scheduler_running_connectors",
        count=len(due),
        connectors=[c.connector_name for c in due],
    )

    for connector in due:
        try:
            async with AsyncSessionFactory() as session, session.begin():
                result = await connector.run(session, trigger_source="scheduler")
                logger.info(
                    "connector_completed",
                    connector=connector.connector_name,
                    success=result.success,
                    rows=result.row_count,
                    runtime=result.runtime_seconds,
                )
                # H1: only refresh benchmarks when dataset is genuinely valid
                if result.success and result.dataset_id and not result.validation_errors:
                    from application.external_intelligence.benchmark_refresh_service import (
                        refresh_for_dataset,
                    )
                    await refresh_for_dataset(
                        result.dataset_id,
                        connector.connector_name,
                        session,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "connector_scheduler_error",
                connector=connector.connector_name,
                error=str(exc),
            )


async def _get_last_successful_refresh(
    connector_name: str,
    session,
) -> datetime | None:
    """Return the timestamp of the last successful run for a connector."""
    from infrastructure.persistence.models.connector_run import ConnectorRunModel
    from sqlalchemy import select

    stmt = (
        select(ConnectorRunModel)
        .where(
            ConnectorRunModel.connector_name == connector_name,
            ConnectorRunModel.status.in_(["healthy", "degraded"]),
        )
        .order_by(ConnectorRunModel.completed_at.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return row.completed_at if row else None


async def trigger_connector_refresh(
    connector_name: str,
    session,
    trigger_source: str = "manual",
) -> object:
    """Manually trigger a single connector refresh.

    H5: Also triggers benchmark refresh on success (same pipeline as scheduler).
    M2: Passes trigger_source through to connector_runs audit record.
    """
    from application.external_intelligence.connectors import ALL_CONNECTORS

    connector_cls = next(
        (cls for cls in ALL_CONNECTORS if cls.connector_name == connector_name),
        None,
    )
    if connector_cls is None:
        raise ValueError(f"Unknown connector: {connector_name!r}")

    connector = connector_cls()
    result = await connector.run(session, trigger_source=trigger_source)
    logger.info(
        "manual_connector_refresh",
        connector=connector_name,
        success=result.success,
        rows=result.row_count,
        trigger_source=trigger_source,
    )

    # H5: trigger benchmark refresh — same as scheduler
    if result.success and result.dataset_id and not result.validation_errors:
        try:
            from application.external_intelligence.benchmark_refresh_service import (
                refresh_for_dataset,
            )
            await refresh_for_dataset(result.dataset_id, connector_name, session)
        except Exception as exc:
            logger.warning("benchmark_refresh_failed_on_manual_trigger", error=str(exc))

    return result
