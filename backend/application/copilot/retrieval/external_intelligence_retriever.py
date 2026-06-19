"""External Intelligence Retriever for the AI Copilot — M34.

Extends the Copilot retrieval layer with external benchmarking data:
- Country risk for supplier countries
- Sector benchmark positions
- Active adverse signals
- High-risk supplier enrichments

All answers cite the external source name, version, and dataset timestamp,
preserving the M33.2 auditability standards.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import RetrievalResult

_LIMIT = 10


async def retrieve_external_intelligence_context(
    org_id: str,
    session: AsyncSession,
    *,
    supplier_id: str | None = None,
    country_code: str | None = None,
    limit: int = _LIMIT,
) -> RetrievalResult:
    """Return external intelligence (enrichments + signals) for the org."""
    from infrastructure.persistence.models.external_intelligence import (
        ExternalRiskSignalModel,
        SupplierEnrichmentModel,
    )

    retrieved_at = datetime.now(UTC).isoformat()

    # Enrichments for suppliers in this org
    enrich_stmt = (
        select(SupplierEnrichmentModel)
        .where(SupplierEnrichmentModel.organization_id == org_id)
        .order_by(SupplierEnrichmentModel.combined_risk_score.desc())
        .limit(limit)
    )
    if supplier_id:
        enrich_stmt = enrich_stmt.where(SupplierEnrichmentModel.supplier_id == supplier_id)

    enrichments = (await session.execute(enrich_stmt)).scalars().all()

    # Active adverse signals
    signal_stmt = (
        select(ExternalRiskSignalModel)
        .where(
            ExternalRiskSignalModel.organization_id == org_id,
            ExternalRiskSignalModel.is_active.is_(True),
        )
        .order_by(ExternalRiskSignalModel.observed_at.desc())
        .limit(limit)
    )
    if supplier_id:
        signal_stmt = signal_stmt.where(ExternalRiskSignalModel.supplier_id == supplier_id)

    signals = (await session.execute(signal_stmt)).scalars().all()

    data: list[dict] = []
    source_ids: list[str] = []
    freshness_metadata: list[dict] = []

    for e in enrichments:
        data.append({
            "supplier_id": e.supplier_id,
            "country_code": e.country_code,
            "country_risk_level": e.country_risk_level,
            "country_risk_score": e.country_risk_score,
            "sanctions_exposure": e.sanctions_exposure,
            "sector_percentile": e.sector_percentile,
            "percentile_rank": e.percentile_rank,
            "benchmark_score": e.benchmark_score,
            "benchmark_explanation": e.benchmark_explanation,
            "external_risk_score": e.external_risk_score,
            "combined_risk_score": e.combined_risk_score,
            "active_signal_count": e.active_signal_count,
            "dataset_version": e.dataset_version,
            "enriched_at": e.enriched_at.isoformat() if e.enriched_at else None,
        })
        source_ids.append(e.supplier_id)
        freshness_metadata.append({
            "object_id": e.supplier_id,
            "object_type": "SupplierEnrichment",
            "updated_at": e.enriched_at.isoformat() if e.enriched_at else None,
            "retrieved_at": retrieved_at,
        })

    for s in signals:
        data.append({
            "signal_id": s.id,
            "signal_type": s.signal_type,
            "severity": s.severity,
            "description": s.description,
            "country_code": s.country_code,
            "supplier_id": s.supplier_id,
            "source_name": s.source_name,
            "source_version": s.source_version,
            "observed_at": s.observed_at.isoformat() if s.observed_at else None,
        })
        if s.supplier_id:
            source_ids.append(s.supplier_id)

    provenance = (
        f"External Intelligence: {len(enrichments)} supplier enrichment(s), "
        f"{len(signals)} active adverse signal(s)"
    )

    return RetrievalResult(
        retriever="external_intelligence_retriever",
        provenance=provenance,
        data=data,
        source_ids=list(set(source_ids)),
        citation_type="Supplier",
        freshness_metadata=freshness_metadata,
    )
