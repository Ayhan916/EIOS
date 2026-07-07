"""M38 Relationship Discovery Engine.

Automatically detects supplier relationships from:
  1. Shared country
  2. Shared sector/industry
  3. Common sanctions events (external intelligence)
  4. Common regulatory finding patterns
  5. Common ownership metadata

All suggestions are PENDING until a human approves or rejects them.
Audit events are emitted on approval and rejection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from application.network.metrics import network_counters

logger = structlog.get_logger(__name__)


async def _log_audit_event(
    session,
    action: str,
    entity_id: str,
    detail: str = "",
    actor_id: str = "network_discovery_engine",
) -> None:
    from infrastructure.persistence.models.audit_event import AuditEventModel

    now = datetime.now(UTC)
    try:
        event = AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action=action,
            actor_id=actor_id,
            entity_type="suggested_relationship",
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata={},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("network_audit_failed", action=action, error=str(exc))


async def _create_suggestion(
    organization_id: str,
    supplier_id: str,
    related_supplier_id: str,
    relationship_type: str,
    confidence: float,
    rationale: str,
    suggestion_source: str,
    calculation_inputs: dict,
    session,
) -> object | None:
    """Create a SuggestedRelationshipModel if no duplicate PENDING suggestion exists."""
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SuggestedRelationshipModel

    # De-duplicate: skip if a PENDING suggestion for this pair already exists
    dedup_stmt = select(SuggestedRelationshipModel).where(
        SuggestedRelationshipModel.organization_id == organization_id,
        SuggestedRelationshipModel.supplier_id == supplier_id,
        SuggestedRelationshipModel.related_supplier_id == related_supplier_id,
        SuggestedRelationshipModel.relationship_type == relationship_type,
        SuggestedRelationshipModel.suggestion_status == "PENDING",
    )
    existing = (await session.execute(dedup_stmt)).scalar_one_or_none()
    if existing is not None:
        return None

    now = datetime.now(UTC)
    suggestion = SuggestedRelationshipModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        organization_id=organization_id,
        supplier_id=supplier_id,
        related_supplier_id=related_supplier_id,
        relationship_type=relationship_type,
        confidence=round(confidence, 4),
        rationale=rationale,
        suggestion_source=suggestion_source,
        suggestion_status="PENDING",
        calculation_inputs=calculation_inputs,
    )
    session.add(suggestion)
    await session.flush()
    network_counters.record_suggestion_created()
    return suggestion


async def discover_shared_country(
    organization_id: str,
    session,
) -> list[object]:
    """Suggest SHARED_COUNTRY relationships for supplier pairs in the same country."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier import SupplierModel

    stmt = select(SupplierModel.id, SupplierModel.country).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
        SupplierModel.country != "",
        SupplierModel.country.is_not(None),
    )
    rows = (await session.execute(stmt)).all()

    by_country: dict[str, list[str]] = {}
    for row in rows:
        by_country.setdefault(row.country, []).append(row.id)

    suggestions = []
    for country, supplier_ids in by_country.items():
        if len(supplier_ids) < 2:
            continue
        # Only suggest for first 10 pairs per country to limit noise
        pairs = 0
        for i, a in enumerate(supplier_ids):
            for b in supplier_ids[i + 1 :]:
                if pairs >= 10:
                    break
                s = await _create_suggestion(
                    organization_id=organization_id,
                    supplier_id=a,
                    related_supplier_id=b,
                    relationship_type="SHARED_COUNTRY",
                    confidence=0.5,
                    rationale=f"Both suppliers operate in {country}",
                    suggestion_source="DISCOVERY_COUNTRY",
                    calculation_inputs={"country": country},
                    session=session,
                )
                if s:
                    suggestions.append(s)
                pairs += 1

    return suggestions


async def discover_shared_sector(
    organization_id: str,
    session,
) -> list[object]:
    """Suggest SHARED_SECTOR relationships for supplier pairs in the same industry."""
    from sqlalchemy import select

    from infrastructure.persistence.models.supplier import SupplierModel

    stmt = select(SupplierModel.id, SupplierModel.industry).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
        SupplierModel.industry != "",
        SupplierModel.industry.is_not(None),
    )
    rows = (await session.execute(stmt)).all()

    by_sector: dict[str, list[str]] = {}
    for row in rows:
        by_sector.setdefault(row.industry, []).append(row.id)

    suggestions = []
    for sector, supplier_ids in by_sector.items():
        if len(supplier_ids) < 2:
            continue
        pairs = 0
        for i, a in enumerate(supplier_ids):
            for b in supplier_ids[i + 1 :]:
                if pairs >= 10:
                    break
                s = await _create_suggestion(
                    organization_id=organization_id,
                    supplier_id=a,
                    related_supplier_id=b,
                    relationship_type="SHARED_SECTOR",
                    confidence=0.4,
                    rationale=f"Both suppliers operate in {sector}",
                    suggestion_source="DISCOVERY_SECTOR",
                    calculation_inputs={"sector": sector},
                    session=session,
                )
                if s:
                    suggestions.append(s)
                pairs += 1

    return suggestions


async def discover_shared_sanctions(
    organization_id: str,
    session,
) -> list[object]:
    """Suggest SHARED_INCIDENT relationships when two suppliers share a sanctions event.

    Uses M34 ExternalIntelligenceDatasetModel with type containing 'sanction'.
    Only active, validated datasets.
    """
    try:
        from sqlalchemy import select

        from infrastructure.persistence.models.external_intelligence import (
            ExternalIntelligenceDatasetModel,
        )

        stmt = select(
            ExternalIntelligenceDatasetModel.supplier_id,
            ExternalIntelligenceDatasetModel.dataset_type,
            ExternalIntelligenceDatasetModel.source_name,
        ).where(
            ExternalIntelligenceDatasetModel.organization_id == organization_id,
            ExternalIntelligenceDatasetModel.dataset_status == "ACTIVE",
            ExternalIntelligenceDatasetModel.supplier_id.is_not(None),
        )
        rows = (await session.execute(stmt)).all()
    except Exception:
        return []

    by_type: dict[str, list[str]] = {}
    for row in rows:
        if "sanction" in (row.dataset_type or "").lower():
            by_type.setdefault(row.dataset_type, []).append(row.supplier_id)

    suggestions = []
    for dtype, supplier_ids in by_type.items():
        unique_ids = list(set(supplier_ids))
        if len(unique_ids) < 2:
            continue
        for i, a in enumerate(unique_ids[:10]):
            for b in unique_ids[i + 1 : 10]:
                s = await _create_suggestion(
                    organization_id=organization_id,
                    supplier_id=a,
                    related_supplier_id=b,
                    relationship_type="SHARED_INCIDENT",
                    confidence=0.8,
                    rationale=f"Both suppliers appear in sanctions dataset: {dtype}",
                    suggestion_source="DISCOVERY_SANCTIONS",
                    calculation_inputs={"dataset_type": dtype},
                    session=session,
                )
                if s:
                    suggestions.append(s)

    return suggestions


async def discover_shared_regulatory_exposure(
    organization_id: str,
    session,
) -> list[object]:
    """Suggest SHARED_REGULATORY_EXPOSURE for suppliers with the same framework failures."""
    try:
        from sqlalchemy import select

        from infrastructure.persistence.models.regulatory import ComplianceGapModel

        stmt = select(
            ComplianceGapModel.supplier_id,
            ComplianceGapModel.framework_id,
        ).where(
            ComplianceGapModel.organization_id == organization_id,
            ComplianceGapModel.supplier_id.is_not(None),
        )
        rows = (await session.execute(stmt)).all()
    except Exception:
        return []

    by_framework: dict[str, list[str]] = {}
    for row in rows:
        if row.framework_id:
            by_framework.setdefault(row.framework_id, []).append(row.supplier_id)

    suggestions = []
    for fw, supplier_ids in by_framework.items():
        unique_ids = list(set(supplier_ids))
        if len(unique_ids) < 2:
            continue
        for i, a in enumerate(unique_ids[:10]):
            for b in unique_ids[i + 1 : 10]:
                s = await _create_suggestion(
                    organization_id=organization_id,
                    supplier_id=a,
                    related_supplier_id=b,
                    relationship_type="SHARED_REGULATORY_EXPOSURE",
                    confidence=0.6,
                    rationale=f"Both suppliers have compliance gaps in framework {fw}",
                    suggestion_source="DISCOVERY_REGULATORY",
                    calculation_inputs={"framework_id": fw},
                    session=session,
                )
                if s:
                    suggestions.append(s)

    return suggestions


async def run_discovery(
    organization_id: str,
    session,
) -> dict[str, int]:
    """Run all discovery engines and return counts per source."""
    country = await discover_shared_country(organization_id, session)
    sector = await discover_shared_sector(organization_id, session)
    sanctions = await discover_shared_sanctions(organization_id, session)
    regulatory = await discover_shared_regulatory_exposure(organization_id, session)

    return {
        "shared_country": len(country),
        "shared_sector": len(sector),
        "shared_sanctions": len(sanctions),
        "shared_regulatory": len(regulatory),
        "total": len(country) + len(sector) + len(sanctions) + len(regulatory),
    }


async def list_suggestions(
    organization_id: str,
    suggestion_status: str | None = None,
    limit: int = 100,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SuggestedRelationshipModel

    stmt = select(SuggestedRelationshipModel).where(
        SuggestedRelationshipModel.organization_id == organization_id
    )
    if suggestion_status:
        stmt = stmt.where(SuggestedRelationshipModel.suggestion_status == suggestion_status.upper())
    stmt = stmt.order_by(SuggestedRelationshipModel.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def approve_suggestion(
    suggestion_id: str,
    organization_id: str,
    approved_by: str,
    session,
) -> object:
    """Approve a suggested relationship.

    Creates a SupplierRelationshipModel from the suggestion and marks it APPROVED.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.network import (
        SuggestedRelationshipModel,
    )

    stmt = select(SuggestedRelationshipModel).where(
        SuggestedRelationshipModel.id == suggestion_id,
        SuggestedRelationshipModel.organization_id == organization_id,
    )
    suggestion = (await session.execute(stmt)).scalar_one_or_none()
    if suggestion is None:
        raise ValueError(f"Suggestion not found: {suggestion_id}")
    if suggestion.suggestion_status != "PENDING":
        raise ValueError(f"Suggestion already {suggestion.suggestion_status}")

    now = datetime.now(UTC)
    suggestion.suggestion_status = "APPROVED"
    suggestion.reviewed_by = approved_by
    suggestion.reviewed_at = now
    suggestion.updated_at = now
    await session.flush()

    from application.network.relationship_service import create_relationship

    await create_relationship(
        organization_id=organization_id,
        supplier_id=suggestion.supplier_id,
        related_supplier_id=suggestion.related_supplier_id,
        relationship_type=suggestion.relationship_type,
        confidence=suggestion.confidence,
        source="DISCOVERY",
        rationale=suggestion.rationale,
        created_by=approved_by,
        session=session,
    )

    await _log_audit_event(
        session,
        "network.suggestion.approved",
        suggestion.id,
        detail=f"approved_by={approved_by} type={suggestion.relationship_type}",
        actor_id=approved_by,
    )
    return suggestion


async def reject_suggestion(
    suggestion_id: str,
    organization_id: str,
    rejected_by: str,
    review_note: str = "",
    session=None,
) -> object:
    from sqlalchemy import select

    from infrastructure.persistence.models.network import SuggestedRelationshipModel

    stmt = select(SuggestedRelationshipModel).where(
        SuggestedRelationshipModel.id == suggestion_id,
        SuggestedRelationshipModel.organization_id == organization_id,
    )
    suggestion = (await session.execute(stmt)).scalar_one_or_none()
    if suggestion is None:
        raise ValueError(f"Suggestion not found: {suggestion_id}")
    if suggestion.suggestion_status != "PENDING":
        raise ValueError(f"Suggestion already {suggestion.suggestion_status}")

    now = datetime.now(UTC)
    suggestion.suggestion_status = "REJECTED"
    suggestion.reviewed_by = rejected_by
    suggestion.reviewed_at = now
    suggestion.review_note = review_note
    suggestion.updated_at = now
    await session.flush()

    await _log_audit_event(
        session,
        "network.suggestion.rejected",
        suggestion.id,
        detail=f"rejected_by={rejected_by} note={review_note[:100]}",
        actor_id=rejected_by,
    )
    return suggestion
