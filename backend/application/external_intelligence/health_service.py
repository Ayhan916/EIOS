"""Connector Health Service — M34.1.

Tracks connector run history to compute health status.

Health statuses:
  HEALTHY  — last N runs all successful
  DEGRADED — last run succeeded but some recent failures
  FAILED   — last run failed
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Sequence

import structlog

from domain.enums import ConnectorStatus

logger = structlog.get_logger(__name__)

_HEALTH_WINDOW = 5  # look at last N runs to determine health


@dataclass
class ConnectorHealth:
    """Health summary for a single connector."""

    connector_name: str
    status: str  # ConnectorStatus value
    last_success: datetime | None
    last_failure: datetime | None
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_runtime_seconds: float
    consecutive_failures: int


async def get_connector_health(
    connector_name: str,
    session,
) -> ConnectorHealth:
    """Compute health status from the connector_runs table."""
    from infrastructure.persistence.models.connector_run import ConnectorRunModel
    from sqlalchemy import select, func

    stmt = (
        select(ConnectorRunModel)
        .where(ConnectorRunModel.connector_name == connector_name)
        .order_by(ConnectorRunModel.started_at.desc())
        .limit(100)
    )
    rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        # LOW: never-run connectors should report UNKNOWN, not HEALTHY
        return ConnectorHealth(
            connector_name=connector_name,
            status="unknown",
            last_success=None,
            last_failure=None,
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            avg_runtime_seconds=0.0,
            consecutive_failures=0,
        )

    total = len(rows)
    successful = [r for r in rows if r.status == ConnectorStatus.HEALTHY.value or r.status == "degraded"]
    failed = [r for r in rows if r.status == ConnectorStatus.FAILED.value]

    last_success = next(
        (r.completed_at for r in rows if r.status in (ConnectorStatus.HEALTHY.value, "degraded")),
        None,
    )
    last_failure = next(
        (r.completed_at for r in rows if r.status == ConnectorStatus.FAILED.value),
        None,
    )

    runtimes = [r.runtime_seconds for r in rows if r.runtime_seconds is not None]
    avg_runtime = round(sum(runtimes) / len(runtimes), 2) if runtimes else 0.0

    # Consecutive failures from most recent
    consecutive_failures = 0
    for r in rows:
        if r.status == ConnectorStatus.FAILED.value:
            consecutive_failures += 1
        else:
            break

    # Classify health
    recent = rows[:_HEALTH_WINDOW]
    recent_failures = sum(1 for r in recent if r.status == ConnectorStatus.FAILED.value)
    if recent_failures == 0:
        status = ConnectorStatus.HEALTHY
    elif recent_failures < _HEALTH_WINDOW:
        status = ConnectorStatus.DEGRADED
    else:
        status = ConnectorStatus.FAILED

    return ConnectorHealth(
        connector_name=connector_name,
        status=status.value,
        last_success=last_success,
        last_failure=last_failure,
        total_runs=total,
        successful_runs=len(successful),
        failed_runs=len(failed),
        avg_runtime_seconds=avg_runtime,
        consecutive_failures=consecutive_failures,
    )


async def get_all_connector_health(
    session,
    connector_names: list[str] | None = None,
) -> list[ConnectorHealth]:
    """Return health for all connectors (or a subset).

    M5: Loads all connector runs in a single query, then aggregates in Python.
    """
    if connector_names is None:
        from application.external_intelligence.connectors import ALL_CONNECTORS
        connector_names = [cls.connector_name for cls in ALL_CONNECTORS]

    if not connector_names:
        return []

    from infrastructure.persistence.models.connector_run import ConnectorRunModel
    from sqlalchemy import select

    stmt = (
        select(ConnectorRunModel)
        .where(ConnectorRunModel.connector_name.in_(connector_names))
        .order_by(ConnectorRunModel.started_at.desc())
    )
    all_rows = (await session.execute(stmt)).scalars().all()

    rows_by_connector: dict[str, list] = {name: [] for name in connector_names}
    for row in all_rows:
        if row.connector_name in rows_by_connector:
            rows_by_connector[row.connector_name].append(row)

    return [_compute_health(name, rows_by_connector[name]) for name in connector_names]


def _compute_health(connector_name: str, rows: list) -> ConnectorHealth:
    """Compute ConnectorHealth from pre-loaded rows (pure, no DB access)."""
    if not rows:
        return ConnectorHealth(
            connector_name=connector_name,
            status="unknown",
            last_success=None,
            last_failure=None,
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            avg_runtime_seconds=0.0,
            consecutive_failures=0,
        )

    total = len(rows)
    successful = [r for r in rows if r.status in (ConnectorStatus.HEALTHY.value, "degraded")]
    failed = [r for r in rows if r.status == ConnectorStatus.FAILED.value]

    last_success = next(
        (r.completed_at for r in rows if r.status in (ConnectorStatus.HEALTHY.value, "degraded")),
        None,
    )
    last_failure = next(
        (r.completed_at for r in rows if r.status == ConnectorStatus.FAILED.value),
        None,
    )

    runtimes = [r.runtime_seconds for r in rows if r.runtime_seconds is not None]
    avg_runtime = round(sum(runtimes) / len(runtimes), 2) if runtimes else 0.0

    consecutive_failures = 0
    for r in rows:
        if r.status == ConnectorStatus.FAILED.value:
            consecutive_failures += 1
        else:
            break

    recent = rows[:_HEALTH_WINDOW]
    recent_failures = sum(1 for r in recent if r.status == ConnectorStatus.FAILED.value)
    if recent_failures == 0:
        status = ConnectorStatus.HEALTHY
    elif recent_failures < _HEALTH_WINDOW:
        status = ConnectorStatus.DEGRADED
    else:
        status = ConnectorStatus.FAILED

    return ConnectorHealth(
        connector_name=connector_name,
        status=status.value,
        last_success=last_success,
        last_failure=last_failure,
        total_runs=total,
        successful_runs=len(successful),
        failed_runs=len(failed),
        avg_runtime_seconds=avg_runtime,
        consecutive_failures=consecutive_failures,
    )


def classify_overall_health(healths: Sequence[ConnectorHealth]) -> str:
    """Compute a single platform-level health signal from individual statuses."""
    if not healths:
        return ConnectorStatus.HEALTHY.value
    statuses = {h.status for h in healths}
    if ConnectorStatus.FAILED.value in statuses:
        return ConnectorStatus.FAILED.value
    if ConnectorStatus.DEGRADED.value in statuses:
        return ConnectorStatus.DEGRADED.value
    return ConnectorStatus.HEALTHY.value
