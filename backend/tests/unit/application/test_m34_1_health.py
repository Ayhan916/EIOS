"""M34.1 Tests — ConnectorHealthService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.external_intelligence.health_service import (
    ConnectorHealth,
    classify_overall_health,
    get_connector_health,
)
from domain.enums import ConnectorStatus


def _make_run(status: str, started_offset_hours: int = 0):
    now = datetime.now(UTC)
    run = MagicMock()
    run.connector_name = "test"
    run.status = status
    run.started_at = now - timedelta(hours=started_offset_hours)
    run.completed_at = now - timedelta(hours=started_offset_hours - 1)
    run.runtime_seconds = 30.0
    return run


def _make_session(runs: list) -> AsyncMock:
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = runs
    session.execute.return_value = execute_result
    return session


# ── No runs ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_runs_returns_unknown():
    # LOW M34.2: never-run connectors report 'unknown', not 'healthy'
    session = _make_session([])
    health = await get_connector_health("world_bank", session)
    assert health.status == "unknown"
    assert health.total_runs == 0
    assert health.consecutive_failures == 0


# ── All successful runs ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_successful_is_healthy():
    runs = [_make_run("healthy") for _ in range(5)]
    session = _make_session(runs)
    health = await get_connector_health("world_bank", session)
    assert health.status == ConnectorStatus.HEALTHY.value
    assert health.consecutive_failures == 0


# ── Mixed runs (some failures) ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_one_recent_failure_is_degraded():
    runs = [_make_run("failed")] + [_make_run("healthy") for _ in range(4)]
    session = _make_session(runs)
    health = await get_connector_health("world_bank", session)
    assert health.status == ConnectorStatus.DEGRADED.value
    assert health.consecutive_failures == 1


# ── All failures → FAILED ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_failures_is_failed():
    runs = [_make_run("failed") for _ in range(5)]
    session = _make_session(runs)
    health = await get_connector_health("world_bank", session)
    assert health.status == ConnectorStatus.FAILED.value
    assert health.consecutive_failures == 5


# ── last_success / last_failure timestamps ───────────────────────────────────


@pytest.mark.asyncio
async def test_last_success_and_failure_timestamps():
    runs = [_make_run("failed", 0), _make_run("healthy", 1)]
    session = _make_session(runs)
    health = await get_connector_health("world_bank", session)
    assert health.last_failure is not None
    assert health.last_success is not None


# ── avg_runtime_seconds ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_avg_runtime_computed():
    runs = [_make_run("healthy") for _ in range(3)]
    for run in runs:
        run.runtime_seconds = 30.0
    session = _make_session(runs)
    health = await get_connector_health("world_bank", session)
    assert health.avg_runtime_seconds == 30.0


# ── classify_overall_health ──────────────────────────────────────────────────


def _health(status: str) -> ConnectorHealth:
    return ConnectorHealth(
        connector_name="x",
        status=status,
        last_success=None,
        last_failure=None,
        total_runs=0,
        successful_runs=0,
        failed_runs=0,
        avg_runtime_seconds=0.0,
        consecutive_failures=0,
    )


def test_classify_all_healthy():
    result = classify_overall_health([_health("healthy"), _health("healthy")])
    assert result == ConnectorStatus.HEALTHY.value


def test_classify_one_degraded():
    result = classify_overall_health([_health("healthy"), _health("degraded")])
    assert result == ConnectorStatus.DEGRADED.value


def test_classify_one_failed():
    result = classify_overall_health([_health("healthy"), _health("failed")])
    assert result == ConnectorStatus.FAILED.value


def test_classify_empty_is_healthy():
    result = classify_overall_health([])
    assert result == ConnectorStatus.HEALTHY.value
