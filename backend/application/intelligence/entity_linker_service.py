"""EntityLinkerService — DB wiring layer for the EntityLinker (ADR-013 / E2-F3).

Loads EntityCandidates from the database (suppliers + entity_aliases) and
applies the stateless EntityLinker to update supplier_id on unlinked signals
and metrics.

The minimum confidence threshold for accepting a link defaults to 0.7 (fuzzy
tier minimum). Callers can raise it to 0.9 (alias-only) or 1.0 (exact-only).
"""

from __future__ import annotations

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from application.intelligence.entity_linker import EntityLinker
from domain.entity_match import EntityCandidate, EntityMatch
from infrastructure.persistence.models.company_intelligence import (
    CompanyMetricModel,
    CompanySignalModel,
)
from infrastructure.persistence.models.entity_alias import EntityAliasModel
from infrastructure.persistence.models.supplier import SupplierModel

logger = structlog.get_logger(__name__)

_DEFAULT_MIN_CONFIDENCE: float = 0.7


async def load_candidates(
    org_id: str,
    session: AsyncSession,
) -> list[EntityCandidate]:
    """Load all suppliers for an org with their known aliases into EntityCandidates."""
    # Load all suppliers in this org
    supplier_rows = (await session.execute(
        select(SupplierModel).where(SupplierModel.organization_id == org_id)
    )).scalars().all()

    if not supplier_rows:
        return []

    supplier_ids = [s.id for s in supplier_rows]

    # Load all aliases for these suppliers
    alias_rows = (await session.execute(
        select(EntityAliasModel).where(EntityAliasModel.supplier_id.in_(supplier_ids))
    )).scalars().all()

    # Group aliases by supplier_id
    aliases_by_supplier: dict[str, list[str]] = {}
    for alias_row in alias_rows:
        aliases_by_supplier.setdefault(alias_row.supplier_id, []).append(alias_row.alias)

    candidates = [
        EntityCandidate(
            supplier_id=s.id,
            canonical_name=s.name,
            legal_name=s.legal_name,
            aliases=tuple(aliases_by_supplier.get(s.id, [])),
        )
        for s in supplier_rows
    ]

    logger.debug(
        "entity_linker_service.candidates_loaded",
        org_id=org_id,
        supplier_count=len(candidates),
        alias_count=len(alias_rows),
    )
    return candidates


async def link_signals(
    org_id: str,
    session: AsyncSession,
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
) -> dict:
    """Link unlinked CompanySignals to suppliers via EntityLinker.

    Signals with supplier_id=None are resolved by company_name.
    Only matches with confidence >= min_confidence are applied.

    Returns dict with linked/skipped/total counts.
    """
    candidates = await load_candidates(org_id, session)
    if not candidates:
        return {"linked": 0, "skipped": 0, "total": 0, "reason": "no_suppliers"}

    linker = EntityLinker()

    unlinked_signals = (await session.execute(
        select(CompanySignalModel).where(
            CompanySignalModel.organization_id == org_id,
            CompanySignalModel.supplier_id.is_(None),
        )
    )).scalars().all()

    linked = 0
    skipped = 0

    for signal in unlinked_signals:
        match: EntityMatch = linker.link(signal.company_name, candidates)
        if match.supplier_id and match.confidence >= min_confidence:
            signal.supplier_id = match.supplier_id
            session.add(signal)
            linked += 1
            logger.debug(
                "entity_linker_service.signal_linked",
                signal_id=signal.id,
                company_name=signal.company_name,
                supplier_id=match.supplier_id,
                confidence=match.confidence,
                method=match.match_method,
            )
        else:
            skipped += 1

    logger.info(
        "entity_linker_service.link_signals_done",
        org_id=org_id,
        total=len(unlinked_signals),
        linked=linked,
        skipped=skipped,
        min_confidence=min_confidence,
    )
    return {"linked": linked, "skipped": skipped, "total": len(unlinked_signals)}


async def link_metrics(
    org_id: str,
    session: AsyncSession,
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
) -> dict:
    """Link unlinked CompanyMetrics to suppliers via EntityLinker."""
    candidates = await load_candidates(org_id, session)
    if not candidates:
        return {"linked": 0, "skipped": 0, "total": 0, "reason": "no_suppliers"}

    linker = EntityLinker()

    unlinked_metrics = (await session.execute(
        select(CompanyMetricModel).where(
            CompanyMetricModel.organization_id == org_id,
            CompanyMetricModel.supplier_id.is_(None),
        )
    )).scalars().all()

    linked = 0
    skipped = 0

    for metric in unlinked_metrics:
        match: EntityMatch = linker.link(metric.company_name, candidates)
        if match.supplier_id and match.confidence >= min_confidence:
            metric.supplier_id = match.supplier_id
            session.add(metric)
            linked += 1
        else:
            skipped += 1

    logger.info(
        "entity_linker_service.link_metrics_done",
        org_id=org_id,
        total=len(unlinked_metrics),
        linked=linked,
        skipped=skipped,
    )
    return {"linked": linked, "skipped": skipped, "total": len(unlinked_metrics)}
