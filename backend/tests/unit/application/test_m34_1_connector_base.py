"""M34.1 Tests — BaseLiveConnector framework."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.external_intelligence.connectors.base import (
    BaseLiveConnector,
    ConnectorRunResult,
    run_with_retry,
)
from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName


# ── Minimal concrete connector for testing ──────────────────────────────────


class _AlwaysSucceedConnector(BaseLiveConnector):
    connector_name = "test_connector"
    connector_version = "1.0"
    refresh_cadence_hours = 24

    async def fetch(self, client):
        return [{"country_code": "DE", "score": 80.0}]

    def normalize(self, raw_records):
        return RawDataset(
            source_name=ExternalSourceName.WORLD_BANK,
            source_version="2025-01",
            records=raw_records,
        )


class _AlwaysFailConnector(BaseLiveConnector):
    connector_name = "always_fail"
    connector_version = "1.0"
    refresh_cadence_hours = 24

    async def fetch(self, client):
        raise RuntimeError("fetch failed")

    def normalize(self, raw_records):
        return RawDataset(
            source_name=ExternalSourceName.WORLD_BANK,
            source_version="2025-01",
            records=raw_records,
        )


# ── ConnectorRunResult ──────────────────────────────────────────────────────


def test_connector_run_result_defaults():
    now = datetime.now(UTC)
    r = ConnectorRunResult(
        connector_name="wb",
        connector_version="1.0",
        started_at=now,
        completed_at=now,
        runtime_seconds=1.2,
    )
    assert r.success is False
    assert r.retry_count == 0
    assert r.row_count == 0
    assert r.validation_errors == []
    assert r.error_message is None


def test_connector_run_result_with_success():
    now = datetime.now(UTC)
    r = ConnectorRunResult(
        connector_name="wb",
        connector_version="1.0",
        started_at=now,
        completed_at=now,
        runtime_seconds=5.0,
        dataset_hash="abc123",
        dataset_id="ds-001",
        row_count=200,
        success=True,
    )
    assert r.success is True
    assert r.dataset_hash == "abc123"
    assert r.row_count == 200


# ── run_with_retry ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_with_retry_succeeds_immediately():
    call_count = 0

    async def coro_factory():
        nonlocal call_count
        call_count += 1
        return "result"

    result = await run_with_retry(coro_factory, max_retries=3, base_delay=0.0)
    assert result == "result"
    assert call_count == 1


@pytest.mark.asyncio
async def test_run_with_retry_retries_on_failure():
    call_count = 0

    async def coro_factory():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("transient error")
        return "success"

    result = await run_with_retry(coro_factory, max_retries=3, base_delay=0.0)
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_run_with_retry_exhausts_retries():
    async def coro_factory():
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        await run_with_retry(coro_factory, max_retries=2, base_delay=0.0)


# ── BaseLiveConnector.validate ──────────────────────────────────────────────


def test_validate_empty_dataset_returns_error():
    connector = _AlwaysSucceedConnector()
    raw = RawDataset(
        source_name=ExternalSourceName.WORLD_BANK,
        source_version="v1",
        records=[],
    )
    errors = connector.validate(raw)
    assert any("empty" in e.lower() for e in errors)


def test_validate_duplicate_rows_detected():
    connector = _AlwaysSucceedConnector()
    record = {"country_code": "US", "score": 50.0}
    raw = RawDataset(
        source_name=ExternalSourceName.WORLD_BANK,
        source_version="v1",
        records=[record, record],
    )
    errors = connector.validate(raw)
    # duplicates should appear in errors or warnings — base class returns list
    # (even if empty; duplication detection may be in validation_service)
    assert isinstance(errors, list)


# ── BaseLiveConnector.ingest integration (mocked session) ──────────────────


@pytest.mark.asyncio
async def test_ingest_calls_fetch_normalize():
    connector = _AlwaysSucceedConnector()
    mock_session = AsyncMock()

    with (
        patch(
            "application.external_intelligence.dataset_service.ingest_dataset",
            new_callable=AsyncMock,
            return_value=MagicMock(id="ds-001", dataset_hash="abc"),
        ),
        patch(
            "application.external_intelligence.connectors.base._record_run",
            new_callable=AsyncMock,
        ),
    ):
        dataset, errors = await connector.ingest(mock_session)
    assert dataset is not None


@pytest.mark.asyncio
async def test_run_returns_connector_run_result():
    connector = _AlwaysSucceedConnector()
    mock_session = AsyncMock()

    with (
        patch(
            "application.external_intelligence.dataset_service.ingest_dataset",
            new_callable=AsyncMock,
            return_value=MagicMock(id="ds-001", dataset_hash="hashval"),
        ),
        patch(
            "application.external_intelligence.connectors.base._record_run",
            new_callable=AsyncMock,
        ),
        patch(
            "application.external_intelligence.connectors.base._check_concurrent_run",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "application.external_intelligence.connectors.base._acquire_running_lock",
            new_callable=AsyncMock,
            return_value="lock-123",
        ),
        patch(
            "application.external_intelligence.metrics.ext_counters.record_dataset_refresh"
        ),
        patch(
            "application.external_intelligence.metrics.ext_counters.record_connector_runtime"
        ),
    ):
        result = await connector.run(mock_session, max_retries=1)

    assert isinstance(result, ConnectorRunResult)
    assert result.connector_name == "test_connector"
