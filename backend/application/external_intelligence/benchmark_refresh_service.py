"""Benchmark Refresh Service — M34.1 / M34.2.

When a new external dataset becomes ACTIVE, this service:
  1. Refreshes relevant SectorBenchmarks tied to the dataset
  2. Re-runs SupplierEnrichment for affected suppliers

M34.2 H3 hardening:
  - refresh_for_dataset() now accepts connector_name to scope by source type
  - Eliminates N+1: all SupplierScoreModel rows are batch-loaded in one query
  - Country connectors only refresh country-enriched suppliers
  - Sanctions connectors only refresh suppliers with sanctions exposure
  - Sector connectors refresh all enrichments (sector scope)

Historical snapshots are preserved (enrichments are upserted, not deleted).
Benchmark refresh is tracked with Prometheus-compatible counters.
"""

from __future__ import annotations

import structlog

from application.external_intelligence.metrics import ext_counters

logger = structlog.get_logger(__name__)

# Connectors that affect country-risk-based enrichment
_COUNTRY_CONNECTORS = frozenset({"world_bank", "transparency_international", "ilo", "unicef"})

# Connectors that affect sanctions exposure
_SANCTIONS_CONNECTORS = frozenset({"un_sanctions", "eu_sanctions"})


async def refresh_for_dataset(
    dataset_id: str,
    connector_name: str,
    session,
) -> int:
    """Re-run enrichment for all suppliers affected by a new dataset.

    H3: Scopes enrichments by connector type to avoid unnecessary refreshes.
    H3: Batch-loads SupplierScoreModel to eliminate N+1 queries.

    Returns the number of enrichments refreshed.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel

    enrichment_stmt = select(SupplierEnrichmentModel)

    if connector_name in _COUNTRY_CONNECTORS:
        enrichment_stmt = enrichment_stmt.where(SupplierEnrichmentModel.country_code.isnot(None))
    elif connector_name in _SANCTIONS_CONNECTORS:
        enrichment_stmt = enrichment_stmt.where(
            SupplierEnrichmentModel.sanctions_exposure != "none"
        )
    # else: sector connectors or unknown — refresh all

    rows = (await session.execute(enrichment_stmt)).scalars().all()
    if not rows:
        return 0

    # H3: batch-load supplier scores in a single query

    supplier_ids = list({r.supplier_id for r in rows})
    scores_by_supplier = await _batch_load_supplier_scores(supplier_ids, session)

    count = 0
    for enrichment_row in rows:
        try:
            internal_esg = scores_by_supplier.get(
                enrichment_row.supplier_id,
                float(enrichment_row.benchmark_score or 50.0),
            )
            await _refresh_single_enrichment_with_score(
                enrichment_row, dataset_id, internal_esg, session
            )
            count += 1
        except Exception as exc:
            logger.warning(
                "enrichment_refresh_failed",
                supplier_id=enrichment_row.supplier_id,
                connector=connector_name,
                error=str(exc),
            )

    if count > 0:
        ext_counters.record_benchmark_refresh()
        logger.info(
            "benchmark_refresh_complete",
            dataset_id=dataset_id,
            connector=connector_name,
            enrichments_refreshed=count,
        )

    return count


async def _batch_load_supplier_scores(
    supplier_ids: list[str],
    session,
) -> dict[str, float]:
    """Return {supplier_id: latest_overall_score} in a single query."""
    if not supplier_ids:
        return {}

    from sqlalchemy import func, select

    from infrastructure.persistence.models.supplier_score import SupplierScoreModel

    # Subquery: latest created_at per supplier_id
    subq = (
        select(
            SupplierScoreModel.supplier_id,
            func.max(SupplierScoreModel.created_at).label("max_created"),
        )
        .where(SupplierScoreModel.supplier_id.in_(supplier_ids))
        .group_by(SupplierScoreModel.supplier_id)
        .subquery()
    )

    stmt = select(SupplierScoreModel).join(
        subq,
        (SupplierScoreModel.supplier_id == subq.c.supplier_id)
        & (SupplierScoreModel.created_at == subq.c.max_created),
    )
    score_rows = (await session.execute(stmt)).scalars().all()
    return {r.supplier_id: float(r.overall_score) for r in score_rows}


async def refresh_all_enrichments(organization_id: str, session) -> int:
    """Re-run enrichment for every supplier in an organization."""
    from sqlalchemy import select

    from infrastructure.persistence.models.external_intelligence import SupplierEnrichmentModel

    stmt = select(SupplierEnrichmentModel).where(
        SupplierEnrichmentModel.organization_id == organization_id
    )
    rows = (await session.execute(stmt)).scalars().all()
    if not rows:
        return 0

    supplier_ids = list({r.supplier_id for r in rows})
    scores_by_supplier = await _batch_load_supplier_scores(supplier_ids, session)

    count = 0
    for row in rows:
        try:
            internal_esg = scores_by_supplier.get(
                row.supplier_id,
                float(row.benchmark_score or 50.0),
            )
            await _refresh_single_enrichment_with_score(row, "", internal_esg, session)
            count += 1
        except Exception as exc:
            logger.warning(
                "enrichment_refresh_failed",
                supplier_id=row.supplier_id,
                org=organization_id,
                error=str(exc),
            )

    if count > 0:
        ext_counters.record_benchmark_refresh()

    return count


async def _refresh_single_enrichment_with_score(
    enrichment_row,
    dataset_id: str,
    internal_esg_score: float,
    session,
) -> None:
    """Re-run enrich_supplier() for one enrichment row using pre-loaded score."""
    from application.external_intelligence.enrichment_service import enrich_supplier

    await enrich_supplier(
        supplier_id=enrichment_row.supplier_id,
        organization_id=enrichment_row.organization_id,
        country_code=enrichment_row.country_code or "",
        sector_id="",
        nace_code="",
        internal_esg_score=internal_esg_score,
        session=session,
        dataset_version=dataset_id,
    )


# Keep old signature for backward compatibility with existing call sites
async def _refresh_single_enrichment(enrichment_row, dataset_id: str, session) -> None:
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_score import SupplierScoreModel

    score_stmt = (
        select(SupplierScoreModel)
        .where(SupplierScoreModel.supplier_id == enrichment_row.supplier_id)
        .order_by(SupplierScoreModel.created_at.desc())
        .limit(1)
    )
    score_row = (await session.execute(score_stmt)).scalar_one_or_none()
    internal_esg = (
        float(score_row.overall_score)
        if score_row
        else float(enrichment_row.benchmark_score or 50.0)
    )
    await _refresh_single_enrichment_with_score(enrichment_row, dataset_id, internal_esg, session)
