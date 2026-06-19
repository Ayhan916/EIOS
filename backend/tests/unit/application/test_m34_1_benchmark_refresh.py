"""M34.1 Tests — BenchmarkRefreshService.

Updated for M34.2 H3: refresh_for_dataset now takes connector_name as 2nd arg
and calls _refresh_single_enrichment_with_score (batch-loaded scores).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.external_intelligence.benchmark_refresh_service import (
    refresh_for_dataset,
)


def _make_enrichment_row(supplier_id: str = "sup-001", org_id: str = "org-001"):
    row = MagicMock()
    row.supplier_id = supplier_id
    row.organization_id = org_id
    row.country_code = "DE"
    row.benchmark_score = 50.0
    row.sanctions_exposure = None
    return row


def _make_session_with_enrichments(enrichment_rows: list):
    """Session that returns enrichment rows on first execute and no scores on second."""
    session = AsyncMock()
    enrichment_result = MagicMock()
    enrichment_result.scalars.return_value.all.return_value = enrichment_rows
    score_result = MagicMock()
    score_result.scalars.return_value.all.return_value = []  # no scores → use fallback
    session.execute.side_effect = [enrichment_result, score_result]
    return session


# ── No enrichments ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_zero_enrichments():
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result

    count = await refresh_for_dataset("ds-001", "world_bank", session)
    assert count == 0


# ── Single enrichment refresh ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_single_enrichment():
    row = _make_enrichment_row()
    session = _make_session_with_enrichments([row])

    with patch(
        "application.external_intelligence.benchmark_refresh_service._refresh_single_enrichment_with_score",
        new_callable=AsyncMock,
    ) as mock_refresh:
        count = await refresh_for_dataset("ds-001", "world_bank", session)

    assert count == 1
    mock_refresh.assert_awaited_once()


# ── Multiple enrichments ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_multiple_enrichments():
    rows = [_make_enrichment_row(f"sup-{i:03d}") for i in range(5)]
    session = _make_session_with_enrichments(rows)

    with patch(
        "application.external_intelligence.benchmark_refresh_service._refresh_single_enrichment_with_score",
        new_callable=AsyncMock,
    ):
        count = await refresh_for_dataset("ds-001", "world_bank", session)

    assert count == 5


# ── Failure in single enrichment doesn't abort the rest ───────────────────────


@pytest.mark.asyncio
async def test_single_enrichment_failure_continues():
    rows = [_make_enrichment_row(f"sup-{i}") for i in range(3)]
    session = _make_session_with_enrichments(rows)

    call_count = 0

    async def sometimes_fail(enrichment_row, dataset_id, internal_esg_score, session):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("transient failure")

    with patch(
        "application.external_intelligence.benchmark_refresh_service._refresh_single_enrichment_with_score",
        side_effect=sometimes_fail,
    ):
        count = await refresh_for_dataset("ds-001", "world_bank", session)

    # 2 out of 3 succeeded
    assert count == 2


# ── ext_counters.record_benchmark_refresh called ─────────────────────────────


@pytest.mark.asyncio
async def test_benchmark_refresh_counter_incremented():
    rows = [_make_enrichment_row()]
    session = _make_session_with_enrichments(rows)

    with (
        patch(
            "application.external_intelligence.benchmark_refresh_service._refresh_single_enrichment_with_score",
            new_callable=AsyncMock,
        ),
        patch(
            "application.external_intelligence.benchmark_refresh_service.ext_counters.record_benchmark_refresh"
        ) as mock_counter,
    ):
        await refresh_for_dataset("ds-001", "world_bank", session)

    mock_counter.assert_called_once()
