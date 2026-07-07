"""Intelligence Timeline Service — append-only event log for Supplier Twins."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.supplier_digital_twin import IntelligenceTimelineEvent


async def append_event(
    event: IntelligenceTimelineEvent,
    session: AsyncSession,
) -> IntelligenceTimelineEvent:
    """Append an intelligence event to the timeline (never mutated)."""

    model = _domain_to_model(event)
    session.add(model)
    await session.flush()
    return event


async def list_timeline(
    supplier_id: str,
    organization_id: str,
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    severity: str | None = None,
    category: str | None = None,
) -> list[IntelligenceTimelineEvent]:
    """Return timeline events for a supplier, newest first."""
    from infrastructure.persistence.models.supplier_digital_twin import (
        IntelligenceTimelineEventModel,
    )

    stmt = (
        select(IntelligenceTimelineEventModel)
        .where(
            IntelligenceTimelineEventModel.supplier_id == supplier_id,
            IntelligenceTimelineEventModel.organization_id == organization_id,
            IntelligenceTimelineEventModel.is_active.is_(True),
        )
        .order_by(IntelligenceTimelineEventModel.occurred_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if severity:
        stmt = stmt.where(IntelligenceTimelineEventModel.severity == severity.upper())
    if category:
        stmt = stmt.where(IntelligenceTimelineEventModel.event_category == category.upper())

    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


async def list_org_intelligence_feed(
    organization_id: str,
    session: AsyncSession,
    limit: int = 30,
    min_severity: str = "MEDIUM",
) -> list[IntelligenceTimelineEvent]:
    """Return the latest intelligence events across all suppliers in an org."""
    from infrastructure.persistence.models.supplier_digital_twin import (
        IntelligenceTimelineEventModel,
    )

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    min_idx = severity_order.get(min_severity.upper(), 2)
    allowed = [s for s, idx in severity_order.items() if idx <= min_idx]

    stmt = (
        select(IntelligenceTimelineEventModel)
        .where(
            IntelligenceTimelineEventModel.organization_id == organization_id,
            IntelligenceTimelineEventModel.is_active.is_(True),
            IntelligenceTimelineEventModel.severity.in_(allowed),
        )
        .order_by(IntelligenceTimelineEventModel.occurred_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


def _domain_to_model(e: IntelligenceTimelineEvent):
    from infrastructure.persistence.models.supplier_digital_twin import (
        IntelligenceTimelineEventModel,
    )

    return IntelligenceTimelineEventModel(
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
        event_type=e.event_type,
        event_category=e.event_category,
        severity=e.severity,
        title=e.title,
        summary=e.summary,
        why_important=e.why_important,
        regulatory_impact=e.regulatory_impact,
        recommended_action=e.recommended_action,
        source_type=e.source_type,
        source_name=e.source_name,
        source_url=e.source_url,
        evidence_ids=e.evidence_ids,
        regulation_ids=e.regulation_ids,
        risk_ids=e.risk_ids,
        signal_id=e.signal_id,
        twin_dimension_affected=e.twin_dimension_affected,
        health_delta=e.health_delta,
        confidence=e.confidence,
        occurred_at=e.occurred_at,
        processed_at=e.processed_at,
        is_active=e.is_active,
    )


def _model_to_domain(m) -> IntelligenceTimelineEvent:
    return IntelligenceTimelineEvent(
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
        event_type=m.event_type,
        event_category=m.event_category,
        severity=m.severity,
        title=m.title,
        summary=m.summary,
        why_important=m.why_important or "",
        regulatory_impact=m.regulatory_impact or "",
        recommended_action=m.recommended_action or "",
        source_type=m.source_type or "",
        source_name=m.source_name or "",
        source_url=m.source_url or "",
        evidence_ids=m.evidence_ids or "[]",
        regulation_ids=m.regulation_ids or "[]",
        risk_ids=m.risk_ids or "[]",
        signal_id=m.signal_id or "",
        twin_dimension_affected=m.twin_dimension_affected or "",
        health_delta=m.health_delta,
        confidence=m.confidence,
        occurred_at=m.occurred_at,
        processed_at=m.processed_at,
        is_active=bool(m.is_active),
    )
