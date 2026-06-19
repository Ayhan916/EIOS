"""M34 External Intelligence Repositories.

Provides CRUD and query access for the five M34 external-intelligence
tables. All global platform data (datasets, country risk, sector benchmarks)
is org-agnostic. Signals and enrichments are tenant-scoped by org_id.
"""

from __future__ import annotations

from typing import Sequence

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DatasetStatus
from domain.external_intelligence import (
    CountryRiskProfile,
    ExternalDataset,
    ExternalRiskSignal,
    SectorBenchmark,
    SupplierEnrichment,
)

logger = structlog.get_logger(__name__)


# ── External Datasets ─────────────────────────────────────────────────────────

class SQLExternalDatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, dataset: ExternalDataset) -> ExternalDataset:
        from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel
        model = ExternalDatasetModel(
            id=dataset.id,
            status=dataset.status.value if hasattr(dataset.status, "value") else dataset.status,
            version=dataset.version,
            owner=dataset.owner,
            created_by=dataset.created_by,
            updated_by=dataset.updated_by,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            source_name=dataset.source_name.value if hasattr(dataset.source_name, "value") else dataset.source_name,
            source_version=dataset.source_version,
            dataset_hash=dataset.dataset_hash,
            imported_at=dataset.imported_at,
            row_count=dataset.row_count,
            dataset_status=dataset.dataset_status.value if hasattr(dataset.dataset_status, "value") else dataset.dataset_status,
            description=dataset.description,
        )
        self._session.add(model)
        await self._session.flush()
        return dataset

    async def get_by_id(self, dataset_id: str) -> ExternalDataset | None:
        from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel
        row = await self._session.get(ExternalDatasetModel, dataset_id)
        return _dataset_to_domain(row) if row else None

    async def get_active_by_source(self, source_name: str) -> ExternalDataset | None:
        from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel
        stmt = (
            select(ExternalDatasetModel)
            .where(
                ExternalDatasetModel.source_name == source_name,
                ExternalDatasetModel.dataset_status == DatasetStatus.ACTIVE.value,
            )
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _dataset_to_domain(row) if row else None

    async def supersede_active(self, source_name: str) -> int:
        """Mark any ACTIVE dataset for source_name as SUPERSEDED. Returns count updated."""
        from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel
        stmt = (
            update(ExternalDatasetModel)
            .where(
                ExternalDatasetModel.source_name == source_name,
                ExternalDatasetModel.dataset_status == DatasetStatus.ACTIVE.value,
            )
            .values(dataset_status=DatasetStatus.SUPERSEDED.value)
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def list(
        self,
        source_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ExternalDataset]:
        from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel
        stmt = select(ExternalDatasetModel).limit(limit)
        if source_name:
            stmt = stmt.where(ExternalDatasetModel.source_name == source_name)
        if status:
            stmt = stmt.where(ExternalDatasetModel.dataset_status == status)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_dataset_to_domain(r) for r in rows]


# ── Country Risk Profiles ─────────────────────────────────────────────────────

class SQLCountryRiskProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, profile: CountryRiskProfile) -> CountryRiskProfile:
        from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel
        model = CountryRiskProfileModel(
            id=profile.id,
            status=profile.status.value if hasattr(profile.status, "value") else profile.status,
            version=profile.version,
            owner=profile.owner,
            created_by=profile.created_by,
            updated_by=profile.updated_by,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            country_code=profile.country_code,
            country_name=profile.country_name,
            dataset_id=profile.dataset_id,
            governance_score=profile.governance_score,
            corruption_score=profile.corruption_score,
            labour_rights_score=profile.labour_rights_score,
            environmental_risk_score=profile.environmental_risk_score,
            human_rights_score=profile.human_rights_score,
            sanctions_status=profile.sanctions_status,
            overall_risk_score=profile.overall_risk_score,
            risk_level=profile.risk_level.value if hasattr(profile.risk_level, "value") else profile.risk_level,
            source_name=profile.source_name.value if hasattr(profile.source_name, "value") else profile.source_name,
            source_version=profile.source_version,
            data_date=profile.data_date,
        )
        self._session.add(model)
        await self._session.flush()
        return profile

    async def get_by_country_code(self, country_code: str) -> CountryRiskProfile | None:
        from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel
        stmt = (
            select(CountryRiskProfileModel)
            .where(CountryRiskProfileModel.country_code == country_code)
            .order_by(CountryRiskProfileModel.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _country_risk_to_domain(row) if row else None

    async def get_by_country_and_dataset(
        self, country_code: str, dataset_id: str
    ) -> CountryRiskProfile | None:
        from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel
        stmt = select(CountryRiskProfileModel).where(
            CountryRiskProfileModel.country_code == country_code,
            CountryRiskProfileModel.dataset_id == dataset_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _country_risk_to_domain(row) if row else None

    async def list(
        self,
        risk_level: str | None = None,
        limit: int = 50,
    ) -> list[CountryRiskProfile]:
        from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel
        stmt = (
            select(CountryRiskProfileModel)
            .order_by(CountryRiskProfileModel.overall_risk_score.desc())
            .limit(limit)
        )
        if risk_level:
            stmt = stmt.where(CountryRiskProfileModel.risk_level == risk_level)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_country_risk_to_domain(r) for r in rows]


# ── Sector Benchmarks ─────────────────────────────────────────────────────────

class SQLSectorBenchmarkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, benchmark: SectorBenchmark) -> SectorBenchmark:
        from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel
        model = SectorBenchmarkModel(
            id=benchmark.id,
            status=benchmark.status.value if hasattr(benchmark.status, "value") else benchmark.status,
            version=benchmark.version,
            owner=benchmark.owner,
            created_by=benchmark.created_by,
            updated_by=benchmark.updated_by,
            created_at=benchmark.created_at,
            updated_at=benchmark.updated_at,
            sector_id=benchmark.sector_id,
            sector_name=benchmark.sector_name,
            nace_code=benchmark.nace_code,
            dataset_id=benchmark.dataset_id,
            average_esg_score=benchmark.average_esg_score,
            average_risk_score=benchmark.average_risk_score,
            average_compliance_coverage=benchmark.average_compliance_coverage,
            average_disclosure_readiness=benchmark.average_disclosure_readiness,
            supplier_count=benchmark.supplier_count,
            p10_esg_score=benchmark.p10_esg_score,
            p25_esg_score=benchmark.p25_esg_score,
            p50_esg_score=benchmark.p50_esg_score,
            p75_esg_score=benchmark.p75_esg_score,
            p90_esg_score=benchmark.p90_esg_score,
            source_name=benchmark.source_name.value if hasattr(benchmark.source_name, "value") else benchmark.source_name,
            source_version=benchmark.source_version,
            benchmark_date=benchmark.benchmark_date,
        )
        self._session.add(model)
        await self._session.flush()
        return benchmark

    async def get_by_sector_id(self, sector_id: str) -> SectorBenchmark | None:
        from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel
        stmt = (
            select(SectorBenchmarkModel)
            .where(SectorBenchmarkModel.sector_id == sector_id)
            .order_by(SectorBenchmarkModel.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _sector_benchmark_to_domain(row) if row else None

    async def get_by_nace(self, nace_code: str) -> SectorBenchmark | None:
        from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel
        stmt = (
            select(SectorBenchmarkModel)
            .where(SectorBenchmarkModel.nace_code == nace_code)
            .order_by(SectorBenchmarkModel.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _sector_benchmark_to_domain(row) if row else None

    async def get_by_sector_and_dataset(
        self, sector_id: str, dataset_id: str
    ) -> SectorBenchmark | None:
        from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel
        stmt = select(SectorBenchmarkModel).where(
            SectorBenchmarkModel.sector_id == sector_id,
            SectorBenchmarkModel.dataset_id == dataset_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _sector_benchmark_to_domain(row) if row else None

    async def list(self, limit: int = 50) -> list[SectorBenchmark]:
        from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel
        rows = (
            await self._session.execute(
                select(SectorBenchmarkModel)
                .order_by(SectorBenchmarkModel.sector_name.asc())
                .limit(limit)
            )
        ).scalars().all()
        return [_sector_benchmark_to_domain(r) for r in rows]


# ── External Risk Signals ─────────────────────────────────────────────────────

class SQLExternalRiskSignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, signal: ExternalRiskSignal) -> ExternalRiskSignal:
        from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel
        model = ExternalRiskSignalModel(
            id=signal.id,
            status=signal.status.value if hasattr(signal.status, "value") else signal.status,
            version=signal.version,
            owner=signal.owner,
            created_by=signal.created_by,
            updated_by=signal.updated_by,
            created_at=signal.created_at,
            updated_at=signal.updated_at,
            signal_type=signal.signal_type.value if hasattr(signal.signal_type, "value") else signal.signal_type,
            severity=signal.severity.value if hasattr(signal.severity, "value") else signal.severity,
            description=signal.description,
            source_name=signal.source_name.value if hasattr(signal.source_name, "value") else signal.source_name,
            source_version=signal.source_version,
            observed_at=signal.observed_at,
            dataset_id=signal.dataset_id or None,
            country_code=signal.country_code,
            sector_code=signal.sector_code,
            supplier_id=signal.supplier_id,
            organization_id=signal.organization_id,
            is_active=signal.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        return signal

    async def list_for_supplier(
        self,
        supplier_id: str,
        organization_id: str,
        active_only: bool = True,
        limit: int = 50,
    ) -> list[ExternalRiskSignal]:
        from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel
        stmt = (
            select(ExternalRiskSignalModel)
            .where(
                ExternalRiskSignalModel.supplier_id == supplier_id,
                ExternalRiskSignalModel.organization_id == organization_id,
            )
            .order_by(ExternalRiskSignalModel.observed_at.desc())
            .limit(limit)
        )
        if active_only:
            stmt = stmt.where(ExternalRiskSignalModel.is_active.is_(True))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_signal_to_domain(r) for r in rows]

    async def list_for_country(
        self,
        country_code: str,
        active_only: bool = True,
        limit: int = 50,
    ) -> list[ExternalRiskSignal]:
        from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel
        stmt = (
            select(ExternalRiskSignalModel)
            .where(ExternalRiskSignalModel.country_code == country_code)
            .order_by(ExternalRiskSignalModel.observed_at.desc())
            .limit(limit)
        )
        if active_only:
            stmt = stmt.where(ExternalRiskSignalModel.is_active.is_(True))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_signal_to_domain(r) for r in rows]

    async def list_active(
        self,
        organization_id: str,
        limit: int = 100,
    ) -> list[ExternalRiskSignal]:
        from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel
        rows = (
            await self._session.execute(
                select(ExternalRiskSignalModel)
                .where(
                    ExternalRiskSignalModel.organization_id == organization_id,
                    ExternalRiskSignalModel.is_active.is_(True),
                )
                .order_by(ExternalRiskSignalModel.observed_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_signal_to_domain(r) for r in rows]


# ── Supplier Enrichments ──────────────────────────────────────────────────────

class SQLSupplierEnrichmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, enrichment: SupplierEnrichment) -> SupplierEnrichment:
        from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel
        model = SupplierEnrichmentModel(
            id=enrichment.id,
            status=enrichment.status.value if hasattr(enrichment.status, "value") else enrichment.status,
            version=enrichment.version,
            owner=enrichment.owner,
            created_by=enrichment.created_by,
            updated_by=enrichment.updated_by,
            created_at=enrichment.created_at,
            updated_at=enrichment.updated_at,
            supplier_id=enrichment.supplier_id,
            organization_id=enrichment.organization_id,
            country_code=enrichment.country_code,
            country_risk_id=enrichment.country_risk_id or None,
            country_risk_level=enrichment.country_risk_level.value if hasattr(enrichment.country_risk_level, "value") else enrichment.country_risk_level,
            country_risk_score=enrichment.country_risk_score,
            sanctions_exposure=enrichment.sanctions_exposure.value if hasattr(enrichment.sanctions_exposure, "value") else enrichment.sanctions_exposure,
            sector_benchmark_id=enrichment.sector_benchmark_id or None,
            sector_percentile=enrichment.sector_percentile,
            percentile_rank=enrichment.percentile_rank.value if hasattr(enrichment.percentile_rank, "value") else enrichment.percentile_rank,
            benchmark_score=enrichment.benchmark_score,
            benchmark_explanation=enrichment.benchmark_explanation,
            external_risk_score=enrichment.external_risk_score,
            combined_risk_score=enrichment.combined_risk_score,
            enriched_at=enrichment.enriched_at,
            dataset_version=enrichment.dataset_version,
            active_signal_count=enrichment.active_signal_count,
        )
        self._session.add(model)
        await self._session.flush()
        return enrichment

    async def get(
        self,
        supplier_id: str,
        organization_id: str,
    ) -> SupplierEnrichment | None:
        from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel
        stmt = select(SupplierEnrichmentModel).where(
            SupplierEnrichmentModel.supplier_id == supplier_id,
            SupplierEnrichmentModel.organization_id == organization_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _enrichment_to_domain(row) if row else None

    async def list_high_risk(
        self,
        organization_id: str,
        min_combined_risk: float = 60.0,
        limit: int = 50,
    ) -> list[SupplierEnrichment]:
        from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel
        rows = (
            await self._session.execute(
                select(SupplierEnrichmentModel)
                .where(
                    SupplierEnrichmentModel.organization_id == organization_id,
                    SupplierEnrichmentModel.combined_risk_score >= min_combined_risk,
                )
                .order_by(SupplierEnrichmentModel.combined_risk_score.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_enrichment_to_domain(r) for r in rows]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dataset_to_domain(m) -> ExternalDataset:
    return ExternalDataset(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        source_name=m.source_name,
        source_version=m.source_version,
        dataset_hash=m.dataset_hash,
        imported_at=m.imported_at,
        row_count=m.row_count or 0,
        dataset_status=m.dataset_status,
        description=m.description or "",
    )


def _country_risk_to_domain(m) -> CountryRiskProfile:
    return CountryRiskProfile(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        country_code=m.country_code,
        country_name=m.country_name,
        dataset_id=m.dataset_id,
        governance_score=m.governance_score or 0.0,
        corruption_score=m.corruption_score or 0.0,
        labour_rights_score=m.labour_rights_score or 0.0,
        environmental_risk_score=m.environmental_risk_score or 0.0,
        human_rights_score=m.human_rights_score or 0.0,
        sanctions_status=m.sanctions_status or "none",
        overall_risk_score=m.overall_risk_score or 0.0,
        risk_level=m.risk_level or "low",
        source_name=m.source_name or "",
        source_version=m.source_version or "",
        data_date=m.data_date or "",
    )


def _sector_benchmark_to_domain(m) -> SectorBenchmark:
    return SectorBenchmark(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        sector_id=m.sector_id,
        sector_name=m.sector_name,
        nace_code=m.nace_code or "",
        dataset_id=m.dataset_id,
        average_esg_score=m.average_esg_score or 0.0,
        average_risk_score=m.average_risk_score or 0.0,
        average_compliance_coverage=m.average_compliance_coverage or 0.0,
        average_disclosure_readiness=m.average_disclosure_readiness or 0.0,
        supplier_count=m.supplier_count or 0,
        p10_esg_score=m.p10_esg_score or 0.0,
        p25_esg_score=m.p25_esg_score or 0.0,
        p50_esg_score=m.p50_esg_score or 0.0,
        p75_esg_score=m.p75_esg_score or 0.0,
        p90_esg_score=m.p90_esg_score or 0.0,
        source_name=m.source_name or "",
        source_version=m.source_version or "",
        benchmark_date=m.benchmark_date or "",
    )


def _signal_to_domain(m) -> ExternalRiskSignal:
    return ExternalRiskSignal(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        signal_type=m.signal_type,
        severity=m.severity,
        description=m.description or "",
        source_name=m.source_name,
        source_version=m.source_version,
        observed_at=m.observed_at,
        dataset_id=m.dataset_id or "",
        country_code=m.country_code or "",
        sector_code=m.sector_code or "",
        supplier_id=m.supplier_id or "",
        organization_id=m.organization_id or "",
        is_active=m.is_active if m.is_active is not None else True,
    )


def _enrichment_to_domain(m) -> SupplierEnrichment:
    from domain.enums import CountryRiskLevel, PercentileRank, SanctionsExposure
    return SupplierEnrichment(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        supplier_id=m.supplier_id,
        organization_id=m.organization_id,
        country_code=m.country_code or "",
        country_risk_id=m.country_risk_id or "",
        country_risk_level=m.country_risk_level or CountryRiskLevel.LOW,
        country_risk_score=m.country_risk_score or 0.0,
        sanctions_exposure=m.sanctions_exposure or SanctionsExposure.NONE,
        sector_benchmark_id=m.sector_benchmark_id or "",
        sector_percentile=m.sector_percentile or 0.0,
        percentile_rank=m.percentile_rank or PercentileRank.MEDIAN,
        benchmark_score=m.benchmark_score or 0.0,
        benchmark_explanation=m.benchmark_explanation or "",
        external_risk_score=m.external_risk_score or 0.0,
        combined_risk_score=m.combined_risk_score or 0.0,
        enriched_at=m.enriched_at,
        dataset_version=m.dataset_version or "",
        active_signal_count=m.active_signal_count or 0,
    )
