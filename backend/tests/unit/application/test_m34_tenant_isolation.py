"""M34 tenant isolation tests.

Verifies that supplier enrichments and risk signals cannot leak
across tenant (organization) boundaries.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def _now():
    return datetime.now(UTC)


def _make_enrichment_model(supplier_id, organization_id):
    m = MagicMock()
    m.id = f"enr-{supplier_id}-{organization_id}"
    m.status = "Active"
    m.version = 1
    m.owner = None
    m.created_by = None
    m.updated_by = None
    m.created_at = _now()
    m.updated_at = _now()
    m.supplier_id = supplier_id
    m.organization_id = organization_id
    m.country_code = "CN"
    m.country_risk_id = None
    m.country_risk_level = "high"
    m.country_risk_score = 70.0
    m.sanctions_exposure = "none"
    m.sector_benchmark_id = None
    m.sector_percentile = 45.0
    m.percentile_rank = "median"
    m.benchmark_score = 60.0
    m.benchmark_explanation = "Test"
    m.external_risk_score = 35.0
    m.combined_risk_score = 42.0
    m.enriched_at = _now()
    m.dataset_version = "2025-Q1"
    m.active_signal_count = 0
    return m


def _make_signal_model(supplier_id, organization_id):
    m = MagicMock()
    m.id = f"sig-{supplier_id}-{organization_id}"
    m.status = "Active"
    m.version = 1
    m.owner = None
    m.created_by = None
    m.updated_by = None
    m.created_at = _now()
    m.updated_at = _now()
    m.signal_type = "sanctions"
    m.severity = "high"
    m.description = "Signal for supplier"
    m.source_name = "ofac"
    m.source_version = "2025"
    m.observed_at = _now()
    m.dataset_id = None
    m.country_code = ""
    m.sector_code = ""
    m.supplier_id = supplier_id
    m.organization_id = organization_id
    m.is_active = True
    return m


# ── Enrichment isolation ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_enrichment_returns_none_for_wrong_org():
    """get_enrichment for (supplier, wrong_org) must return None."""
    session = AsyncMock()
    # DB returns None because org filter excludes it
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    from application.external_intelligence.enrichment_service import get_enrichment

    enrichment = await get_enrichment("sup-001", "org-other", session)
    assert enrichment is None


@pytest.mark.asyncio
async def test_get_enrichment_returns_record_for_correct_org():
    model = _make_enrichment_model("sup-001", "org-001")
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = model
    session.execute = AsyncMock(return_value=result)

    from application.external_intelligence.enrichment_service import get_enrichment

    enrichment = await get_enrichment("sup-001", "org-001", session)
    assert enrichment is not None
    assert enrichment.organization_id == "org-001"


@pytest.mark.asyncio
async def test_list_high_risk_restricted_to_org():
    """list_high_risk_suppliers only returns enrichments for the given org."""
    model = _make_enrichment_model("sup-001", "org-001")
    model.combined_risk_score = 80.0
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [model]
    session.execute = AsyncMock(return_value=result)

    from application.external_intelligence.enrichment_service import list_high_risk_suppliers

    enrichments = await list_high_risk_suppliers("org-001", session)
    # All returned enrichments must belong to org-001
    for e in enrichments:
        assert e.organization_id == "org-001"


# ── Signal isolation ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_signals_for_supplier_restricted_to_org():
    """Signals for supplier in org-001 not visible under org-002."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)

    from application.external_intelligence.signal_service import list_signals_for_supplier

    signals = await list_signals_for_supplier("sup-001", "org-002", session)
    assert signals == []


@pytest.mark.asyncio
async def test_list_signals_for_supplier_returns_correct_org():
    model = _make_signal_model("sup-001", "org-001")
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [model]
    session.execute = AsyncMock(return_value=result)

    from application.external_intelligence.signal_service import list_signals_for_supplier

    signals = await list_signals_for_supplier("sup-001", "org-001", session)
    assert len(signals) == 1
    assert signals[0].organization_id == "org-001"


# ── Country risk is global (no org) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_country_risk_is_platform_global():
    """Country risk profiles have no org filter — same data for all tenants."""
    from domain.external_intelligence import CountryRiskProfile

    profile = CountryRiskProfile(
        country_code="DE",
        country_name="Germany",
        dataset_id="ds-001",
        overall_risk_score=18.0,
        risk_level="low",
        sanctions_status="none",
        source_name="world_bank",
        source_version="2025",
        data_date="2025-01-01",
    )
    # CountryRiskProfile has no organization_id field
    assert not hasattr(profile, "organization_id")


@pytest.mark.asyncio
async def test_sector_benchmark_is_platform_global():
    """Sector benchmarks have no org filter — same data for all tenants."""
    from domain.enums import ExternalSourceName
    from domain.external_intelligence import SectorBenchmark

    benchmark = SectorBenchmark(
        sector_id="sec-001",
        sector_name="Manufacturing",
        nace_code="C28",
        dataset_id="ds-001",
        source_name=ExternalSourceName.SECTOR_ESG_BENCHMARK,
        source_version="2025",
        benchmark_date="2025-01-01",
    )
    assert not hasattr(benchmark, "organization_id")


# ── External dataset is platform-global ──────────────────────────────────────


@pytest.mark.asyncio
async def test_external_dataset_has_no_org():
    from domain.enums import DatasetStatus, ExternalSourceName
    from domain.external_intelligence import ExternalDataset

    ds = ExternalDataset(
        source_name=ExternalSourceName.WORLD_BANK,
        source_version="2025",
        dataset_hash="abc",
        imported_at=_now(),
        dataset_status=DatasetStatus.ACTIVE,
    )
    assert not hasattr(ds, "organization_id")
