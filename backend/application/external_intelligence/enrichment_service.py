"""Supplier Enrichment Service — M34.

Produces a SupplierEnrichment by combining:
  - Internal supplier score (ESG score from SupplierScore)
  - Country risk profile (from external datasets)
  - Sector benchmark position (from external datasets)
  - Active adverse signals count

The resulting SupplierEnrichment is tenant-scoped and persisted
per supplier per organisation. Re-running enrichment on updated external
data supersedes the prior record.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import CountryRiskLevel, EntityStatus, PercentileRank, SanctionsExposure
from domain.external_intelligence import SupplierEnrichment

from .benchmark_engine import benchmark_supplier
from .country_risk_service import get_country_risk
from .sector_benchmark_service import get_benchmark_by_nace, get_sector_benchmark
from .signal_service import list_signals_for_supplier

logger = structlog.get_logger(__name__)

_COUNTRY_RISK_WEIGHT = 0.4
_BENCHMARK_WEIGHT = 0.3
_SIGNAL_WEIGHT = 0.3


async def enrich_supplier(
    supplier_id: str,
    organization_id: str,
    country_code: str,
    sector_id: str,
    nace_code: str,
    internal_esg_score: float,
    session: AsyncSession,
    dataset_version: str = "",
) -> SupplierEnrichment:
    """Build or refresh a SupplierEnrichment for a supplier.

    Steps:
    1. Fetch country risk profile
    2. Fetch sector benchmark
    3. Run benchmark engine (pure)
    4. Count active adverse signals
    5. Calculate combined_risk_score
    6. Persist and return
    """
    from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel

    # 1. Country risk
    country_profile = await get_country_risk(country_code, session) if country_code else None
    country_risk_score = country_profile.overall_risk_score if country_profile else 0.0
    country_risk_level = country_profile.risk_level if country_profile else CountryRiskLevel.LOW
    country_risk_id = country_profile.id if country_profile else ""
    sanctions_status = country_profile.sanctions_status if country_profile else "none"
    sanctions_exposure = (
        SanctionsExposure.CONFIRMED
        if sanctions_status == "comprehensive"
        else SanctionsExposure.POTENTIAL
        if sanctions_status == "partial"
        else SanctionsExposure.NONE
    )

    # 2 & 3. Sector benchmark
    benchmark = None
    if nace_code:
        benchmark = await get_benchmark_by_nace(nace_code, session)
    if benchmark is None and sector_id:
        benchmark = await get_sector_benchmark(sector_id, session)

    percentile = 50.0
    rank = PercentileRank.MEDIAN
    benchmark_score = 0.0
    benchmark_explanation = "No sector benchmark available."
    sector_benchmark_id = ""

    if benchmark is not None:
        br = benchmark_supplier(supplier_id, internal_esg_score, benchmark)
        percentile = br.percentile
        rank = br.percentile_rank
        benchmark_score = br.benchmark_score
        benchmark_explanation = br.explanation
        sector_benchmark_id = benchmark.id

    # 4. Active signals
    signals = await list_signals_for_supplier(supplier_id, organization_id, session)
    active_signal_count = len(signals)

    # 5. Combined risk score
    # Country risk: higher = worse (0–100)
    # Benchmark: supplier percentile inverted to risk (100 - percentile = risk proxy)
    # Signal penalty: 5 per active signal, capped at 30
    benchmark_risk = max(0.0, 100.0 - percentile)
    signal_penalty = min(active_signal_count * 5.0, 30.0)

    external_risk = (
        country_risk_score * _COUNTRY_RISK_WEIGHT
        + benchmark_risk * _BENCHMARK_WEIGHT
        + signal_penalty * _SIGNAL_WEIGHT
    )
    external_risk = max(0.0, min(100.0, external_risk))

    # Combined = blend internal (ESG inverted) with external
    internal_risk = max(0.0, 100.0 - internal_esg_score)
    combined_risk = (internal_risk * 0.5) + (external_risk * 0.5)

    enrichment = SupplierEnrichment(
        supplier_id=supplier_id,
        organization_id=organization_id,
        country_code=country_code,
        country_risk_id=country_risk_id,
        country_risk_level=country_risk_level,
        country_risk_score=round(country_risk_score, 2),
        sanctions_exposure=sanctions_exposure,
        sector_benchmark_id=sector_benchmark_id,
        sector_percentile=round(percentile, 1),
        percentile_rank=rank,
        benchmark_score=round(benchmark_score, 2),
        benchmark_explanation=benchmark_explanation,
        external_risk_score=round(external_risk, 2),
        combined_risk_score=round(combined_risk, 2),
        enriched_at=datetime.now(UTC),
        dataset_version=dataset_version,
        active_signal_count=active_signal_count,
        status=EntityStatus.ACTIVE,
    )

    # Upsert: update existing enrichment for this supplier/org or create new
    existing_stmt = select(SupplierEnrichmentModel).where(
        SupplierEnrichmentModel.supplier_id == supplier_id,
        SupplierEnrichmentModel.organization_id == organization_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()

    if existing is not None:
        # Update in place
        _update_model(existing, enrichment)
        session.add(existing)
        await session.flush()
        enrichment.id = existing.id
    else:
        model = _domain_to_model(enrichment)
        session.add(model)
        await session.flush()

    logger.info(
        "supplier_enriched",
        supplier_id=supplier_id,
        org_id=organization_id,
        country_risk=round(country_risk_score, 1),
        percentile=round(percentile, 1),
        combined_risk=round(combined_risk, 2),
    )
    return enrichment


async def get_enrichment(
    supplier_id: str,
    organization_id: str,
    session: AsyncSession,
) -> SupplierEnrichment | None:
    """Return the current enrichment for a supplier."""
    from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel

    stmt = select(SupplierEnrichmentModel).where(
        SupplierEnrichmentModel.supplier_id == supplier_id,
        SupplierEnrichmentModel.organization_id == organization_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _model_to_domain(row) if row else None


async def list_high_risk_suppliers(
    organization_id: str,
    session: AsyncSession,
    min_combined_risk: float = 60.0,
    limit: int = 50,
) -> list[SupplierEnrichment]:
    """Return suppliers with combined_risk_score above threshold."""
    from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel

    stmt = (
        select(SupplierEnrichmentModel)
        .where(
            SupplierEnrichmentModel.organization_id == organization_id,
            SupplierEnrichmentModel.combined_risk_score >= min_combined_risk,
        )
        .order_by(SupplierEnrichmentModel.combined_risk_score.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


def _domain_to_model(e: SupplierEnrichment):
    from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel
    return SupplierEnrichmentModel(
        id=e.id,
        status=e.status.value if hasattr(e.status, "value") else e.status,
        version=e.version,
        owner=e.owner,
        created_by=e.created_by,
        updated_by=e.updated_by,
        created_at=e.created_at,
        updated_at=e.updated_at,
        supplier_id=e.supplier_id,
        organization_id=e.organization_id,
        country_code=e.country_code,
        country_risk_id=e.country_risk_id or None,
        country_risk_level=e.country_risk_level.value if hasattr(e.country_risk_level, "value") else e.country_risk_level,
        country_risk_score=e.country_risk_score,
        sanctions_exposure=e.sanctions_exposure.value if hasattr(e.sanctions_exposure, "value") else e.sanctions_exposure,
        sector_benchmark_id=e.sector_benchmark_id or None,
        sector_percentile=e.sector_percentile,
        percentile_rank=e.percentile_rank.value if hasattr(e.percentile_rank, "value") else e.percentile_rank,
        benchmark_score=e.benchmark_score,
        benchmark_explanation=e.benchmark_explanation,
        external_risk_score=e.external_risk_score,
        combined_risk_score=e.combined_risk_score,
        enriched_at=e.enriched_at,
        dataset_version=e.dataset_version,
        active_signal_count=e.active_signal_count,
    )


def _update_model(model, e: SupplierEnrichment) -> None:
    """In-place update of existing enrichment model."""
    from datetime import UTC, datetime
    model.country_code = e.country_code
    model.country_risk_id = e.country_risk_id or None
    model.country_risk_level = e.country_risk_level.value if hasattr(e.country_risk_level, "value") else e.country_risk_level
    model.country_risk_score = e.country_risk_score
    model.sanctions_exposure = e.sanctions_exposure.value if hasattr(e.sanctions_exposure, "value") else e.sanctions_exposure
    model.sector_benchmark_id = e.sector_benchmark_id or None
    model.sector_percentile = e.sector_percentile
    model.percentile_rank = e.percentile_rank.value if hasattr(e.percentile_rank, "value") else e.percentile_rank
    model.benchmark_score = e.benchmark_score
    model.benchmark_explanation = e.benchmark_explanation
    model.external_risk_score = e.external_risk_score
    model.combined_risk_score = e.combined_risk_score
    model.enriched_at = e.enriched_at
    model.dataset_version = e.dataset_version
    model.active_signal_count = e.active_signal_count
    model.updated_at = datetime.now(UTC)


def _model_to_domain(m) -> SupplierEnrichment:
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
