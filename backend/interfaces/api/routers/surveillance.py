"""M37 Continuous ESG Risk Surveillance API Router.

Prefix: /api/v1/surveillance

Scopes:
  surveillance:read  — read signals, watchlists, episodes, trends, dashboard, heatmaps
  surveillance:write — acknowledge/dismiss signals, manage watchlist, manage episodes

All reads are scoped to current_user.organization_id.
Agents may NEVER approve findings, close episodes, or take irreversible actions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.api.deps import get_current_user, get_db, require_admin, require_analyst
from interfaces.api.schemas.surveillance import (
    AddWatchlistRequest,
    CreateEpisodeRequest,
    HeatmapCell,
    RiskEpisodeResponse,
    RiskTimelineEvent,
    RiskTrendResponse,
    SupplierWatchlistResponse,
    SurveillanceDashboard,
    SurveillanceSignalResponse,
    TransitionEpisodeRequest,
)

router = APIRouter(prefix="/surveillance", tags=["Surveillance (M37)"])

_ANALYST = Depends(require_analyst)
_ADMIN = Depends(require_admin)


# ── Signals ───────────────────────────────────────────────────────────────────


@router.get(
    "/signals",
    response_model=list[SurveillanceSignalResponse],
    dependencies=[_ANALYST],
)
async def list_signals(
    supplier_id: str | None = None,
    signal_type: str | None = None,
    severity: str | None = None,
    signal_status: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[SurveillanceSignalResponse]:
    from application.surveillance.signal_service import list_signals

    rows = await list_signals(
        organization_id=current_user.organization_id,
        supplier_id=supplier_id,
        signal_type=signal_type,
        severity=severity,
        signal_status=signal_status,
        limit=limit,
        offset=offset,
        session=session,
    )
    return [SurveillanceSignalResponse.model_validate(r) for r in rows]


@router.get(
    "/signals/{signal_id}",
    response_model=SurveillanceSignalResponse,
    dependencies=[_ANALYST],
)
async def get_signal(
    signal_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SurveillanceSignalResponse:
    from application.surveillance.signal_service import get_signal

    signal = await get_signal(signal_id, current_user.organization_id, session)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return SurveillanceSignalResponse.model_validate(signal)


@router.post(
    "/signals/{signal_id}/acknowledge",
    response_model=SurveillanceSignalResponse,
    dependencies=[_ANALYST],
)
async def acknowledge_signal(
    signal_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SurveillanceSignalResponse:
    from application.surveillance.signal_service import acknowledge_signal

    try:
        signal = await acknowledge_signal(
            signal_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SurveillanceSignalResponse.model_validate(signal)


@router.post(
    "/signals/{signal_id}/dismiss",
    response_model=SurveillanceSignalResponse,
    dependencies=[_ANALYST],
)
async def dismiss_signal(
    signal_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SurveillanceSignalResponse:
    from application.surveillance.signal_service import dismiss_signal

    try:
        signal = await dismiss_signal(
            signal_id, current_user.organization_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SurveillanceSignalResponse.model_validate(signal)


# ── Watchlists ────────────────────────────────────────────────────────────────


@router.get(
    "/watchlists",
    response_model=list[SupplierWatchlistResponse],
    dependencies=[_ANALYST],
)
async def list_watchlist(
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[SupplierWatchlistResponse]:
    from application.surveillance.watchlist_service import list_watchlist

    rows = await list_watchlist(
        current_user.organization_id,
        active_only=active_only,
        limit=limit,
        session=session,
    )
    return [SupplierWatchlistResponse.model_validate(r) for r in rows]


@router.post(
    "/watchlists",
    response_model=SupplierWatchlistResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def add_to_watchlist(
    body: AddWatchlistRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SupplierWatchlistResponse:
    from application.surveillance.watchlist_service import add_to_watchlist

    entry = await add_to_watchlist(
        organization_id=current_user.organization_id,
        supplier_id=body.supplier_id,
        watch_reason=body.watch_reason,
        severity=body.severity,
        added_by_type="MANUAL",
        created_by=current_user.id,
        session=session,
    )
    await session.commit()
    return SupplierWatchlistResponse.model_validate(entry)


@router.delete(
    "/watchlists/{supplier_id}",
    response_model=SupplierWatchlistResponse,
    dependencies=[_ANALYST],
)
async def remove_from_watchlist(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SupplierWatchlistResponse:
    from application.surveillance.watchlist_service import remove_from_watchlist

    try:
        entry = await remove_from_watchlist(
            current_user.organization_id, supplier_id, current_user.id, session
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return SupplierWatchlistResponse.model_validate(entry)


# ── Risk Episodes ─────────────────────────────────────────────────────────────


@router.get(
    "/episodes",
    response_model=list[RiskEpisodeResponse],
    dependencies=[_ANALYST],
)
async def list_episodes(
    supplier_id: str | None = None,
    episode_status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[RiskEpisodeResponse]:
    from application.surveillance.episode_service import list_episodes

    rows = await list_episodes(
        current_user.organization_id,
        supplier_id=supplier_id,
        episode_status=episode_status,
        limit=limit,
        session=session,
    )
    return [RiskEpisodeResponse.model_validate(r) for r in rows]


@router.get(
    "/episodes/{episode_id}",
    response_model=RiskEpisodeResponse,
    dependencies=[_ANALYST],
)
async def get_episode(
    episode_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RiskEpisodeResponse:
    from application.surveillance.episode_service import get_episode

    episode = await get_episode(episode_id, current_user.organization_id, session)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return RiskEpisodeResponse.model_validate(episode)


@router.post(
    "/episodes",
    response_model=RiskEpisodeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_episode(
    body: CreateEpisodeRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RiskEpisodeResponse:
    from application.surveillance.episode_service import create_episode

    episode = await create_episode(
        organization_id=current_user.organization_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        supplier_id=body.supplier_id,
        created_by=current_user.id,
        session=session,
    )
    await session.commit()
    return RiskEpisodeResponse.model_validate(episode)


@router.post(
    "/episodes/{episode_id}/transition",
    response_model=RiskEpisodeResponse,
    dependencies=[_ANALYST],
)
async def transition_episode(
    episode_id: str,
    body: TransitionEpisodeRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RiskEpisodeResponse:
    from application.surveillance.episode_service import transition_episode

    try:
        episode = await transition_episode(
            episode_id,
            current_user.organization_id,
            body.new_status,
            current_user.id,
            session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RiskEpisodeResponse.model_validate(episode)


# ── Risk Trends ───────────────────────────────────────────────────────────────


@router.get(
    "/trends",
    response_model=list[RiskTrendResponse],
    dependencies=[_ANALYST],
)
async def list_trends(
    supplier_id: str | None = None,
    limit: int = Query(24, ge=1, le=120),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[RiskTrendResponse]:
    from sqlalchemy import select

    from infrastructure.persistence.models.surveillance import RiskTrendModel

    stmt = select(RiskTrendModel).where(
        RiskTrendModel.organization_id == current_user.organization_id
    )
    if supplier_id:
        stmt = stmt.where(RiskTrendModel.supplier_id == supplier_id)
    stmt = stmt.order_by(RiskTrendModel.period.desc()).limit(limit)
    rows = list((await session.execute(stmt)).scalars().all())
    return [RiskTrendResponse.model_validate(r) for r in rows]


# ── Risk Timeline ─────────────────────────────────────────────────────────────


@router.get(
    "/suppliers/{supplier_id}/timeline",
    response_model=list[RiskTimelineEvent],
    dependencies=[_ANALYST],
)
async def supplier_risk_timeline(
    supplier_id: str,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[RiskTimelineEvent]:
    from application.surveillance.portfolio_monitor import compute_supplier_risk_timeline

    events = await compute_supplier_risk_timeline(
        supplier_id, current_user.organization_id, session, limit=limit
    )
    return [RiskTimelineEvent(**e) for e in events]


# ── Heatmaps ──────────────────────────────────────────────────────────────────


@router.get(
    "/heatmaps/{dimension}",
    response_model=list[HeatmapCell],
    dependencies=[_ANALYST],
)
async def get_heatmap(
    dimension: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[HeatmapCell]:
    from application.surveillance.portfolio_monitor import compute_heatmap

    try:
        cells = await compute_heatmap(current_user.organization_id, dimension, session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return [HeatmapCell(**c) for c in cells]


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=SurveillanceDashboard,
    dependencies=[_ANALYST],
)
async def get_surveillance_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SurveillanceDashboard:
    from application.surveillance.episode_service import list_episodes
    from application.surveillance.portfolio_monitor import compute_portfolio_stats
    from application.surveillance.signal_service import list_signals
    from application.surveillance.watchlist_service import list_watchlist

    org_id = current_user.organization_id

    stats = await compute_portfolio_stats(org_id, session)
    recent_signals = await list_signals(org_id, signal_status="ACTIVE", limit=10, session=session)
    recent_episodes = await list_episodes(org_id, episode_status="OPEN", limit=10, session=session)
    watchlist = await list_watchlist(org_id, active_only=True, limit=20, session=session)

    return SurveillanceDashboard(
        **stats,
        recent_signals=[SurveillanceSignalResponse.model_validate(s) for s in recent_signals],
        recent_episodes=[RiskEpisodeResponse.model_validate(e) for e in recent_episodes],
        watchlist=[SupplierWatchlistResponse.model_validate(w) for w in watchlist],
    )
