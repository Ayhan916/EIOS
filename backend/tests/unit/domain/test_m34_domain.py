"""M34 Domain entity tests."""

import pytest
from datetime import datetime, UTC

from domain.enums import (
    CountryRiskLevel,
    DatasetStatus,
    EntityStatus,
    ExternalSourceName,
    PercentileRank,
    RiskSignalType,
    SanctionsExposure,
    SignalSeverity,
)
from domain.external_intelligence import (
    CountryRiskProfile,
    ExternalDataset,
    ExternalRiskSignal,
    SectorBenchmark,
    SupplierEnrichment,
)


def _now():
    return datetime.now(UTC)


# ── ExternalDataset ────────────────────────────────────────────────────────────

class TestExternalDataset:
    def test_create_minimal(self):
        ds = ExternalDataset(
            source_name=ExternalSourceName.WORLD_BANK,
            source_version="2025-Q1",
            dataset_hash="abc123",
            imported_at=_now(),
            row_count=100,
            dataset_status=DatasetStatus.ACTIVE,
            description="World Bank governance data",
        )
        assert ds.source_name == ExternalSourceName.WORLD_BANK
        assert ds.dataset_status == DatasetStatus.ACTIVE
        assert ds.row_count == 100

    def test_id_auto_generated(self):
        ds = ExternalDataset(
            source_name=ExternalSourceName.TRANSPARENCY_INTERNATIONAL,
            source_version="2025",
            dataset_hash="xyz",
            imported_at=_now(),
        )
        assert ds.id is not None and len(ds.id) > 0

    def test_dataset_status_enum_values(self):
        assert DatasetStatus.ACTIVE.value == "active"
        assert DatasetStatus.SUPERSEDED.value == "superseded"
        assert DatasetStatus.ARCHIVED.value == "archived"

    def test_source_name_enum_values(self):
        assert ExternalSourceName.WORLD_BANK.value == "world_bank"
        assert ExternalSourceName.OFAC.value == "ofac"
        assert ExternalSourceName.SECTOR_ESG_BENCHMARK.value == "sector_esg_benchmark"


# ── CountryRiskProfile ─────────────────────────────────────────────────────────

class TestCountryRiskProfile:
    def test_create(self):
        profile = CountryRiskProfile(
            country_code="DE",
            country_name="Germany",
            dataset_id="ds-001",
            governance_score=85.0,
            corruption_score=20.0,
            labour_rights_score=75.0,
            environmental_risk_score=30.0,
            human_rights_score=80.0,
            sanctions_status="none",
            overall_risk_score=18.0,
            risk_level=CountryRiskLevel.LOW,
            source_name=ExternalSourceName.WORLD_BANK,
            source_version="2025",
            data_date="2025-01-01",
        )
        assert profile.country_code == "DE"
        assert profile.risk_level == CountryRiskLevel.LOW
        assert profile.overall_risk_score == 18.0

    def test_risk_level_enum_values(self):
        assert CountryRiskLevel.LOW.value == "low"
        assert CountryRiskLevel.MODERATE.value == "moderate"
        assert CountryRiskLevel.HIGH.value == "high"
        assert CountryRiskLevel.CRITICAL.value == "critical"

    def test_high_risk_profile(self):
        profile = CountryRiskProfile(
            country_code="XX",
            country_name="Test Country",
            dataset_id="ds-002",
            overall_risk_score=80.0,
            risk_level=CountryRiskLevel.CRITICAL,
            sanctions_status="comprehensive",
            source_name=ExternalSourceName.FRAGILE_STATES_INDEX,
            source_version="2025",
            data_date="2025-01-01",
        )
        assert profile.risk_level == CountryRiskLevel.CRITICAL
        assert profile.sanctions_status == "comprehensive"


# ── SectorBenchmark ────────────────────────────────────────────────────────────

class TestSectorBenchmark:
    def _make(self, **kwargs):
        defaults = dict(
            sector_id="sec-001",
            sector_name="Manufacturing",
            nace_code="C28",
            dataset_id="ds-bench-001",
            average_esg_score=60.0,
            average_risk_score=40.0,
            average_compliance_coverage=70.0,
            average_disclosure_readiness=65.0,
            supplier_count=150,
            p10_esg_score=30.0,
            p25_esg_score=45.0,
            p50_esg_score=60.0,
            p75_esg_score=75.0,
            p90_esg_score=88.0,
            source_name=ExternalSourceName.SECTOR_ESG_BENCHMARK,
            source_version="2025-Q1",
            benchmark_date="2025-03-01",
        )
        defaults.update(kwargs)
        return SectorBenchmark(**defaults)

    def test_create(self):
        b = self._make()
        assert b.sector_name == "Manufacturing"
        assert b.p50_esg_score == 60.0

    def test_percentile_spread(self):
        b = self._make()
        assert b.p10_esg_score < b.p25_esg_score < b.p50_esg_score < b.p75_esg_score < b.p90_esg_score


# ── ExternalRiskSignal ─────────────────────────────────────────────────────────

class TestExternalRiskSignal:
    def test_create(self):
        s = ExternalRiskSignal(
            signal_type=RiskSignalType.SANCTIONS,
            severity=SignalSeverity.CRITICAL,
            description="Confirmed OFAC SDN match",
            source_name=ExternalSourceName.OFAC,
            source_version="2025-06",
            observed_at=_now(),
            supplier_id="sup-abc",
            organization_id="org-xyz",
        )
        assert s.signal_type == RiskSignalType.SANCTIONS
        assert s.severity == SignalSeverity.CRITICAL
        assert s.is_active is True

    def test_signal_type_enum_values(self):
        assert RiskSignalType.SANCTIONS.value == "sanctions"
        assert RiskSignalType.CORRUPTION.value == "corruption"
        assert RiskSignalType.LABOUR_RIGHTS.value == "labour_rights"
        assert RiskSignalType.ENVIRONMENTAL.value == "environmental"
        assert RiskSignalType.GOVERNANCE.value == "governance"

    def test_signal_severity_enum_values(self):
        assert SignalSeverity.CRITICAL.value == "critical"
        assert SignalSeverity.HIGH.value == "high"
        assert SignalSeverity.MEDIUM.value == "medium"
        assert SignalSeverity.LOW.value == "low"


# ── SupplierEnrichment ─────────────────────────────────────────────────────────

class TestSupplierEnrichment:
    def test_create(self):
        e = SupplierEnrichment(
            supplier_id="sup-001",
            organization_id="org-001",
            country_code="CN",
            country_risk_level=CountryRiskLevel.HIGH,
            country_risk_score=70.0,
            sanctions_exposure=SanctionsExposure.NONE,
            sector_percentile=45.0,
            percentile_rank=PercentileRank.MEDIAN,
            benchmark_score=55.0,
            benchmark_explanation="Supplier is at the 45th percentile.",
            external_risk_score=38.5,
            combined_risk_score=45.0,
            enriched_at=_now(),
            dataset_version="2025-Q1",
            active_signal_count=0,
            status=EntityStatus.ACTIVE,
        )
        assert e.supplier_id == "sup-001"
        assert e.percentile_rank == PercentileRank.MEDIAN
        assert e.combined_risk_score == 45.0

    def test_percentile_rank_enum_values(self):
        assert PercentileRank.TOP_10.value == "top_10"
        assert PercentileRank.TOP_25.value == "top_25"
        assert PercentileRank.MEDIAN.value == "median"
        assert PercentileRank.BOTTOM_25.value == "bottom_25"
        assert PercentileRank.BOTTOM_10.value == "bottom_10"

    def test_sanctions_exposure_enum_values(self):
        assert SanctionsExposure.NONE.value == "none"
        assert SanctionsExposure.POTENTIAL.value == "potential"
        assert SanctionsExposure.CONFIRMED.value == "confirmed"
