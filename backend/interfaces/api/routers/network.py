"""M38 Supplier Network Intelligence API Router.

Prefix: /api/v1/network

Scopes:
  network:read  — read relationships, exposures, clusters, dashboard
  network:write — create/remove relationships, approve/reject suggestions,
                  run discovery, resolve clusters

Tenant isolation: all reads and writes are scoped to current_user.organization_id.
Cross-tenant access returns 404.

Agents may NEVER approve relationships, resolve clusters, or take irreversible actions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.api.deps import get_current_user, get_db, require_admin, require_analyst
from interfaces.api.schemas.network import (
    CentralityRecord,
    CreateRelationshipRequest,
    DependencyAnalysisResponse,
    DiscoveryResult,
    IncidentClusterResponse,
    NeighborhoodResponse,
    NetworkDashboard,
    NetworkExposureSignalResponse,
    NetworkWatchlistEntryResponse,
    ResilienceAssessmentResponse,
    ReviewSuggestionRequest,
    ShortestPathResponse,
    SuggestedRelationshipResponse,
    SupplierCriticalityResponse,
    SupplierRelationshipResponse,
)

router = APIRouter(prefix="/network", tags=["Network Intelligence (M38)"])

_ANALYST = Depends(require_analyst)
_ADMIN = Depends(require_admin)


# ── Relationships ─────────────────────────────────────────────────────────────


@router.get(
    "/relationships",
    response_model=list[SupplierRelationshipResponse],
    dependencies=[_ANALYST],
)
async def list_relationships(
    supplier_id: str | None = None,
    relationship_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[SupplierRelationshipResponse]:
    from application.network.relationship_service import list_relationships

    rows = await list_relationships(
        organization_id=current_user.organization_id,
        supplier_id=supplier_id,
        relationship_type=relationship_type,
        limit=limit,
        session=session,
    )
    return [SupplierRelationshipResponse.model_validate(r) for r in rows]


@router.post(
    "/relationships",
    response_model=SupplierRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_relationship(
    body: CreateRelationshipRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SupplierRelationshipResponse:
    from application.network.relationship_service import create_relationship

    try:
        rel = await create_relationship(
            organization_id=current_user.organization_id,
            supplier_id=body.supplier_id,
            related_supplier_id=body.related_supplier_id,
            relationship_type=body.relationship_type,
            confidence=body.confidence,
            source="MANUAL",
            rationale=body.rationale,
            created_by=current_user.id,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SupplierRelationshipResponse.model_validate(rel)


@router.get(
    "/relationships/{relationship_id}",
    response_model=SupplierRelationshipResponse,
    dependencies=[_ANALYST],
)
async def get_relationship(
    relationship_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SupplierRelationshipResponse:
    from application.network.relationship_service import get_relationship

    rel = await get_relationship(relationship_id, current_user.organization_id, session)
    if rel is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return SupplierRelationshipResponse.model_validate(rel)


@router.delete(
    "/relationships/{relationship_id}",
    response_model=SupplierRelationshipResponse,
    dependencies=[_ANALYST],
)
async def remove_relationship(
    relationship_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SupplierRelationshipResponse:
    from application.network.relationship_service import remove_relationship

    try:
        rel = await remove_relationship(
            relationship_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return SupplierRelationshipResponse.model_validate(rel)


# ── Suggested Relationships ───────────────────────────────────────────────────


@router.get(
    "/suggested-relationships",
    response_model=list[SuggestedRelationshipResponse],
    dependencies=[_ANALYST],
)
async def list_suggested_relationships(
    suggestion_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[SuggestedRelationshipResponse]:
    from application.network.discovery_engine import list_suggestions

    rows = await list_suggestions(
        organization_id=current_user.organization_id,
        suggestion_status=suggestion_status,
        limit=limit,
        session=session,
    )
    return [SuggestedRelationshipResponse.model_validate(r) for r in rows]


@router.post(
    "/suggested-relationships/{suggestion_id}/approve",
    response_model=SuggestedRelationshipResponse,
    dependencies=[_ANALYST],
)
async def approve_suggestion(
    suggestion_id: str,
    body: ReviewSuggestionRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SuggestedRelationshipResponse:
    from application.network.discovery_engine import approve_suggestion

    try:
        suggestion = await approve_suggestion(
            suggestion_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SuggestedRelationshipResponse.model_validate(suggestion)


@router.post(
    "/suggested-relationships/{suggestion_id}/reject",
    response_model=SuggestedRelationshipResponse,
    dependencies=[_ANALYST],
)
async def reject_suggestion(
    suggestion_id: str,
    body: ReviewSuggestionRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SuggestedRelationshipResponse:
    from application.network.discovery_engine import reject_suggestion

    try:
        suggestion = await reject_suggestion(
            suggestion_id,
            current_user.organization_id,
            current_user.id,
            review_note=body.review_note,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SuggestedRelationshipResponse.model_validate(suggestion)


@router.post(
    "/discovery/run",
    response_model=DiscoveryResult,
    dependencies=[_ANALYST],
)
async def run_discovery(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DiscoveryResult:
    from application.network.discovery_engine import run_discovery

    result = await run_discovery(current_user.organization_id, session)
    await session.commit()
    return DiscoveryResult(**result)


# ── Exposure Signals ──────────────────────────────────────────────────────────


@router.get(
    "/exposure-signals",
    response_model=list[NetworkExposureSignalResponse],
    dependencies=[_ANALYST],
)
async def list_exposure_signals(
    impacted_supplier_id: str | None = None,
    origin_supplier_id: str | None = None,
    exposure_status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[NetworkExposureSignalResponse]:
    from application.network.risk_propagation import list_exposure_signals

    rows = await list_exposure_signals(
        organization_id=current_user.organization_id,
        impacted_supplier_id=impacted_supplier_id,
        origin_supplier_id=origin_supplier_id,
        exposure_status=exposure_status,
        limit=limit,
        session=session,
    )
    return [NetworkExposureSignalResponse.model_validate(r) for r in rows]


@router.post(
    "/cascade/detect",
    response_model=list[NetworkExposureSignalResponse],
    dependencies=[_ANALYST],
)
async def detect_cascade(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[NetworkExposureSignalResponse]:
    from application.network.cascading_risk import detect_cascading_risk

    signals = await detect_cascading_risk(current_user.organization_id, session)
    await session.commit()
    return [NetworkExposureSignalResponse.model_validate(s) for s in signals]


# ── Clusters ──────────────────────────────────────────────────────────────────


@router.get(
    "/clusters",
    response_model=list[IncidentClusterResponse],
    dependencies=[_ANALYST],
)
async def list_clusters(
    cluster_status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[IncidentClusterResponse]:
    from application.network.cluster_service import list_clusters

    rows = await list_clusters(
        organization_id=current_user.organization_id,
        cluster_status=cluster_status,
        limit=limit,
        session=session,
    )
    return [IncidentClusterResponse.model_validate(r) for r in rows]


@router.get(
    "/clusters/{cluster_id}",
    response_model=IncidentClusterResponse,
    dependencies=[_ANALYST],
)
async def get_cluster(
    cluster_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IncidentClusterResponse:
    from application.network.cluster_service import get_cluster

    cluster = await get_cluster(cluster_id, current_user.organization_id, session)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return IncidentClusterResponse.model_validate(cluster)


@router.post(
    "/clusters/{cluster_id}/resolve",
    response_model=IncidentClusterResponse,
    dependencies=[_ANALYST],
)
async def resolve_cluster(
    cluster_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> IncidentClusterResponse:
    from application.network.cluster_service import resolve_cluster

    try:
        cluster = await resolve_cluster(
            cluster_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return IncidentClusterResponse.model_validate(cluster)


@router.post(
    "/clusters/detect",
    response_model=list[IncidentClusterResponse],
    dependencies=[_ANALYST],
)
async def detect_clusters(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[IncidentClusterResponse]:
    from application.network.cascading_risk import cluster_incidents

    clusters = await cluster_incidents(current_user.organization_id, session)
    await session.commit()
    return [IncidentClusterResponse.model_validate(c) for c in clusters]


# ── Dependency Analysis ───────────────────────────────────────────────────────


@router.get(
    "/dependency-analysis",
    response_model=DependencyAnalysisResponse,
    dependencies=[_ANALYST],
)
async def get_org_dependency(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DependencyAnalysisResponse:
    from application.network.dependency_service import compute_dependency_analysis

    result = await compute_dependency_analysis(
        organization_id=current_user.organization_id,
        session=session,
    )
    await session.commit()
    return DependencyAnalysisResponse.model_validate(result)


@router.get(
    "/dependency-analysis/{supplier_id}",
    response_model=DependencyAnalysisResponse,
    dependencies=[_ANALYST],
)
async def get_supplier_dependency(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DependencyAnalysisResponse:
    from application.network.dependency_service import compute_dependency_analysis

    result = await compute_dependency_analysis(
        organization_id=current_user.organization_id,
        supplier_id=supplier_id,
        session=session,
    )
    await session.commit()
    return DependencyAnalysisResponse.model_validate(result)


# ── Resilience ────────────────────────────────────────────────────────────────


@router.get(
    "/resilience",
    response_model=ResilienceAssessmentResponse,
    dependencies=[_ANALYST],
)
async def get_org_resilience(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ResilienceAssessmentResponse:
    from application.network.resilience_service import compute_resilience

    result = await compute_resilience(
        organization_id=current_user.organization_id,
        session=session,
    )
    await session.commit()
    return ResilienceAssessmentResponse.model_validate(result)


@router.get(
    "/resilience/{supplier_id}",
    response_model=ResilienceAssessmentResponse,
    dependencies=[_ANALYST],
)
async def get_supplier_resilience(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ResilienceAssessmentResponse:
    from application.network.resilience_service import compute_resilience

    result = await compute_resilience(
        organization_id=current_user.organization_id,
        supplier_id=supplier_id,
        session=session,
    )
    await session.commit()
    return ResilienceAssessmentResponse.model_validate(result)


# ── Centrality ────────────────────────────────────────────────────────────────


@router.get(
    "/centrality",
    response_model=list[CentralityRecord],
    dependencies=[_ANALYST],
)
async def get_centrality(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[CentralityRecord]:
    from application.network.centrality_service import compute_centrality

    records = await compute_centrality(current_user.organization_id, session)
    return [CentralityRecord(**r) for r in records[:limit]]


@router.get(
    "/criticality",
    response_model=list[SupplierCriticalityResponse],
    dependencies=[_ANALYST],
)
async def list_criticality(
    criticality_level: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[SupplierCriticalityResponse]:
    from application.network.centrality_service import list_criticality

    rows = await list_criticality(
        organization_id=current_user.organization_id,
        criticality_level=criticality_level,
        limit=limit,
        session=session,
    )
    return [SupplierCriticalityResponse.model_validate(r) for r in rows]


@router.get(
    "/criticality/{supplier_id}",
    response_model=SupplierCriticalityResponse,
    dependencies=[_ANALYST],
)
async def get_supplier_criticality(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SupplierCriticalityResponse:
    from application.network.centrality_service import get_criticality

    record = await get_criticality(current_user.organization_id, supplier_id, session)
    if record is None:
        raise HTTPException(status_code=404, detail="Criticality record not found")
    return SupplierCriticalityResponse.model_validate(record)


# ── Graph Traversal ───────────────────────────────────────────────────────────


@router.get(
    "/suppliers/{supplier_id}/neighborhood",
    response_model=NeighborhoodResponse,
    dependencies=[_ANALYST],
)
async def get_neighborhood(
    supplier_id: str,
    max_depth: int = Query(2, ge=1, le=5),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> NeighborhoodResponse:
    from application.network.graph_service import bfs_neighborhood

    neighbors = await bfs_neighborhood(
        current_user.organization_id, supplier_id, max_depth=max_depth, session=session
    )
    return NeighborhoodResponse(supplier_id=supplier_id, neighbors=neighbors)


@router.get(
    "/suppliers/{src}/path/{dst}",
    response_model=ShortestPathResponse,
    dependencies=[_ANALYST],
)
async def get_shortest_path(
    src: str,
    dst: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ShortestPathResponse:
    from application.network.graph_service import shortest_path

    path = await shortest_path(current_user.organization_id, src, dst, session=session)
    return ShortestPathResponse(
        src=src,
        dst=dst,
        path=path,
        path_length=len(path) - 1 if path else None,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=NetworkDashboard,
    dependencies=[_ANALYST],
)
async def get_network_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> NetworkDashboard:
    from sqlalchemy import func, select

    from application.network.centrality_service import list_criticality
    from application.network.cluster_service import list_clusters
    from application.network.dependency_service import get_dependency_analysis
    from application.network.resilience_service import get_resilience
    from application.network.risk_propagation import list_exposure_signals
    from infrastructure.persistence.models.network import SupplierRelationshipModel

    org_id = current_user.organization_id

    from infrastructure.persistence.models.network import (
        IncidentClusterModel,
        SuggestedRelationshipModel,
    )
    from infrastructure.persistence.models.network import (
        NetworkExposureSignalModel as _NExpModel,
    )

    # Relationship count
    rel_stmt = (
        select(func.count())
        .select_from(SupplierRelationshipModel)
        .where(
            SupplierRelationshipModel.organization_id == org_id,
            SupplierRelationshipModel.relationship_status == "ACTIVE",
        )
    )
    total_rels = (await session.execute(rel_stmt)).scalar_one()

    # Pending suggestions count
    pend_stmt = (
        select(func.count())
        .select_from(SuggestedRelationshipModel)
        .where(
            SuggestedRelationshipModel.organization_id == org_id,
            SuggestedRelationshipModel.suggestion_status == "PENDING",
        )
    )
    pending_count = (await session.execute(pend_stmt)).scalar_one()

    # P0 M38.1 fix: true COUNT rather than len(limited list)
    exp_count_stmt = (
        select(func.count())
        .select_from(_NExpModel)
        .where(
            _NExpModel.organization_id == org_id,
            _NExpModel.exposure_status == "ACTIVE",
        )
    )
    active_exposure_count = (await session.execute(exp_count_stmt)).scalar_one()

    # Cluster count
    cluster_count_stmt = (
        select(func.count())
        .select_from(IncidentClusterModel)
        .where(
            IncidentClusterModel.organization_id == org_id,
            IncidentClusterModel.cluster_status == "ACTIVE",
        )
    )
    active_cluster_count = (await session.execute(cluster_count_stmt)).scalar_one()

    # Recent lists for detail cards
    exposures = await list_exposure_signals(
        org_id, exposure_status="ACTIVE", limit=10, session=session
    )
    clusters = await list_clusters(org_id, cluster_status="ACTIVE", limit=10, session=session)
    critical = await list_criticality(
        org_id, criticality_level="CRITICAL", limit=10, session=session
    )
    resilience = await get_resilience(org_id, session=session)
    dep = await get_dependency_analysis(org_id, session=session)

    return NetworkDashboard(
        total_relationships=total_rels,
        pending_suggestions=pending_count,
        active_exposures=active_exposure_count,
        active_clusters=active_cluster_count,
        critical_suppliers=len(critical),
        resilience_score=resilience.resilience_score if resilience else None,
        dependency_score=dep.dependency_score if dep else None,
        top_critical=[SupplierCriticalityResponse.model_validate(r) for r in critical],
        recent_exposures=[NetworkExposureSignalResponse.model_validate(e) for e in exposures],
        recent_clusters=[IncidentClusterResponse.model_validate(c) for c in clusters],
    )


# ── Network Watchlists (M38.1 / Spec Section 13) ─────────────────────────────


@router.get(
    "/watchlists",
    response_model=list[NetworkWatchlistEntryResponse],
    dependencies=[_ANALYST],
)
async def get_network_watchlists(
    watched_supplier_id: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[NetworkWatchlistEntryResponse]:
    from application.network.watchlist_service import get_network_watchlist

    entries = await get_network_watchlist(
        organization_id=current_user.organization_id,
        watched_supplier_id=watched_supplier_id,
        session=session,
    )
    return [NetworkWatchlistEntryResponse(**e) for e in entries]


@router.post(
    "/watchlists/{supplier_id}/expand",
    response_model=list[NetworkWatchlistEntryResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def expand_watchlist(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[NetworkWatchlistEntryResponse]:
    from application.network.watchlist_service import expand_watchlist_network

    entries = await expand_watchlist_network(
        organization_id=current_user.organization_id,
        watched_supplier_id=supplier_id,
        session=session,
    )
    await session.commit()
    return [
        NetworkWatchlistEntryResponse(
            id=e.id,
            organization_id=e.organization_id,
            watched_supplier_id=e.watched_supplier_id,
            related_supplier_id=e.related_supplier_id,
            distance=e.distance,
            has_active_alert=False,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in entries
    ]


@router.delete(
    "/watchlists/{supplier_id}/expand",
    response_model=dict,
    dependencies=[_ANALYST],
)
async def collapse_watchlist(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    from application.network.watchlist_service import remove_watchlist_network

    deleted = await remove_watchlist_network(
        organization_id=current_user.organization_id,
        watched_supplier_id=supplier_id,
        session=session,
    )
    await session.commit()
    return {"deleted": deleted}
