"""M42 — Sustainability Performance Management & Decarbonization Platform Router.

All endpoints require JWT authentication via Bearer token.
All governance actions are attributed to the authenticated user (actor_id from JWT sub).
"""

from __future__ import annotations

import jwt as _jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.sustainability import (
    carbon_service,
    climate_service,
    kpi_service,
    objective_service,
    reporting_service,
    roadmap_service,
    rollup_service,
    scoring_service,
)
from application.sustainability.objective_service import (
    SustainabilityConflict,
    SustainabilityError,
)
from interfaces.api.deps import get_db
from interfaces.api.schemas.sustainability import (
    AssuranceRecordCreate,
    AssuranceRecordResponse,
    CarbonInventoryCreate,
    CarbonInventoryResponse,
    ClimateRiskAssessmentCreate,
    ClimateRiskAssessmentResponse,
    CSRDMappingCreate,
    CSRDMappingResponse,
    DecarbonizationInitiativeCreate,
    DecarbonizationInitiativeResponse,
    EmissionSourceCreate,
    EmissionSourceResponse,
    ESGKPICreate,
    ESGKPIResponse,
    ESGObjectiveCreate,
    ESGObjectiveResponse,
    ESGObjectiveStatusUpdate,
    ESGTargetCreate,
    ESGTargetResponse,
    ESGTargetValueUpdate,
    ForecastCreate,
    ForecastResponse,
    InitiativeProgressUpdate,
    ISSBMappingCreate,
    ISSBMappingResponse,
    KPIAlertCreate,
    KPIAlertResponse,
    KPIMeasurementCreate,
    KPIMeasurementResponse,
    MilestoneCreate,
    MilestoneUpdate,
    NetZeroMilestoneResponse,
    NetZeroRoadmapCreate,
    NetZeroRoadmapResponse,
    RollupSummaryResponse,
    SBTStatusUpdate,
    ScenarioCreate,
    ScenarioResponse,
    ScienceBasedTargetCreate,
    ScienceBasedTargetResponse,
    ScorecardComputeRequest,
    SustainabilityDashboard,
    SustainabilityReportCreate,
    SustainabilityReportResponse,
    SustainabilityScorecardResponse,
)
from shared.security import decode_token

router = APIRouter(prefix="/sustainability", tags=["sustainability"])


def _require_actor(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth[7:]
    try:
        payload = decode_token(token)
    except _jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail="Token expired", headers={"WWW-Authenticate": "Bearer"}
        )
    except _jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"}
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401, detail="Invalid token type", headers={"WWW-Authenticate": "Bearer"}
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=401, detail="Token missing subject", headers={"WWW-Authenticate": "Bearer"}
        )
    return sub


def _err(exc: SustainabilityError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _conflict(exc: SustainabilityConflict) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/{organization_id}/dashboard", response_model=SustainabilityDashboard)
async def get_dashboard(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    def _query(s):
        from infrastructure.persistence.models.sustainability import (
            CarbonInventoryModel,
            DecarbonizationInitiativeModel,
            ESGKPIModel,
            KPIAlertModel,
            ScienceBasedTargetModel,
            SustainabilityObjectiveModel,
            SustainabilityScorecardModel,
        )

        total_obj = (
            s.query(SustainabilityObjectiveModel)
            .filter(SustainabilityObjectiveModel.organization_id == organization_id)
            .count()
        )
        active_obj = (
            s.query(SustainabilityObjectiveModel)
            .filter(
                SustainabilityObjectiveModel.organization_id == organization_id,
                SustainabilityObjectiveModel.objective_status == "ACTIVE",
            )
            .count()
        )
        completed_obj = (
            s.query(SustainabilityObjectiveModel)
            .filter(
                SustainabilityObjectiveModel.organization_id == organization_id,
                SustainabilityObjectiveModel.objective_status == "COMPLETED",
            )
            .count()
        )
        total_kpis = (
            s.query(ESGKPIModel).filter(ESGKPIModel.organization_id == organization_id).count()
        )
        active_kpis = (
            s.query(ESGKPIModel)
            .filter(ESGKPIModel.organization_id == organization_id, ESGKPIModel.is_active)
            .count()
        )
        open_alerts = (
            s.query(KPIAlertModel)
            .filter(KPIAlertModel.organization_id == organization_id, not KPIAlertModel.is_resolved)
            .count()
        )
        active_init = (
            s.query(DecarbonizationInitiativeModel)
            .filter(
                DecarbonizationInitiativeModel.organization_id == organization_id,
                DecarbonizationInitiativeModel.initiative_status == "IN_PROGRESS",
            )
            .count()
        )
        latest_inv = (
            s.query(CarbonInventoryModel)
            .filter(
                CarbonInventoryModel.organization_id == organization_id,
                CarbonInventoryModel.inventory_status == "FINALIZED",
            )
            .order_by(CarbonInventoryModel.reporting_year.desc())
            .first()
        )
        latest_sc = (
            s.query(SustainabilityScorecardModel)
            .filter(SustainabilityScorecardModel.organization_id == organization_id)
            .order_by(SustainabilityScorecardModel.period_end.desc())
            .first()
        )
        active_sbts = (
            s.query(ScienceBasedTargetModel)
            .filter(
                ScienceBasedTargetModel.organization_id == organization_id,
                ScienceBasedTargetModel.sbt_status == "ACTIVE",
            )
            .count()
        )
        return (
            total_obj,
            active_obj,
            completed_obj,
            total_kpis,
            active_kpis,
            open_alerts,
            active_init,
            latest_inv,
            latest_sc,
            active_sbts,
        )

    (
        total_obj,
        active_obj,
        completed_obj,
        total_kpis,
        active_kpis,
        open_alerts,
        active_init,
        latest_inv,
        latest_sc,
        active_sbts,
    ) = await db.run_sync(_query)

    return SustainabilityDashboard(
        organization_id=organization_id,
        total_objectives=total_obj,
        active_objectives=active_obj,
        completed_objectives=completed_obj,
        total_kpis=total_kpis,
        active_kpis=active_kpis,
        total_emissions_tco2e=latest_inv.total_emissions if latest_inv else None,
        latest_inventory_year=latest_inv.reporting_year if latest_inv else None,
        open_alerts=open_alerts,
        active_initiatives=active_init,
        latest_overall_score=latest_sc.overall_score if latest_sc else None,
        active_sbts=active_sbts,
    )


# ── ESG Objectives ─────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/objectives",
    response_model=ESGObjectiveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_objective(
    organization_id: str,
    body: ESGObjectiveCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        obj = await db.run_sync(
            lambda s: objective_service.create_objective(
                organization_id=organization_id,
                title=body.title,
                category=body.category,
                actor_id=actor_id,
                session=s,
                description=body.description,
                owner_user_id=body.owner_user_id,
                start_date=body.start_date,
                target_date=body.target_date,
                program_id=body.program_id,
            )
        )
        await db.refresh(obj)
    except SustainabilityError as exc:
        raise _err(exc)
    return obj


@router.get("/{organization_id}/objectives", response_model=list[ESGObjectiveResponse])
async def list_objectives(
    organization_id: str,
    category: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: objective_service.list_objectives(
            organization_id,
            s,
            category=category,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    )


@router.patch(
    "/{organization_id}/objectives/{objective_id}/status",
    response_model=ESGObjectiveResponse,
)
async def update_objective_status(
    organization_id: str,
    objective_id: str,
    body: ESGObjectiveStatusUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        obj = await db.run_sync(
            lambda s: objective_service.update_objective_status(
                objective_id, body.status, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(obj)
    except SustainabilityError as exc:
        raise _err(exc)
    return obj


# ── ESG Targets ───────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/objectives/{objective_id}/targets",
    response_model=ESGTargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_target(
    organization_id: str,
    objective_id: str,
    body: ESGTargetCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        t = await db.run_sync(
            lambda s: objective_service.create_target(
                organization_id=organization_id,
                objective_id=objective_id,
                metric_name=body.metric_name,
                baseline_value=body.baseline_value,
                target_value=body.target_value,
                actor_id=actor_id,
                session=s,
                target_unit=body.target_unit,
                measurement_frequency=body.measurement_frequency,
                target_date=body.target_date,
                notes=body.notes,
            )
        )
        await db.refresh(t)
    except SustainabilityError as exc:
        raise _err(exc)
    resp = ESGTargetResponse.model_validate(t)
    resp.progress_percent = objective_service.compute_progress(
        t.baseline_value, t.target_value, t.current_value
    )
    return resp


@router.get(
    "/{organization_id}/objectives/{objective_id}/targets",
    response_model=list[ESGTargetResponse],
)
async def list_targets(
    organization_id: str,
    objective_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    pairs = await db.run_sync(
        lambda s: objective_service.list_targets(objective_id, s, limit=limit, offset=offset)
    )
    result = []
    for t, progress in pairs:
        r = ESGTargetResponse.model_validate(t)
        r.progress_percent = progress
        result.append(r)
    return result


@router.get("/{organization_id}/targets", response_model=list[ESGTargetResponse])
async def list_all_targets(
    organization_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    pairs = await db.run_sync(
        lambda s: objective_service.list_all_targets(organization_id, s, limit=limit, offset=offset)
    )
    result = []
    for t, progress in pairs:
        r = ESGTargetResponse.model_validate(t)
        r.progress_percent = progress
        result.append(r)
    return result


@router.patch(
    "/{organization_id}/targets/{target_id}/value",
    response_model=ESGTargetResponse,
)
async def update_target_value(
    organization_id: str,
    target_id: str,
    body: ESGTargetValueUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        t, progress = await db.run_sync(
            lambda s: objective_service.update_target_value(
                target_id, body.current_value, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(t)
    except SustainabilityError as exc:
        raise _err(exc)
    resp = ESGTargetResponse.model_validate(t)
    resp.progress_percent = progress
    return resp


# ── KPIs ──────────────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/kpis",
    response_model=ESGKPIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_kpi(
    organization_id: str,
    body: ESGKPICreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        kpi = await db.run_sync(
            lambda s: kpi_service.create_kpi(
                organization_id=organization_id,
                name=body.name,
                category=body.category,
                actor_id=actor_id,
                session=s,
                description=body.description,
                formula=body.formula,
                unit=body.unit,
                frequency=body.frequency,
                target_value=body.target_value,
                alert_threshold=body.alert_threshold,
            )
        )
        await db.refresh(kpi)
    except SustainabilityError as exc:
        raise _err(exc)
    return kpi


@router.get("/{organization_id}/kpis", response_model=list[ESGKPIResponse])
async def list_kpis(
    organization_id: str,
    category: str | None = None,
    active_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: kpi_service.list_kpis(
            organization_id,
            s,
            category=category,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )
    )


@router.post(
    "/{organization_id}/kpis/{kpi_id}/measurements",
    response_model=KPIMeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_measurement(
    organization_id: str,
    kpi_id: str,
    body: KPIMeasurementCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        m = await db.run_sync(
            lambda s: kpi_service.record_measurement(
                kpi_id=kpi_id,
                organization_id=organization_id,
                period_start=body.period_start,
                period_end=body.period_end,
                measured_value=body.measured_value,
                actor_id=actor_id,
                session=s,
                source=body.source,
                confidence=body.confidence,
                notes=body.notes,
            )
        )
        await db.refresh(m)
    except SustainabilityError as exc:
        raise _err(exc)
    return m


@router.get(
    "/{organization_id}/kpis/{kpi_id}/measurements",
    response_model=list[KPIMeasurementResponse],
)
async def list_measurements(
    organization_id: str,
    kpi_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: kpi_service.list_measurements(kpi_id, s, limit=limit, offset=offset)
    )


@router.post(
    "/{organization_id}/kpis/{kpi_id}/alerts",
    response_model=KPIAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_alert(
    organization_id: str,
    kpi_id: str,
    body: KPIAlertCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        alert = await db.run_sync(
            lambda s: kpi_service.create_kpi_alert(
                kpi_id=kpi_id,
                organization_id=organization_id,
                alert_type=body.alert_type,
                triggered_value=body.triggered_value,
                actor_id=actor_id,
                session=s,
                threshold_value=body.threshold_value,
                message=body.message,
            )
        )
        await db.refresh(alert)
    except SustainabilityError as exc:
        raise _err(exc)
    return alert


@router.get("/{organization_id}/alerts", response_model=list[KPIAlertResponse])
async def list_alerts(
    organization_id: str,
    kpi_id: str | None = None,
    unresolved_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: kpi_service.list_alerts(
            organization_id,
            s,
            kpi_id=kpi_id,
            unresolved_only=unresolved_only,
            limit=limit,
            offset=offset,
        )
    )


@router.post("/{organization_id}/alerts/{alert_id}/resolve", response_model=KPIAlertResponse)
async def resolve_alert(
    organization_id: str,
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        alert = await db.run_sync(
            lambda s: kpi_service.resolve_alert(
                alert_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(alert)
    except SustainabilityError as exc:
        raise _err(exc)
    return alert


# ── Scorecards ────────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/scorecards",
    response_model=SustainabilityScorecardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def compute_scorecard(
    organization_id: str,
    body: ScorecardComputeRequest,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    sc = await db.run_sync(
        lambda s: scoring_service.compute_scorecard(
            organization_id, body.period_start, body.period_end, actor_id, s
        )
    )
    await db.refresh(sc)
    return sc


@router.get(
    "/{organization_id}/scorecards",
    response_model=list[SustainabilityScorecardResponse],
)
async def list_scorecards(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: scoring_service.list_scorecards(organization_id, s, limit=limit, offset=offset)
    )


# ── Emission Sources ──────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/emissions",
    response_model=EmissionSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_emission_source(
    organization_id: str,
    body: EmissionSourceCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        src = await db.run_sync(
            lambda s: carbon_service.add_emission_source(
                organization_id=organization_id,
                name=body.name,
                scope=body.scope,
                activity_data=body.activity_data,
                emission_factor=body.emission_factor,
                period_start=body.period_start,
                period_end=body.period_end,
                reporting_year=body.reporting_year,
                actor_id=actor_id,
                session=s,
                category=body.category,
                activity_unit=body.activity_unit,
                emission_factor_unit=body.emission_factor_unit,
                source_reference=body.source_reference,
                inventory_id=body.inventory_id,
            )
        )
        await db.refresh(src)
    except SustainabilityError as exc:
        raise _err(exc)
    return src


@router.get("/{organization_id}/emissions", response_model=list[EmissionSourceResponse])
async def list_emission_sources(
    organization_id: str,
    reporting_year: int | None = None,
    scope: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: carbon_service.list_emission_sources(
            organization_id,
            s,
            reporting_year=reporting_year,
            scope=scope,
            limit=limit,
            offset=offset,
        )
    )


# ── Carbon Inventory ──────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/inventory",
    response_model=CarbonInventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inventory(
    organization_id: str,
    body: CarbonInventoryCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    inv = await db.run_sync(
        lambda s: carbon_service.create_or_get_inventory(
            organization_id, body.reporting_year, body.period_start, body.period_end, actor_id, s
        )
    )
    await db.refresh(inv)
    return inv


@router.get("/{organization_id}/inventory", response_model=list[CarbonInventoryResponse])
async def list_inventories(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: carbon_service.list_inventories(organization_id, s, limit=limit, offset=offset)
    )


@router.post(
    "/{organization_id}/inventory/{inventory_id}/recalculate",
    response_model=CarbonInventoryResponse,
)
async def recalculate_inventory(
    organization_id: str,
    inventory_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        inv = await db.run_sync(
            lambda s: carbon_service.recalculate_inventory(
                inventory_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(inv)
    except SustainabilityConflict as exc:
        raise _conflict(exc)
    except SustainabilityError as exc:
        raise _err(exc)
    return inv


@router.post(
    "/{organization_id}/inventory/{inventory_id}/finalize",
    response_model=CarbonInventoryResponse,
)
async def finalize_inventory(
    organization_id: str,
    inventory_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        inv = await db.run_sync(
            lambda s: carbon_service.finalize_inventory(
                inventory_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(inv)
    except SustainabilityConflict as exc:
        raise _conflict(exc)
    except SustainabilityError as exc:
        raise _err(exc)
    return inv


# ── Decarbonization Initiatives ───────────────────────────────────────────────


@router.post(
    "/{organization_id}/initiatives",
    response_model=DecarbonizationInitiativeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_initiative(
    organization_id: str,
    body: DecarbonizationInitiativeCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        init = await db.run_sync(
            lambda s: roadmap_service.create_initiative(
                organization_id=organization_id,
                name=body.name,
                initiative_type=body.initiative_type,
                expected_reduction=body.expected_reduction,
                actor_id=actor_id,
                session=s,
                description=body.description,
                roadmap_id=body.roadmap_id,
                cost_estimate=body.cost_estimate,
                start_date=body.start_date,
                end_date=body.end_date,
                notes=body.notes,
            )
        )
        await db.refresh(init)
    except SustainabilityError as exc:
        raise _err(exc)
    return init


@router.get(
    "/{organization_id}/initiatives",
    response_model=list[DecarbonizationInitiativeResponse],
)
async def list_initiatives(
    organization_id: str,
    roadmap_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: roadmap_service.list_initiatives(
            organization_id,
            s,
            roadmap_id=roadmap_id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    )


@router.patch(
    "/{organization_id}/initiatives/{initiative_id}/progress",
    response_model=DecarbonizationInitiativeResponse,
)
async def update_initiative(
    organization_id: str,
    initiative_id: str,
    body: InitiativeProgressUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        init = await db.run_sync(
            lambda s: roadmap_service.update_initiative_progress(
                initiative_id,
                body.actual_reduction,
                body.status,
                actor_id,
                s,
                organization_id=organization_id,
            )
        )
        await db.refresh(init)
    except SustainabilityError as exc:
        raise _err(exc)
    return init


# ── Net Zero Roadmaps ─────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/roadmaps",
    response_model=NetZeroRoadmapResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_roadmap(
    organization_id: str,
    body: NetZeroRoadmapCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rm = await db.run_sync(
            lambda s: roadmap_service.create_roadmap(
                organization_id=organization_id,
                name=body.name,
                baseline_year=body.baseline_year,
                target_year=body.target_year,
                baseline_emissions=body.baseline_emissions,
                target_reduction_percent=body.target_reduction_percent,
                actor_id=actor_id,
                session=s,
                description=body.description,
            )
        )
        await db.refresh(rm)
    except SustainabilityError as exc:
        raise _err(exc)
    return rm


@router.get("/{organization_id}/roadmaps", response_model=list[NetZeroRoadmapResponse])
async def list_roadmaps(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: roadmap_service.list_roadmaps(organization_id, s, limit=limit, offset=offset)
    )


@router.post(
    "/{organization_id}/roadmaps/{roadmap_id}/milestones",
    response_model=NetZeroMilestoneResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_milestone(
    organization_id: str,
    roadmap_id: str,
    body: MilestoneCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    ms = await db.run_sync(
        lambda s: roadmap_service.add_milestone(
            roadmap_id=roadmap_id,
            milestone_year=body.milestone_year,
            target_emissions=body.target_emissions,
            actor_id=actor_id,
            session=s,
            notes=body.notes,
        )
    )
    await db.refresh(ms)
    return ms


@router.get(
    "/{organization_id}/roadmaps/{roadmap_id}/milestones",
    response_model=list[NetZeroMilestoneResponse],
)
async def list_milestones(
    organization_id: str,
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(lambda s: roadmap_service.list_milestones(roadmap_id, s))


@router.patch(
    "/{organization_id}/milestones/{milestone_id}",
    response_model=NetZeroMilestoneResponse,
)
async def update_milestone(
    organization_id: str,
    milestone_id: str,
    body: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        ms = await db.run_sync(
            lambda s: roadmap_service.update_milestone(
                milestone_id, body.actual_emissions, body.status, actor_id, s
            )
        )
        await db.refresh(ms)
    except SustainabilityError as exc:
        raise _err(exc)
    return ms


# ── Science Based Targets ─────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/sbts",
    response_model=ScienceBasedTargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sbt(
    organization_id: str,
    body: ScienceBasedTargetCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        sbt = await db.run_sync(
            lambda s: roadmap_service.create_science_based_target(
                organization_id=organization_id,
                scope=body.scope,
                target_type=body.target_type,
                baseline_year=body.baseline_year,
                baseline_emissions=body.baseline_emissions,
                target_reduction_percent=body.target_reduction_percent,
                target_year=body.target_year,
                actor_id=actor_id,
                session=s,
                sbt_framework=body.sbt_framework,
                description=body.description,
                commitment_date=body.commitment_date,
            )
        )
        await db.refresh(sbt)
    except SustainabilityError as exc:
        raise _err(exc)
    return sbt


@router.get("/{organization_id}/sbts", response_model=list[ScienceBasedTargetResponse])
async def list_sbts(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: roadmap_service.list_science_based_targets(
            organization_id, s, limit=limit, offset=offset
        )
    )


@router.patch("/{organization_id}/sbts/{sbt_id}/status", response_model=ScienceBasedTargetResponse)
async def update_sbt_status(
    organization_id: str,
    sbt_id: str,
    body: SBTStatusUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        sbt = await db.run_sync(
            lambda s: roadmap_service.update_sbt_status(
                sbt_id,
                body.status,
                actor_id,
                s,
                organization_id=organization_id,
                approval_date=body.approval_date,
            )
        )
        await db.refresh(sbt)
    except SustainabilityError as exc:
        raise _err(exc)
    return sbt


# ── Climate Risk ──────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/climate-risk",
    response_model=ClimateRiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_climate_risk(
    organization_id: str,
    body: ClimateRiskAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        cra = await db.run_sync(
            lambda s: climate_service.create_climate_risk_assessment(
                organization_id=organization_id,
                title=body.title,
                assessment_year=body.assessment_year,
                transition_risk_score=body.transition_risk_score,
                physical_risk_score=body.physical_risk_score,
                regulatory_risk_score=body.regulatory_risk_score,
                actor_id=actor_id,
                session=s,
                scenario=body.scenario,
                transition_risk_details=body.transition_risk_details,
                physical_risk_details=body.physical_risk_details,
                regulatory_risk_details=body.regulatory_risk_details,
                network_entity_id=body.network_entity_id,
                regulation_id=body.regulation_id,
                notes=body.notes,
            )
        )
        await db.refresh(cra)
    except SustainabilityError as exc:
        raise _err(exc)
    return cra


@router.get(
    "/{organization_id}/climate-risk",
    response_model=list[ClimateRiskAssessmentResponse],
)
async def list_climate_risk(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: climate_service.list_climate_risk_assessments(
            organization_id, s, limit=limit, offset=offset
        )
    )


# ── Assurance ─────────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/assurance",
    response_model=AssuranceRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assurance(
    organization_id: str,
    body: AssuranceRecordCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: reporting_service.create_assurance_record(
                organization_id=organization_id,
                report_type=body.report_type,
                reviewed_period_start=body.reviewed_period_start,
                reviewed_period_end=body.reviewed_period_end,
                reviewer_user_id=body.reviewer_user_id,
                assurance_level=body.assurance_level,
                actor_id=actor_id,
                session=s,
                findings=body.findings,
                methodology=body.methodology,
            )
        )
        await db.refresh(rec)
    except SustainabilityError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/assurance", response_model=list[AssuranceRecordResponse])
async def list_assurance(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: reporting_service.list_assurance_records(
            organization_id, s, limit=limit, offset=offset
        )
    )


# ── CSRD Mappings ─────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/csrd-mappings",
    response_model=CSRDMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_csrd_mapping(
    organization_id: str,
    body: CSRDMappingCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        m = await db.run_sync(
            lambda s: reporting_service.create_csrd_mapping(
                organization_id=organization_id,
                esrs_standard=body.esrs_standard,
                actor_id=actor_id,
                session=s,
                kpi_id=body.kpi_id,
                objective_id=body.objective_id,
                target_id=body.target_id,
                disclosure_requirement=body.disclosure_requirement,
                data_point_reference=body.data_point_reference,
                compliance_status=body.compliance_status,
                notes=body.notes,
            )
        )
        await db.refresh(m)
    except SustainabilityError as exc:
        raise _err(exc)
    return m


@router.get("/{organization_id}/csrd-mappings", response_model=list[CSRDMappingResponse])
async def list_csrd_mappings(
    organization_id: str,
    esrs_standard: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: reporting_service.list_csrd_mappings(
            organization_id, s, esrs_standard=esrs_standard, limit=limit, offset=offset
        )
    )


# ── ISSB Mappings ─────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/issb-mappings",
    response_model=ISSBMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_issb_mapping(
    organization_id: str,
    body: ISSBMappingCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        m = await db.run_sync(
            lambda s: reporting_service.create_issb_mapping(
                organization_id=organization_id,
                issb_standard=body.issb_standard,
                actor_id=actor_id,
                session=s,
                kpi_id=body.kpi_id,
                objective_id=body.objective_id,
                disclosure_topic=body.disclosure_topic,
                metric_reference=body.metric_reference,
                compliance_status=body.compliance_status,
                notes=body.notes,
            )
        )
        await db.refresh(m)
    except SustainabilityError as exc:
        raise _err(exc)
    return m


@router.get("/{organization_id}/issb-mappings", response_model=list[ISSBMappingResponse])
async def list_issb_mappings(
    organization_id: str,
    issb_standard: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: reporting_service.list_issb_mappings(
            organization_id, s, issb_standard=issb_standard, limit=limit, offset=offset
        )
    )


# ── Forecasts ─────────────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/forecasts",
    response_model=ForecastResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_forecast(
    organization_id: str,
    body: ForecastCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        fc = await db.run_sync(
            lambda s: scoring_service.create_forecast(
                organization_id=organization_id,
                forecast_type=body.forecast_type,
                method=body.method,
                period_start=body.period_start,
                period_end=body.period_end,
                historical_data=body.historical_data,
                forecast_horizon_months=body.forecast_horizon_months,
                actor_id=actor_id,
                session=s,
                kpi_id=body.kpi_id,
                assumptions=body.assumptions,
            )
        )
        await db.refresh(fc)
    except SustainabilityError as exc:
        raise _err(exc)
    return fc


@router.get("/{organization_id}/forecasts", response_model=list[ForecastResponse])
async def list_forecasts(
    organization_id: str,
    forecast_type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: scoring_service.list_forecasts(
            organization_id, s, forecast_type=forecast_type, limit=limit, offset=offset
        )
    )


# ── Scenario Analysis ─────────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/scenarios",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scenario(
    organization_id: str,
    body: ScenarioCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        sc = await db.run_sync(
            lambda s: scoring_service.create_scenario(
                organization_id=organization_id,
                name=body.name,
                scenario_type=body.scenario_type,
                inputs=body.inputs,
                assumptions=body.assumptions,
                actor_id=actor_id,
                session=s,
                description=body.description,
            )
        )
        await db.refresh(sc)
    except SustainabilityError as exc:
        raise _err(exc)
    return sc


@router.get("/{organization_id}/scenarios", response_model=list[ScenarioResponse])
async def list_scenarios(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: scoring_service.list_scenarios(organization_id, s, limit=limit, offset=offset)
    )


# ── Sustainability Reports ─────────────────────────────────────────────────────


@router.post(
    "/{organization_id}/reports",
    response_model=SustainabilityReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    organization_id: str,
    body: SustainabilityReportCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        report = await db.run_sync(
            lambda s: reporting_service.generate_report(
                organization_id=organization_id,
                title=body.title,
                period_start=body.period_start,
                period_end=body.period_end,
                report_type=body.report_type,
                actor_id=actor_id,
                session=s,
            )
        )
        await db.refresh(report)
    except SustainabilityError as exc:
        raise _err(exc)
    return report


@router.get("/{organization_id}/reports", response_model=list[SustainabilityReportResponse])
async def list_reports(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: reporting_service.list_reports(organization_id, s, limit=limit, offset=offset)
    )


@router.get(
    "/{organization_id}/reports/{report_id}",
    response_model=SustainabilityReportResponse,
)
async def get_report(
    organization_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    report = await db.run_sync(lambda s: reporting_service.get_report(report_id, s))
    if not report or report.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post(
    "/{organization_id}/reports/{report_id}/finalize",
    response_model=SustainabilityReportResponse,
)
async def finalize_report(
    organization_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        report = await db.run_sync(
            lambda s: reporting_service.finalize_report(
                report_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(report)
    except SustainabilityConflict as exc:
        raise _conflict(exc)
    except SustainabilityError as exc:
        raise _err(exc)
    return report


# ── Rollup helpers ─────────────────────────────────────────────────────────────


def _rollup_to_response(r: rollup_service.RollupSummary) -> RollupSummaryResponse:
    from interfaces.api.schemas.sustainability import (
        ClimateRiskRollupSchema,
        EmissionsRollupSchema,
        KPIsRollupSchema,
        ObjectivesRollupSchema,
        ScoreRollupSchema,
        TargetsRollupSchema,
    )

    return RollupSummaryResponse(
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        organization_ids=r.organization_ids,
        computed_at=r.computed_at,
        emissions=EmissionsRollupSchema(
            total_emissions=r.emissions.total_emissions,
            scope1=r.emissions.scope1,
            scope2=r.emissions.scope2,
            scope3=r.emissions.scope3,
            inventories_count=r.emissions.inventories_count,
        ),
        objectives=ObjectivesRollupSchema(
            total=r.objectives.total,
            active=r.objectives.active,
            completed=r.objectives.completed,
            completion_percent=r.objectives.completion_percent,
        ),
        targets=TargetsRollupSchema(
            total=r.targets.total,
            with_measurements=r.targets.with_measurements,
            attainment_percent=r.targets.attainment_percent,
        ),
        kpis=KPIsRollupSchema(
            total=r.kpis.total,
            active=r.kpis.active,
        ),
        scores=ScoreRollupSchema(
            avg_overall_score=r.scores.avg_overall_score,
            avg_environmental_score=r.scores.avg_environmental_score,
            avg_social_score=r.scores.avg_social_score,
            avg_governance_score=r.scores.avg_governance_score,
            scorecard_count=r.scores.scorecard_count,
        ),
        climate_risks=ClimateRiskRollupSchema(
            avg_overall_risk=r.climate_risks.avg_overall_risk,
            avg_transition_risk=r.climate_risks.avg_transition_risk,
            avg_physical_risk=r.climate_risks.avg_physical_risk,
            avg_regulatory_risk=r.climate_risks.avg_regulatory_risk,
            assessment_count=r.climate_risks.assessment_count,
        ),
    )


# ── Rollup endpoints ───────────────────────────────────────────────────────────


@router.get("/rollups/enterprise/{entity_id}", response_model=RollupSummaryResponse)
async def rollup_enterprise(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        result = await db.run_sync(
            lambda s: rollup_service.compute_rollup("enterprise", entity_id, actor_id, s)
        )
    except SustainabilityError as exc:
        raise _err(exc)
    return _rollup_to_response(result)


@router.get("/rollups/business-unit/{entity_id}", response_model=RollupSummaryResponse)
async def rollup_business_unit(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        result = await db.run_sync(
            lambda s: rollup_service.compute_rollup("business_unit", entity_id, actor_id, s)
        )
    except SustainabilityError as exc:
        raise _err(exc)
    return _rollup_to_response(result)


@router.get("/rollups/legal-entity/{entity_id}", response_model=RollupSummaryResponse)
async def rollup_legal_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        result = await db.run_sync(
            lambda s: rollup_service.compute_rollup("legal_entity", entity_id, actor_id, s)
        )
    except SustainabilityError as exc:
        raise _err(exc)
    return _rollup_to_response(result)


@router.get("/rollups/region/{entity_id}", response_model=RollupSummaryResponse)
async def rollup_region(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        result = await db.run_sync(
            lambda s: rollup_service.compute_rollup("region", entity_id, actor_id, s)
        )
    except SustainabilityError as exc:
        raise _err(exc)
    return _rollup_to_response(result)
