"""M34 enrichment service tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.enums import SanctionsExposure


def _now():
    return datetime.now(UTC)


def _make_country_profile(
    overall_risk_score=70.0,
    risk_level="high",
    sanctions_status="none",
):
    from domain.external_intelligence import CountryRiskProfile

    return CountryRiskProfile(
        id="cr-001",
        country_code="CN",
        country_name="China",
        dataset_id="ds-001",
        overall_risk_score=overall_risk_score,
        risk_level=risk_level,
        sanctions_status=sanctions_status,
        source_name="world_bank",
        source_version="2025",
        data_date="2025-01-01",
    )


def _make_benchmark():
    from domain.enums import ExternalSourceName
    from domain.external_intelligence import SectorBenchmark

    return SectorBenchmark(
        sector_id="sec-001",
        sector_name="Manufacturing",
        nace_code="C28",
        dataset_id="ds-bench-001",
        average_esg_score=60.0,
        average_risk_score=40.0,
        average_compliance_coverage=70.0,
        average_disclosure_readiness=65.0,
        supplier_count=150,
        p10_esg_score=20.0,
        p25_esg_score=40.0,
        p50_esg_score=60.0,
        p75_esg_score=75.0,
        p90_esg_score=90.0,
        source_name=ExternalSourceName.SECTOR_ESG_BENCHMARK,
        source_version="2025-Q1",
        benchmark_date="2025-03-01",
    )


@pytest.mark.asyncio
@patch("application.external_intelligence.enrichment_service.get_country_risk")
@patch("application.external_intelligence.enrichment_service.get_benchmark_by_nace")
@patch("application.external_intelligence.enrichment_service.list_signals_for_supplier")
async def test_enrich_supplier_returns_enrichment(mock_signals, mock_bench, mock_country):
    mock_country.return_value = _make_country_profile()
    mock_bench.return_value = _make_benchmark()
    mock_signals.return_value = []

    session = AsyncMock()
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=no_existing)
    session.flush = AsyncMock()

    from application.external_intelligence.enrichment_service import enrich_supplier

    enrichment = await enrich_supplier(
        supplier_id="sup-001",
        organization_id="org-001",
        country_code="CN",
        sector_id="sec-001",
        nace_code="C28",
        internal_esg_score=65.0,
        session=session,
    )
    assert enrichment is not None
    assert enrichment.supplier_id == "sup-001"
    assert enrichment.organization_id == "org-001"
    assert 0.0 <= enrichment.combined_risk_score <= 100.0


@pytest.mark.asyncio
@patch("application.external_intelligence.enrichment_service.get_country_risk")
@patch("application.external_intelligence.enrichment_service.get_benchmark_by_nace")
@patch("application.external_intelligence.enrichment_service.list_signals_for_supplier")
async def test_enrich_high_risk_country_raises_combined_risk(
    mock_signals, mock_bench, mock_country
):
    mock_country.return_value = _make_country_profile(
        overall_risk_score=90.0, risk_level="critical"
    )
    mock_bench.return_value = None
    mock_signals.return_value = []

    session = AsyncMock()
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=no_existing)
    session.flush = AsyncMock()

    from application.external_intelligence.enrichment_service import enrich_supplier

    enrichment = await enrich_supplier(
        supplier_id="sup-002",
        organization_id="org-001",
        country_code="XX",
        sector_id="",
        nace_code="",
        internal_esg_score=70.0,
        session=session,
    )
    # Country risk 90 * 0.4 = 36 contribution to external risk
    assert enrichment.country_risk_score == 90.0
    assert enrichment.combined_risk_score > 20.0


@pytest.mark.asyncio
@patch("application.external_intelligence.enrichment_service.get_country_risk")
@patch("application.external_intelligence.enrichment_service.get_benchmark_by_nace")
@patch("application.external_intelligence.enrichment_service.list_signals_for_supplier")
async def test_enrich_signals_increase_risk(mock_signals, mock_bench, mock_country):
    """5 active signals should add penalty to combined risk."""
    from domain.enums import ExternalSourceName, RiskSignalType, SignalSeverity
    from domain.external_intelligence import ExternalRiskSignal

    mock_country.return_value = _make_country_profile(
        overall_risk_score=30.0, risk_level="moderate"
    )
    mock_bench.return_value = _make_benchmark()
    # 5 signals → 5 * 5 = 25 penalty
    mock_signals.return_value = [
        ExternalRiskSignal(
            signal_type=RiskSignalType.SANCTIONS,
            severity=SignalSeverity.HIGH,
            description="Test",
            source_name=ExternalSourceName.OFAC,
            source_version="2025",
            observed_at=_now(),
            supplier_id="sup-001",
            organization_id="org-001",
        )
        for _ in range(5)
    ]

    session = AsyncMock()
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=no_existing)
    session.flush = AsyncMock()

    from application.external_intelligence.enrichment_service import enrich_supplier

    enrichment_with_signals = await enrich_supplier(
        supplier_id="sup-001",
        organization_id="org-001",
        country_code="DE",
        sector_id="sec-001",
        nace_code="C28",
        internal_esg_score=65.0,
        session=session,
    )
    assert enrichment_with_signals.active_signal_count == 5
    assert enrichment_with_signals.combined_risk_score > 0


@pytest.mark.asyncio
@patch("application.external_intelligence.enrichment_service.get_country_risk")
@patch("application.external_intelligence.enrichment_service.get_benchmark_by_nace")
@patch("application.external_intelligence.enrichment_service.list_signals_for_supplier")
async def test_enrich_upserts_existing_record(mock_signals, mock_bench, mock_country):
    """Re-running enrichment on existing record updates in-place."""

    mock_country.return_value = _make_country_profile()
    mock_bench.return_value = _make_benchmark()
    mock_signals.return_value = []

    existing_model = MagicMock()
    existing_model.id = "enr-001"

    session = AsyncMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = existing_model
    session.execute = AsyncMock(return_value=found)
    session.flush = AsyncMock()

    from application.external_intelligence.enrichment_service import enrich_supplier

    await enrich_supplier(
        supplier_id="sup-001",
        organization_id="org-001",
        country_code="CN",
        sector_id="sec-001",
        nace_code="C28",
        internal_esg_score=65.0,
        session=session,
    )
    # Should add existing_model (the updated one), not a new one
    session.add.assert_called_with(existing_model)


@pytest.mark.asyncio
@patch("application.external_intelligence.enrichment_service.get_country_risk")
@patch("application.external_intelligence.enrichment_service.get_benchmark_by_nace")
@patch("application.external_intelligence.enrichment_service.list_signals_for_supplier")
async def test_enrich_sanctions_status_confirmed(mock_signals, mock_bench, mock_country):
    mock_country.return_value = _make_country_profile(sanctions_status="comprehensive")
    mock_bench.return_value = None
    mock_signals.return_value = []

    session = AsyncMock()
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=no_existing)
    session.flush = AsyncMock()

    from application.external_intelligence.enrichment_service import enrich_supplier

    enrichment = await enrich_supplier(
        supplier_id="sup-001",
        organization_id="org-001",
        country_code="RU",
        sector_id="",
        nace_code="",
        internal_esg_score=50.0,
        session=session,
    )
    assert enrichment.sanctions_exposure == SanctionsExposure.CONFIRMED
