"""M34.1 Tests — ExternalIntelligenceScheduler."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.external_intelligence.freshness_service import (
    DatasetFreshness,
    assess_freshness,
)
from domain.enums import FreshnessStatus


def _make_freshness(status: str, source: str = "world_bank") -> DatasetFreshness:
    return DatasetFreshness(
        source_name=source,
        freshness_status=status,
        last_refresh=None,
        expected_cadence_hours=24 * 30,
        hours_since_refresh=None,
        hours_overdue=0.0 if status == "fresh" else 5.0,
        next_expected_refresh=None,
    )


# ── trigger_connector_refresh ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_unknown_connector_raises():
    from application.external_intelligence.scheduler import trigger_connector_refresh

    session = AsyncMock()
    with patch(
        "application.external_intelligence.connectors.ALL_CONNECTORS",
        [],
    ):
        with pytest.raises(ValueError, match="Unknown connector"):
            await trigger_connector_refresh("nonexistent", session)


@pytest.mark.asyncio
async def test_trigger_known_connector_runs():
    from application.external_intelligence.scheduler import trigger_connector_refresh

    mock_connector = MagicMock()
    mock_connector.connector_name = "world_bank"
    mock_run_result = MagicMock()
    mock_run_result.success = True
    mock_run_result.row_count = 100
    mock_connector_instance = MagicMock()
    mock_connector_instance.run = AsyncMock(return_value=mock_run_result)
    mock_connector_instance.connector_name = "world_bank"
    mock_connector.return_value = mock_connector_instance

    session = AsyncMock()

    with patch(
        "application.external_intelligence.connectors.ALL_CONNECTORS",
        [mock_connector],
    ):
        result = await trigger_connector_refresh("world_bank", session)

    assert result.success is True
    assert result.row_count == 100


# ── _get_last_successful_refresh ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_last_refresh_returns_none_when_no_runs():
    from application.external_intelligence.scheduler import _get_last_successful_refresh

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    session.execute.return_value = execute_result

    result = await _get_last_successful_refresh("world_bank", session)
    assert result is None


@pytest.mark.asyncio
async def test_get_last_refresh_returns_completed_at():
    from application.external_intelligence.scheduler import _get_last_successful_refresh

    now = datetime.now(UTC)
    mock_run = MagicMock()
    mock_run.completed_at = now - timedelta(hours=5)

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = mock_run
    session.execute.return_value = execute_result

    result = await _get_last_successful_refresh("world_bank", session)
    assert result is not None


# ── Scheduler cancellation ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scheduler_stops_on_cancel():
    """Scheduler task should propagate CancelledError cleanly."""
    from application.external_intelligence.scheduler import run_intelligence_scheduler

    with (
        patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        patch(
            "application.external_intelligence.scheduler._run_due_connectors",
            new_callable=AsyncMock,
        ),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_intelligence_scheduler()
