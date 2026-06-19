"""Dataset Freshness Service — M34.1.

Tracks the freshness of each external dataset based on expected refresh cadence.

Freshness status:
  FRESH   — refreshed within expected cadence (green)
  STALE   — overdue by up to 2× cadence (amber)
  EXPIRED — more than 2× cadence overdue (red)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Sequence

import structlog

from domain.enums import ExternalSourceName, FreshnessStatus

logger = structlog.get_logger(__name__)

# Expected refresh cadence per source (hours)
_CADENCE_HOURS: dict[str, int] = {
    ExternalSourceName.WORLD_BANK.value: 24 * 30,
    ExternalSourceName.TRANSPARENCY_INTERNATIONAL.value: 24 * 30,
    ExternalSourceName.ILO.value: 24 * 30,
    ExternalSourceName.UNICEF.value: 24 * 30,
    ExternalSourceName.UN_SANCTIONS.value: 24,
    ExternalSourceName.EU_SANCTIONS.value: 24,
    ExternalSourceName.SECTOR_ESG_BENCHMARK.value: 24 * 90,
    ExternalSourceName.SECTOR_RISK_CLASSIFICATION.value: 24 * 90,
    ExternalSourceName.CLIMATE_VULNERABILITY.value: 24 * 90,
    ExternalSourceName.WATER_STRESS.value: 24 * 90,
    ExternalSourceName.BIODIVERSITY_RISK.value: 24 * 90,
}

_DEFAULT_CADENCE_HOURS = 24 * 30


@dataclass
class DatasetFreshness:
    """Freshness assessment for a single external data source."""

    source_name: str
    last_refresh: datetime | None
    expected_cadence_hours: int
    freshness_status: str  # FreshnessStatus value
    hours_since_refresh: float | None
    hours_overdue: float
    next_expected_refresh: datetime | None


def assess_freshness(
    source_name: str,
    last_refresh: datetime | None,
    as_of: datetime | None = None,
) -> DatasetFreshness:
    """Return a FreshnessStatus for a data source.

    Args:
        source_name: ExternalSourceName value.
        last_refresh: When the dataset was last successfully ingested.
        as_of: Reference timestamp (defaults to now).
    """
    now = as_of or datetime.now(UTC)
    cadence_hours = _CADENCE_HOURS.get(source_name, _DEFAULT_CADENCE_HOURS)
    cadence = timedelta(hours=cadence_hours)

    if last_refresh is None:
        return DatasetFreshness(
            source_name=source_name,
            last_refresh=None,
            expected_cadence_hours=cadence_hours,
            freshness_status=FreshnessStatus.EXPIRED.value,
            hours_since_refresh=None,
            hours_overdue=float("inf"),
            next_expected_refresh=None,
        )

    if last_refresh.tzinfo is None:
        last_refresh = last_refresh.replace(tzinfo=UTC)

    elapsed = now - last_refresh
    hours_since = elapsed.total_seconds() / 3600
    next_expected = last_refresh + cadence
    hours_overdue = max(0.0, (now - next_expected).total_seconds() / 3600)

    if elapsed <= cadence:
        status = FreshnessStatus.FRESH
    elif elapsed <= cadence * 2:
        status = FreshnessStatus.STALE
    else:
        status = FreshnessStatus.EXPIRED

    return DatasetFreshness(
        source_name=source_name,
        last_refresh=last_refresh,
        expected_cadence_hours=cadence_hours,
        freshness_status=status.value,
        hours_since_refresh=round(hours_since, 1),
        hours_overdue=round(hours_overdue, 1),
        next_expected_refresh=next_expected,
    )


async def get_freshness_dashboard(session) -> list[DatasetFreshness]:
    """Return freshness status for all known external sources.

    M5: Uses a single GROUP BY query instead of N sequential queries.
    """
    from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel
    from sqlalchemy import select, func

    source_names = [s.value for s in ExternalSourceName]

    stmt = (
        select(
            ExternalDatasetModel.source_name,
            func.max(ExternalDatasetModel.imported_at).label("last_imported"),
        )
        .where(ExternalDatasetModel.dataset_status == "active")
        .group_by(ExternalDatasetModel.source_name)
    )
    rows = (await session.execute(stmt)).all()
    last_refresh_by_source = {r.source_name: r.last_imported for r in rows}

    return [
        assess_freshness(name, last_refresh_by_source.get(name))
        for name in source_names
    ]


def needs_refresh(freshness: DatasetFreshness) -> bool:
    """Return True if a dataset should be refreshed now."""
    return freshness.freshness_status in (
        FreshnessStatus.STALE.value,
        FreshnessStatus.EXPIRED.value,
    )
