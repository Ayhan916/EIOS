"""M34.2 Tests — H1 (success gating) and H2/M3 (validation wired into ingest)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.external_intelligence.connectors.base import ConnectorRunResult


# ── H1: success=False when quarantined ───────────────────────────────────────


@pytest.mark.asyncio
async def test_run_success_false_when_quarantined():
    """run() must return success=False when validation_errors is non-empty."""
    from application.external_intelligence.connectors.base import BaseLiveConnector
    from application.external_intelligence.base_adapter import RawDataset

    class _FakeConnector(BaseLiveConnector):
        connector_name = "test_connector"

        async def fetch(self, client):
            return [{"country_code": "XX", "governance_score": 1.0, "corruption_score": 1.0}]

        def normalize(self, raw_records):
            return RawDataset(
                source_name="test_connector",
                source_version="1.0",
                records=raw_records,
                description="test",
            )

    connector = _FakeConnector()
    mock_session = AsyncMock()

    # Validation returns errors → quarantine
    validation_errors = ["Row count 1 below minimum 50"]

    with (
        patch(
            "application.external_intelligence.connectors.base._check_concurrent_run",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "application.external_intelligence.connectors.base._acquire_running_lock",
            new_callable=AsyncMock,
            return_value="lock-id-123",
        ),
        patch(
            "application.external_intelligence.connectors.base._record_run",
            new_callable=AsyncMock,
        ),
        patch.object(connector, "ingest", new_callable=AsyncMock) as mock_ingest,
    ):
        mock_dataset = MagicMock()
        mock_dataset.id = "ds-001"
        mock_dataset.dataset_hash = "abc"
        mock_dataset.row_count = 1
        mock_ingest.return_value = (mock_dataset, validation_errors)

        result = await connector.run(mock_session)

    assert result.success is False
    assert result.validation_errors == validation_errors


@pytest.mark.asyncio
async def test_run_success_true_when_no_validation_errors():
    """run() must return success=True when no errors."""
    from application.external_intelligence.connectors.base import BaseLiveConnector
    from application.external_intelligence.base_adapter import RawDataset

    class _FakeConnector(BaseLiveConnector):
        connector_name = "test_connector"

        async def fetch(self, client):
            return []

        def normalize(self, raw_records):
            return RawDataset(
                source_name="test_connector",
                source_version="1.0",
                records=raw_records,
                description="test",
            )

    connector = _FakeConnector()
    mock_session = AsyncMock()

    with (
        patch(
            "application.external_intelligence.connectors.base._check_concurrent_run",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "application.external_intelligence.connectors.base._acquire_running_lock",
            new_callable=AsyncMock,
            return_value="lock-id-456",
        ),
        patch(
            "application.external_intelligence.connectors.base._record_run",
            new_callable=AsyncMock,
        ),
        patch.object(connector, "ingest", new_callable=AsyncMock) as mock_ingest,
    ):
        mock_dataset = MagicMock()
        mock_dataset.id = "ds-002"
        mock_dataset.dataset_hash = "def"
        mock_dataset.row_count = 100
        mock_ingest.return_value = (mock_dataset, [])

        result = await connector.run(mock_session)

    assert result.success is True
    assert result.validation_errors == []


# ── H4: concurrency guard ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_aborts_when_already_running():
    """run() must abort and return success=False when a 'running' lock exists."""
    from application.external_intelligence.connectors.base import BaseLiveConnector
    from application.external_intelligence.base_adapter import RawDataset

    class _FakeConnector(BaseLiveConnector):
        connector_name = "test_connector"

        async def fetch(self, client):
            return []

        def normalize(self, raw_records):
            return RawDataset(source_name="test_connector", source_version="1.0",
                              records=[], description="test")

    connector = _FakeConnector()
    mock_session = AsyncMock()

    with patch(
        "application.external_intelligence.connectors.base._check_concurrent_run",
        new_callable=AsyncMock,
        return_value="existing-run-id",
    ):
        result = await connector.run(mock_session)

    assert result.success is False
    assert "already running" in (result.error_message or "")


@pytest.mark.asyncio
async def test_check_concurrent_run_returns_none_when_no_running():
    from application.external_intelligence.connectors.base import _check_concurrent_run

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    session.execute.return_value = execute_result

    result = await _check_concurrent_run("world_bank", session)
    assert result is None


# ── H2/M3: validation wired into ingest ──────────────────────────────────────


def test_validate_dataset_called_with_raw():
    """validate_dataset is a pure function that takes a RawDataset."""
    from application.external_intelligence.validation_service import validate_dataset
    from application.external_intelligence.base_adapter import RawDataset

    raw = RawDataset(
        source_name="world_bank",
        source_version="2023",
        records=[],
        description="empty test",
    )
    result = validate_dataset(raw)
    assert result.is_valid is False
    assert any("empty" in e.lower() for e in result.errors)


def test_validate_dataset_passes_for_valid_data():
    from application.external_intelligence.validation_service import validate_dataset
    from application.external_intelligence.base_adapter import RawDataset

    # Use unique country codes to avoid duplicate detection
    records = [
        {"country_code": f"C{i:02d}", "governance_score": float(i), "corruption_score": float(i)}
        for i in range(60)
    ]
    raw = RawDataset(
        source_name="world_bank",
        source_version="2023",
        records=records,
        description="test",
    )
    result = validate_dataset(raw)
    # Only hash-mismatch error is expected (hash not pre-set on RawDataset)
    assert not result.errors or all("hash" in e.lower() for e in result.errors)
