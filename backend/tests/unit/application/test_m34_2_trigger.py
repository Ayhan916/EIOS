"""M34.2 Tests — H5 Manual trigger also calls benchmark refresh."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_trigger_calls_benchmark_refresh_on_success():
    """H5: trigger_connector_refresh must call refresh_for_dataset on success."""
    from application.external_intelligence.scheduler import trigger_connector_refresh

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.dataset_id = "ds-001"
    mock_result.validation_errors = []
    mock_result.row_count = 100
    mock_result.runtime_seconds = 5.0
    mock_result.connector_name = "world_bank"

    mock_connector_cls = MagicMock()
    mock_connector_cls.connector_name = "world_bank"
    mock_connector_instance = MagicMock()
    mock_connector_instance.run = AsyncMock(return_value=mock_result)
    mock_connector_instance.connector_name = "world_bank"
    mock_connector_cls.return_value = mock_connector_instance

    session = AsyncMock()

    with (
        patch(
            "application.external_intelligence.connectors.ALL_CONNECTORS",
            [mock_connector_cls],
        ),
        patch(
            "application.external_intelligence.benchmark_refresh_service.refresh_for_dataset",
            new_callable=AsyncMock,
        ) as mock_refresh,
    ):
        result = await trigger_connector_refresh("world_bank", session, trigger_source="manual")

    mock_refresh.assert_called_once_with("ds-001", "world_bank", session)
    assert result.success is True


@pytest.mark.asyncio
async def test_trigger_does_not_call_benchmark_refresh_on_failure():
    """H5: trigger_connector_refresh must NOT call refresh on failure."""
    from application.external_intelligence.scheduler import trigger_connector_refresh

    mock_result = MagicMock()
    mock_result.success = False
    mock_result.dataset_id = None
    mock_result.validation_errors = []
    mock_result.row_count = 0
    mock_result.runtime_seconds = 2.0
    mock_result.connector_name = "world_bank"

    mock_connector_cls = MagicMock()
    mock_connector_cls.connector_name = "world_bank"
    mock_connector_instance = MagicMock()
    mock_connector_instance.run = AsyncMock(return_value=mock_result)
    mock_connector_instance.connector_name = "world_bank"
    mock_connector_cls.return_value = mock_connector_instance

    session = AsyncMock()

    with (
        patch(
            "application.external_intelligence.connectors.ALL_CONNECTORS",
            [mock_connector_cls],
        ),
        patch(
            "application.external_intelligence.benchmark_refresh_service.refresh_for_dataset",
            new_callable=AsyncMock,
        ) as mock_refresh,
    ):
        result = await trigger_connector_refresh("world_bank", session)

    mock_refresh.assert_not_called()
    assert result.success is False


@pytest.mark.asyncio
async def test_trigger_does_not_call_benchmark_refresh_when_quarantined():
    """H5: quarantined datasets (validation_errors non-empty) must not trigger refresh."""
    from application.external_intelligence.scheduler import trigger_connector_refresh

    mock_result = MagicMock()
    mock_result.success = False  # H1: quarantined = success False
    mock_result.dataset_id = "ds-002"
    mock_result.validation_errors = ["Row count below minimum"]
    mock_result.row_count = 1
    mock_result.runtime_seconds = 3.0
    mock_result.connector_name = "world_bank"

    mock_connector_cls = MagicMock()
    mock_connector_cls.connector_name = "world_bank"
    mock_connector_instance = MagicMock()
    mock_connector_instance.run = AsyncMock(return_value=mock_result)
    mock_connector_instance.connector_name = "world_bank"
    mock_connector_cls.return_value = mock_connector_instance

    session = AsyncMock()

    with (
        patch(
            "application.external_intelligence.connectors.ALL_CONNECTORS",
            [mock_connector_cls],
        ),
        patch(
            "application.external_intelligence.benchmark_refresh_service.refresh_for_dataset",
            new_callable=AsyncMock,
        ) as mock_refresh,
    ):
        await trigger_connector_refresh("world_bank", session)

    mock_refresh.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_passes_trigger_source_to_connector_run():
    """M2: trigger_connector_refresh passes trigger_source to connector.run()."""
    from application.external_intelligence.scheduler import trigger_connector_refresh

    mock_result = MagicMock()
    mock_result.success = False
    mock_result.dataset_id = None
    mock_result.validation_errors = []
    mock_result.row_count = 0
    mock_result.runtime_seconds = 1.0
    mock_result.connector_name = "world_bank"

    mock_connector_cls = MagicMock()
    mock_connector_cls.connector_name = "world_bank"
    mock_connector_instance = MagicMock()
    mock_connector_instance.run = AsyncMock(return_value=mock_result)
    mock_connector_instance.connector_name = "world_bank"
    mock_connector_cls.return_value = mock_connector_instance

    session = AsyncMock()

    with patch(
        "application.external_intelligence.connectors.ALL_CONNECTORS",
        [mock_connector_cls],
    ):
        await trigger_connector_refresh("world_bank", session, trigger_source="manual")

    mock_connector_instance.run.assert_called_once_with(
        session, trigger_source="manual"
    )
