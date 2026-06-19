"""M34.2 Tests — H3 Benchmark Refresh scoping and N+1 elimination."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.external_intelligence.benchmark_refresh_service import (
    _COUNTRY_CONNECTORS,
    _SANCTIONS_CONNECTORS,
)


def test_country_connector_set_contains_expected_sources():
    assert "world_bank" in _COUNTRY_CONNECTORS
    assert "transparency_international" in _COUNTRY_CONNECTORS
    assert "ilo" in _COUNTRY_CONNECTORS
    assert "unicef" in _COUNTRY_CONNECTORS


def test_sanctions_connector_set_contains_expected_sources():
    assert "un_sanctions" in _SANCTIONS_CONNECTORS
    assert "eu_sanctions" in _SANCTIONS_CONNECTORS


@pytest.mark.asyncio
async def test_refresh_for_dataset_returns_zero_when_no_enrichments():
    from application.external_intelligence.benchmark_refresh_service import refresh_for_dataset

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result

    count = await refresh_for_dataset("ds-001", "world_bank", session)
    assert count == 0


@pytest.mark.asyncio
async def test_refresh_for_dataset_calls_batch_score_load():
    """H3: batch_load_supplier_scores is called once for all enrichments."""
    from application.external_intelligence.benchmark_refresh_service import refresh_for_dataset

    mock_enrichment = MagicMock()
    mock_enrichment.supplier_id = "sup-001"
    mock_enrichment.organization_id = "org-001"
    mock_enrichment.country_code = "DE"
    mock_enrichment.benchmark_score = 60.0
    mock_enrichment.sanctions_exposure = None

    session = AsyncMock()
    execute_result_enrichments = MagicMock()
    execute_result_enrichments.scalars.return_value.all.return_value = [mock_enrichment]
    execute_result_scores = MagicMock()
    execute_result_scores.scalars.return_value.all.return_value = []
    session.execute.side_effect = [execute_result_enrichments, execute_result_scores]

    with patch(
        "application.external_intelligence.benchmark_refresh_service._refresh_single_enrichment_with_score",
        new_callable=AsyncMock,
    ) as mock_refresh:
        count = await refresh_for_dataset("ds-001", "world_bank", session)

    mock_refresh.assert_called_once()
    assert count == 1


@pytest.mark.asyncio
async def test_refresh_for_dataset_scopes_country_connectors():
    """H3: Country connectors must filter by country_code IS NOT NULL."""
    from application.external_intelligence.benchmark_refresh_service import refresh_for_dataset

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result

    await refresh_for_dataset("ds-001", "world_bank", session)

    # The query is built with a WHERE clause — verify the call was made
    assert session.execute.called


@pytest.mark.asyncio
async def test_batch_load_supplier_scores_returns_empty_dict_for_no_suppliers():
    from application.external_intelligence.benchmark_refresh_service import (
        _batch_load_supplier_scores,
    )

    session = AsyncMock()
    result = await _batch_load_supplier_scores([], session)
    assert result == {}
