"""M50 Supplier Digital Twin API Router.

Endpoints:
  GET  /suppliers/{id}/twin             — current twin state
  GET  /suppliers/{id}/twin/timeline    — intelligence timeline
  POST /suppliers/{id}/twin/process     — trigger pipeline for unprocessed signals
  GET  /intelligence/feed               — org-level intelligence feed (all suppliers)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.intelligence_engine.collector_orchestrator import run_collection_for_org
from application.intelligence_engine.pipeline_service import process_signals_for_supplier
from application.intelligence_engine.source_credibility import get_credibility
from application.intelligence_engine.timeline_service import (
    list_org_intelligence_feed,
    list_timeline,
)
from application.intelligence_engine.twin_service import get_or_create_twin
from domain.user import User
from interfaces.api.deps import get_current_user, get_db
from interfaces.api.schemas.supplier_twin import (
    CollectIntelligenceResponse,
    HealthDimensionResponse,
    IntelligenceFeedResponse,
    IntelligenceTimelineEventResponse,
    ProcessSignalsResponse,
    SupplierDigitalTwinResponse,
    TimelineListResponse,
)

router = APIRouter(tags=["Supplier Digital Twin"])


def _twin_to_response(twin) -> SupplierDigitalTwinResponse:
    dimensions = [
        HealthDimensionResponse(
            name="esg_health",
            label="ESG",
            score=twin.esg_health,
            status=_health_status(twin.esg_health),
        ),
        HealthDimensionResponse(
            name="compliance_health",
            label="Compliance",
            score=twin.compliance_health,
            status=_health_status(twin.compliance_health),
        ),
        HealthDimensionResponse(
            name="financial_health",
            label="Financial",
            score=twin.financial_health,
            status=_health_status(twin.financial_health),
        ),
        HealthDimensionResponse(
            name="geopolitical_health",
            label="Geopolitical",
            score=twin.geopolitical_health,
            status=_health_status(twin.geopolitical_health),
        ),
        HealthDimensionResponse(
            name="cyber_health",
            label="Cyber",
            score=twin.cyber_health,
            status=_health_status(twin.cyber_health),
        ),
        HealthDimensionResponse(
            name="human_rights_health",
            label="Human Rights",
            score=twin.human_rights_health,
            status=_health_status(twin.human_rights_health),
        ),
        HealthDimensionResponse(
            name="environmental_health",
            label="Environmental",
            score=twin.environmental_health,
            status=_health_status(twin.environmental_health),
        ),
        HealthDimensionResponse(
            name="operational_health",
            label="Operational",
            score=twin.operational_health,
            status=_health_status(twin.operational_health),
        ),
    ]
    return SupplierDigitalTwinResponse(
        id=twin.id,
        supplier_id=twin.supplier_id,
        organization_id=twin.organization_id,
        esg_health=twin.esg_health,
        compliance_health=twin.compliance_health,
        financial_health=twin.financial_health,
        geopolitical_health=twin.geopolitical_health,
        cyber_health=twin.cyber_health,
        human_rights_health=twin.human_rights_health,
        environmental_health=twin.environmental_health,
        operational_health=twin.operational_health,
        overall_health=twin.overall_health,
        health_trend=twin.health_trend,
        ai_confidence=twin.ai_confidence,
        open_recommendations=twin.open_recommendations,
        open_actions=twin.open_actions,
        event_count=twin.event_count,
        critical_event_count=twin.critical_event_count,
        last_event_at=twin.last_event_at,
        last_updated_at=twin.last_updated_at,
        twin_version=twin.twin_version,
        dimensions=dimensions,
    )


def _event_to_response(e) -> IntelligenceTimelineEventResponse:
    credibility = get_credibility(e.source_name)
    return IntelligenceTimelineEventResponse(
        id=e.id,
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
        credibility_level=credibility.level,
        credibility_reason=credibility.reason,
        occurred_at=e.occurred_at,
        processed_at=e.processed_at,
        is_active=e.is_active,
    )


def _health_status(score: float) -> str:
    if score < 40:
        return "CRITICAL"
    if score < 60:
        return "AT_RISK"
    if score < 75:
        return "MODERATE"
    return "HEALTHY"


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/suppliers/{supplier_id}/twin",
    response_model=SupplierDigitalTwinResponse,
)
async def get_supplier_twin(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupplierDigitalTwinResponse:
    twin = await get_or_create_twin(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        session=session,
    )
    await session.commit()
    return _twin_to_response(twin)


@router.get(
    "/suppliers/{supplier_id}/twin/timeline",
    response_model=TimelineListResponse,
)
async def get_supplier_twin_timeline(
    supplier_id: str,
    limit: int = 50,
    offset: int = 0,
    severity: str | None = None,
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TimelineListResponse:
    events = await list_timeline(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        session=session,
        limit=limit,
        offset=offset,
        severity=severity,
        category=category,
    )
    return TimelineListResponse(
        events=[_event_to_response(e) for e in events],
        total=len(events),
        supplier_id=supplier_id,
    )


@router.post(
    "/suppliers/{supplier_id}/twin/process",
    response_model=ProcessSignalsResponse,
    status_code=status.HTTP_200_OK,
)
async def process_supplier_signals(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProcessSignalsResponse:
    """Trigger the intelligence pipeline for all unprocessed signals of a supplier."""
    events = await process_signals_for_supplier(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        session=session,
    )
    await session.commit()
    return ProcessSignalsResponse(
        supplier_id=supplier_id,
        events_created=len(events),
        twin_updated=len(events) > 0,
        message=f"Processed {len(events)} new signal(s) into the intelligence timeline.",
    )


@router.post(
    "/intelligence/collect",
    response_model=CollectIntelligenceResponse,
    status_code=status.HTTP_200_OK,
)
async def collect_intelligence(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CollectIntelligenceResponse:
    """Fetch external intelligence from all live sources (EU sanctions, OFAC, World Bank,
    UN Security Council sanctions, GDELT news), match against org suppliers, update Digital Twins."""
    summary = await run_collection_for_org(
        org_id=current_user.organization_id,
        session=session,
    )
    await session.commit()
    return CollectIntelligenceResponse(
        sources_attempted=summary.sources_attempted,
        sources_ok=summary.sources_ok,
        entities_checked=summary.entities_checked,
        suppliers_matched=summary.suppliers_matched,
        signals_created=summary.signals_created,
        twins_updated=summary.twins_updated,
        events_created=summary.events_created,
        duration_seconds=summary.duration_seconds(),
        errors=summary.errors,
        message=(
            f"Collection complete: {summary.signals_created} new signals, "
            f"{summary.twins_updated} twins updated, {summary.events_created} events created."
            if not summary.errors
            else f"Partial: {summary.signals_created} signals, errors: {'; '.join(summary.errors[:2])}"
        ),
    )


@router.post(
    "/intelligence/collect/batch",
    response_model=CollectIntelligenceResponse,
    status_code=status.HTTP_200_OK,
)
async def collect_intelligence_batch(
    supplier_ids: list[str],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CollectIntelligenceResponse:
    """Fetch external intelligence for a specific list of suppliers."""
    from application.intelligence_engine.collector_orchestrator import CollectionSummary
    from datetime import UTC, datetime

    combined = CollectionSummary(org_id=current_user.organization_id, started_at=datetime.now(UTC))
    for sid in supplier_ids:
        s = await run_collection_for_org(
            org_id=current_user.organization_id,
            session=session,
            supplier_id=sid,
        )
        combined.sources_attempted = max(combined.sources_attempted, s.sources_attempted)
        combined.sources_ok = max(combined.sources_ok, s.sources_ok)
        combined.entities_checked += s.entities_checked
        combined.suppliers_matched += s.suppliers_matched
        combined.signals_created += s.signals_created
        combined.twins_updated += s.twins_updated
        combined.events_created += s.events_created
        combined.errors.extend(s.errors)

    await session.commit()
    combined.completed_at = datetime.now(UTC)
    return CollectIntelligenceResponse(
        sources_attempted=combined.sources_attempted,
        sources_ok=combined.sources_ok,
        entities_checked=combined.entities_checked,
        suppliers_matched=combined.suppliers_matched,
        signals_created=combined.signals_created,
        twins_updated=combined.twins_updated,
        events_created=combined.events_created,
        duration_seconds=combined.duration_seconds(),
        errors=combined.errors,
        message=(
            f"Collection complete: {combined.signals_created} new signals, "
            f"{combined.twins_updated} twins updated, {combined.events_created} events created."
            if not combined.errors
            else f"Partial: {combined.signals_created} signals, errors: {'; '.join(combined.errors[:2])}"
        ),
    )


@router.post(
    "/suppliers/{supplier_id}/intelligence/collect",
    response_model=CollectIntelligenceResponse,
    status_code=status.HTTP_200_OK,
)
async def collect_intelligence_for_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CollectIntelligenceResponse:
    """Fetch external intelligence for a single supplier only."""
    summary = await run_collection_for_org(
        org_id=current_user.organization_id,
        session=session,
        supplier_id=supplier_id,
    )
    await session.commit()
    return CollectIntelligenceResponse(
        sources_attempted=summary.sources_attempted,
        sources_ok=summary.sources_ok,
        entities_checked=summary.entities_checked,
        suppliers_matched=summary.suppliers_matched,
        signals_created=summary.signals_created,
        twins_updated=summary.twins_updated,
        events_created=summary.events_created,
        duration_seconds=summary.duration_seconds(),
        errors=summary.errors,
        message=(
            f"Collection complete: {summary.signals_created} new signals, "
            f"{summary.twins_updated} twins updated, {summary.events_created} events created."
            if not summary.errors
            else f"Partial: {summary.signals_created} signals, errors: {'; '.join(summary.errors[:2])}"
        ),
    )


@router.get(
    "/intelligence/feed",
    response_model=IntelligenceFeedResponse,
)
async def get_intelligence_feed(
    limit: int = 30,
    min_severity: str = "MEDIUM",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IntelligenceFeedResponse:
    """Organisation-level intelligence feed: latest events across all suppliers."""
    events = await list_org_intelligence_feed(
        organization_id=current_user.organization_id,
        session=session,
        limit=limit,
        min_severity=min_severity,
    )
    return IntelligenceFeedResponse(
        events=[_event_to_response(e) for e in events],
        total=len(events),
        organization_id=current_user.organization_id,
    )
