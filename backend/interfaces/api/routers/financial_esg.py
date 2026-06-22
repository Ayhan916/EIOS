"""M43 — Financial ESG, Value Creation & Capital Markets Platform Router."""

from __future__ import annotations

import jwt as _jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.financial_esg import (
    carbon_cost_service,
    finance_service,
    kpi_service,
    readiness_service,
    reporting_service,
    revenue_service,
    risk_service,
    rollup_service,
    taxonomy_service,
    value_service,
)
from application.financial_esg.kpi_service import FinancialESGError, FinancialESGConflict
from interfaces.api.deps import get_db
from interfaces.api.schemas.financial_esg import (
    CapitalMarketsAssessmentCreate,
    CapitalMarketsAssessmentResponse,
    CarbonCostModelCreate,
    CarbonCostModelResponse,
    ClimateFinanceCreate,
    ClimateFinanceResponse,
    CorrelationCreate,
    CorrelationResponse,
    CovenantMonitorRequest,
    DisclosurePackageCreate,
    DisclosurePackageResponse,
    FinanceInstrumentCreate,
    FinanceInstrumentResponse,
    FinancialKPICreate,
    FinancialKPIResponse,
    FinancialReportCreate,
    FinancialReportResponse,
    FinancialRollupResponse,
    CarbonEconomicsRollupSchema,
    GreenRevenueRollupSchema,
    TaxonomyRollupSchema,
    FinanceRollupSchema,
    ValueCreationRollupSchema,
    GreenCapexCreate,
    GreenCapexResponse,
    GreenOpexCreate,
    GreenOpexResponse,
    GreenRevenueCreate,
    GreenRevenueResponse,
    KPIMeasurementCreate,
    KPIMeasurementResponse,
    LinkedKPICreate,
    LinkedKPIResponse,
    MilestoneCreate,
    MilestoneResponse,
    ScenarioCreate,
    ScenarioResponse,
    TaxonomyAssessmentCreate,
    TaxonomyAssessmentResponse,
    TaxonomyStatusUpdate,
    TransitionPlanCreate,
    TransitionPlanResponse,
    ValuationCreate,
    ValuationResponse,
    ValueInitiativeCreate,
    ValueInitiativeResponse,
    ValueInitiativeUpdate,
    CostOfRiskCreate,
    CostOfRiskResponse,
)
from shared.security import decode_token

router = APIRouter(prefix="/financial-esg", tags=["financial-esg"])


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
        raise HTTPException(status_code=401, detail="Token expired", headers={"WWW-Authenticate": "Bearer"})
    except _jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type", headers={"WWW-Authenticate": "Bearer"})
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing subject", headers={"WWW-Authenticate": "Bearer"})
    return sub


def _err(exc: FinancialESGError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _conflict(exc: FinancialESGConflict) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ── Financial ESG KPIs ────────────────────────────────────────────────────────

@router.post("/{organization_id}/kpis", response_model=FinancialKPIResponse, status_code=201)
async def create_kpi(
    organization_id: str,
    body: FinancialKPICreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: kpi_service.create_kpi(
                organization_id, body.name, body.category, actor_id, s,
                formula=body.formula, unit=body.unit, frequency=body.frequency,
                owner_user_id=body.owner_user_id, description=body.description,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/kpis", response_model=list[FinancialKPIResponse])
async def list_kpis(
    organization_id: str,
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: kpi_service.list_kpis(organization_id, s, category=category, limit=limit, offset=offset)
    )


@router.post("/{organization_id}/kpis/measurements", response_model=KPIMeasurementResponse, status_code=201)
async def record_measurement(
    organization_id: str,
    body: KPIMeasurementCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: kpi_service.record_measurement(
                body.kpi_id, organization_id, body.period, body.value, actor_id, s,
                source=body.source, confidence=body.confidence, notes=body.notes,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/kpis/{kpi_id}/measurements", response_model=list[KPIMeasurementResponse])
async def list_measurements(
    organization_id: str,
    kpi_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        return await db.run_sync(
            lambda s: kpi_service.list_measurements(kpi_id, organization_id, s, limit=limit, offset=offset)
        )
    except FinancialESGError as exc:
        raise _err(exc)


# ── Carbon Cost ───────────────────────────────────────────────────────────────

@router.post("/{organization_id}/carbon-cost", response_model=CarbonCostModelResponse, status_code=201)
async def create_carbon_cost(
    organization_id: str,
    body: CarbonCostModelCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: carbon_cost_service.create_carbon_cost_model(
            organization_id, body.name, body.assessment_year,
            body.total_emissions, body.internal_carbon_price, body.regulatory_carbon_price,
            actor_id, s,
            avoided_emissions=body.avoided_emissions, currency=body.currency,
            inventory_id=body.inventory_id, notes=body.notes,
        )
    )
    await db.refresh(rec)
    return rec


@router.get("/{organization_id}/carbon-cost", response_model=list[CarbonCostModelResponse])
async def list_carbon_cost(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: carbon_cost_service.list_carbon_cost_models(organization_id, s, limit=limit, offset=offset)
    )


# ── Cost of Risk ──────────────────────────────────────────────────────────────

@router.post("/{organization_id}/risk", response_model=CostOfRiskResponse, status_code=201)
async def create_risk_assessment(
    organization_id: str,
    body: CostOfRiskCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: risk_service.create_cost_of_risk_assessment(
                organization_id, body.name,
                body.supplier_risk_score, body.climate_risk_score,
                body.compliance_risk_score, body.operational_risk_score,
                body.exposure_base, actor_id, s,
                currency=body.currency, notes=body.notes,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/risk", response_model=list[CostOfRiskResponse])
async def list_risk_assessments(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: risk_service.list_risk_assessments(organization_id, s, limit=limit, offset=offset)
    )


# ── Value Creation ────────────────────────────────────────────────────────────

@router.post("/{organization_id}/value-creation", response_model=ValueInitiativeResponse, status_code=201)
async def create_value_initiative(
    organization_id: str,
    body: ValueInitiativeCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: value_service.create_value_creation_initiative(
            organization_id, body.name, body.investment_amount, body.expected_value, actor_id, s,
            description=body.description, realized_value=body.realized_value,
            payback_period_months=body.payback_period_months,
            start_date=body.start_date, end_date=body.end_date,
            currency=body.currency, category=body.category,
        )
    )
    await db.refresh(rec)
    return rec


@router.patch("/{organization_id}/value-creation/{initiative_id}", response_model=ValueInitiativeResponse)
async def update_value_initiative(
    organization_id: str,
    initiative_id: str,
    body: ValueInitiativeUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: value_service.update_realized_value(
                initiative_id, body.realized_value, actor_id, s,
                organization_id=organization_id, new_status=body.new_status,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/value-creation", response_model=list[ValueInitiativeResponse])
async def list_value_initiatives(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: value_service.list_value_initiatives(organization_id, s, limit=limit, offset=offset)
    )


# ── Sustainable Finance ───────────────────────────────────────────────────────

@router.post("/{organization_id}/finance", response_model=FinanceInstrumentResponse, status_code=201)
async def create_finance_instrument(
    organization_id: str,
    body: FinanceInstrumentCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: finance_service.create_finance_instrument(
                organization_id, body.name, body.instrument_type, body.amount, actor_id, s,
                currency=body.currency, maturity_date=body.maturity_date,
                issuer=body.issuer, counterparty=body.counterparty,
                description=body.description, kpi_linkage=body.kpi_linkage,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/finance", response_model=list[FinanceInstrumentResponse])
async def list_finance_instruments(
    organization_id: str,
    instrument_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: finance_service.list_finance_instruments(
            organization_id, s, instrument_type=instrument_type, limit=limit, offset=offset
        )
    )


@router.post("/{organization_id}/finance/linked-kpis", response_model=LinkedKPIResponse, status_code=201)
async def create_linked_kpi(
    organization_id: str,
    body: LinkedKPICreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: finance_service.create_linked_kpi(
                organization_id, body.instrument_id, body.kpi_name, actor_id, s,
                esg_target_id=body.esg_target_id, kpi_description=body.kpi_description,
                threshold_value=body.threshold_value, threshold_direction=body.threshold_direction,
                current_value=body.current_value,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.post("/{organization_id}/finance/linked-kpis/{linked_kpi_id}/monitor", response_model=LinkedKPIResponse)
async def monitor_covenant(
    organization_id: str,
    linked_kpi_id: str,
    body: CovenantMonitorRequest,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: finance_service.monitor_covenant(
                linked_kpi_id, body.current_value, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


# ── Transition Plans ──────────────────────────────────────────────────────────

@router.post("/{organization_id}/transition-plans", response_model=TransitionPlanResponse, status_code=201)
async def create_transition_plan(
    organization_id: str,
    body: TransitionPlanCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: finance_service.create_transition_plan(
            organization_id, body.name, actor_id, s,
            description=body.description, baseline_state=body.baseline_state,
            target_state=body.target_state, financing_needs=body.financing_needs,
            funding_sources=body.funding_sources, start_date=body.start_date,
            target_date=body.target_date, currency=body.currency,
        )
    )
    await db.refresh(rec)
    return rec


@router.get("/{organization_id}/transition-plans", response_model=list[TransitionPlanResponse])
async def list_transition_plans(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: finance_service.list_transition_plans(organization_id, s, limit=limit, offset=offset)
    )


@router.post("/{organization_id}/transition-plans/{plan_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def add_milestone(
    organization_id: str,
    plan_id: str,
    body: MilestoneCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: finance_service.add_transition_milestone(
                plan_id, organization_id, body.title, actor_id, s,
                description=body.description, due_date=body.due_date,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


# ── Taxonomy ──────────────────────────────────────────────────────────────────

@router.post("/{organization_id}/taxonomy", response_model=TaxonomyAssessmentResponse, status_code=201)
async def create_taxonomy_assessment(
    organization_id: str,
    body: TaxonomyAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: taxonomy_service.create_taxonomy_assessment(
                organization_id, body.assessment_year, actor_id, s,
                taxonomy_framework=body.taxonomy_framework,
                eligible_activities=body.eligible_activities,
                aligned_activities=body.aligned_activities,
                total_revenue=body.total_revenue,
                total_capex=body.total_capex,
                total_opex=body.total_opex,
                justification=body.justification,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.patch("/{organization_id}/taxonomy/{assessment_id}/status", response_model=TaxonomyAssessmentResponse)
async def update_taxonomy_status(
    organization_id: str,
    assessment_id: str,
    body: TaxonomyStatusUpdate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: taxonomy_service.update_assessment_status(
                assessment_id, body.new_status, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/taxonomy", response_model=list[TaxonomyAssessmentResponse])
async def list_taxonomy_assessments(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: taxonomy_service.list_taxonomy_assessments(organization_id, s, limit=limit, offset=offset)
    )


# ── Green Revenue ─────────────────────────────────────────────────────────────

@router.post("/{organization_id}/revenue", response_model=GreenRevenueResponse, status_code=201)
async def create_green_revenue(
    organization_id: str,
    body: GreenRevenueCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: revenue_service.create_green_revenue(
                organization_id, body.revenue_stream, body.amount, body.total_revenue,
                body.period, actor_id, s,
                taxonomy_category=body.taxonomy_category,
                alignment_status=body.alignment_status, currency=body.currency, notes=body.notes,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/revenue", response_model=list[GreenRevenueResponse])
async def list_green_revenue(
    organization_id: str,
    period: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: revenue_service.list_green_revenue(
            organization_id, s, period=period, limit=limit, offset=offset
        )
    )


@router.post("/{organization_id}/capex", response_model=GreenCapexResponse, status_code=201)
async def create_green_capex(
    organization_id: str,
    body: GreenCapexCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: revenue_service.create_green_capex(
                organization_id, body.project_name, body.amount, body.alignment_percent,
                body.period, actor_id, s,
                taxonomy_category=body.taxonomy_category, currency=body.currency, notes=body.notes,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/capex", response_model=list[GreenCapexResponse])
async def list_green_capex(
    organization_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: revenue_service.list_green_capex(organization_id, s, limit=limit, offset=offset)
    )


@router.post("/{organization_id}/opex", response_model=GreenOpexResponse, status_code=201)
async def create_green_opex(
    organization_id: str,
    body: GreenOpexCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: revenue_service.create_green_opex(
                organization_id, body.description, body.amount, body.alignment_percent,
                body.period, actor_id, s,
                category=body.category, currency=body.currency, notes=body.notes,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/opex", response_model=list[GreenOpexResponse])
async def list_green_opex(
    organization_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: revenue_service.list_green_opex(organization_id, s, limit=limit, offset=offset)
    )


# ── Capital Markets Readiness ─────────────────────────────────────────────────

@router.post("/{organization_id}/readiness", response_model=CapitalMarketsAssessmentResponse, status_code=201)
async def create_readiness_assessment(
    organization_id: str,
    body: CapitalMarketsAssessmentCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: readiness_service.create_capital_markets_assessment(
                organization_id, actor_id, s,
                disclosure_readiness=body.disclosure_readiness,
                assurance_readiness=body.assurance_readiness,
                taxonomy_readiness=body.taxonomy_readiness,
                kpi_readiness=body.kpi_readiness,
                assessment_notes=body.assessment_notes,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/readiness", response_model=list[CapitalMarketsAssessmentResponse])
async def list_readiness_assessments(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: readiness_service.list_capital_markets_assessments(
            organization_id, s, limit=limit, offset=offset
        )
    )


# ── Investor Disclosure Packages ──────────────────────────────────────────────

@router.post("/{organization_id}/disclosure-packages", response_model=DisclosurePackageResponse, status_code=201)
async def create_disclosure_package(
    organization_id: str,
    body: DisclosurePackageCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: readiness_service.generate_disclosure_package(
            organization_id, body.title, body.period_start, body.period_end, actor_id, s,
            description=body.description,
            esg_kpi_snapshot=body.esg_kpi_snapshot,
            taxonomy_snapshot=body.taxonomy_snapshot,
            climate_metrics_snapshot=body.climate_metrics_snapshot,
            assurance_status_snapshot=body.assurance_status_snapshot,
            sustainability_targets_snapshot=body.sustainability_targets_snapshot,
        )
    )
    await db.refresh(rec)
    return rec


@router.post("/{organization_id}/disclosure-packages/{package_id}/finalize", response_model=DisclosurePackageResponse)
async def finalize_disclosure_package(
    organization_id: str,
    package_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: readiness_service.finalize_disclosure_package(
                package_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(rec)
    except FinancialESGConflict as exc:
        raise _conflict(exc)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/disclosure-packages", response_model=list[DisclosurePackageResponse])
async def list_disclosure_packages(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: readiness_service.list_disclosure_packages(organization_id, s, limit=limit, offset=offset)
    )


# ── Climate Finance Analytics ─────────────────────────────────────────────────

@router.post("/{organization_id}/climate-finance", response_model=ClimateFinanceResponse, status_code=201)
async def create_climate_finance(
    organization_id: str,
    body: ClimateFinanceCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: value_service.create_climate_finance_analysis(
            organization_id, body.analysis_name, body.analysis_year,
            body.transition_investment, body.emissions_reduction, actor_id, s,
            carbon_price_proxy=body.carbon_price_proxy,
            currency=body.currency, notes=body.notes,
        )
    )
    await db.refresh(rec)
    return rec


@router.get("/{organization_id}/climate-finance", response_model=list[ClimateFinanceResponse])
async def list_climate_finance(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: value_service.list_climate_analyses(organization_id, s, limit=limit, offset=offset)
    )


# ── Sustainability Valuation ──────────────────────────────────────────────────

@router.post("/{organization_id}/valuation", response_model=ValuationResponse, status_code=201)
async def create_valuation(
    organization_id: str,
    body: ValuationCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: value_service.create_sustainability_valuation(
            organization_id, body.valuation_name, body.valuation_year,
            body.risk_reduction_value, body.carbon_reduction_value,
            body.operational_efficiency_value, actor_id, s,
            currency=body.currency, notes=body.notes,
        )
    )
    await db.refresh(rec)
    return rec


@router.get("/{organization_id}/valuation", response_model=list[ValuationResponse])
async def list_valuations(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: value_service.list_valuations(organization_id, s, limit=limit, offset=offset)
    )


# ── Scenario Analysis ─────────────────────────────────────────────────────────

@router.post("/{organization_id}/scenarios", response_model=ScenarioResponse, status_code=201)
async def create_scenario(
    organization_id: str,
    body: ScenarioCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: reporting_service.create_scenario_analysis(
                organization_id, body.scenario_name, body.scenario_type,
                body.inputs, body.assumptions, actor_id, s, notes=body.notes,
            )
        )
        await db.refresh(rec)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/scenarios", response_model=list[ScenarioResponse])
async def list_scenarios(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: reporting_service.list_scenario_analyses(organization_id, s, limit=limit, offset=offset)
    )


# ── ESG Financial Correlation ─────────────────────────────────────────────────

@router.post("/{organization_id}/correlations", response_model=CorrelationResponse, status_code=201)
async def create_correlation(
    organization_id: str,
    body: CorrelationCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: reporting_service.create_esg_correlation(
            organization_id, body.esg_score, body.risk_reduction,
            body.cost_reduction, body.financial_performance, body.correlation_period,
            actor_id, s,
            scorecard_id=body.scorecard_id, methodology=body.methodology,
            assumptions=body.assumptions,
        )
    )
    await db.refresh(rec)
    return rec


@router.get("/{organization_id}/correlations", response_model=list[CorrelationResponse])
async def list_correlations(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: reporting_service.list_correlations(organization_id, s, limit=limit, offset=offset)
    )


# ── Reports ───────────────────────────────────────────────────────────────────

@router.post("/{organization_id}/reports", response_model=FinancialReportResponse, status_code=201)
async def generate_report(
    organization_id: str,
    body: FinancialReportCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    rec = await db.run_sync(
        lambda s: reporting_service.generate_financial_esg_report(
            organization_id, body.title, body.report_period_start, body.report_period_end, actor_id, s
        )
    )
    await db.refresh(rec)
    return rec


@router.post("/{organization_id}/reports/{report_id}/finalize", response_model=FinancialReportResponse)
async def finalize_report(
    organization_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        rec = await db.run_sync(
            lambda s: reporting_service.finalize_financial_esg_report(
                report_id, actor_id, s, organization_id=organization_id
            )
        )
        await db.refresh(rec)
    except FinancialESGConflict as exc:
        raise _conflict(exc)
    except FinancialESGError as exc:
        raise _err(exc)
    return rec


@router.get("/{organization_id}/reports", response_model=list[FinancialReportResponse])
async def list_reports(
    organization_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    return await db.run_sync(
        lambda s: reporting_service.list_financial_esg_reports(organization_id, s, limit=limit, offset=offset)
    )


# ── Enterprise Rollups ────────────────────────────────────────────────────────

def _rollup_to_response(r: rollup_service.FinancialRollupSummary) -> FinancialRollupResponse:
    return FinancialRollupResponse(
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        organization_ids=r.organization_ids,
        computed_at=r.computed_at,
        carbon_economics=CarbonEconomicsRollupSchema(
            total_carbon_cost=r.carbon_economics.total_carbon_cost,
            total_regulatory_exposure=r.carbon_economics.total_regulatory_exposure,
            total_avoided_cost=r.carbon_economics.total_avoided_cost,
            model_count=r.carbon_economics.model_count,
        ),
        green_revenue=GreenRevenueRollupSchema(
            total_green_amount=r.green_revenue.total_green_amount,
            avg_green_percent=r.green_revenue.avg_green_percent,
            record_count=r.green_revenue.record_count,
        ),
        taxonomy=TaxonomyRollupSchema(
            avg_aligned_percent=r.taxonomy.avg_aligned_percent,
            avg_eligible_percent=r.taxonomy.avg_eligible_percent,
            assessment_count=r.taxonomy.assessment_count,
        ),
        finance=FinanceRollupSchema(
            total_exposure=r.finance.total_exposure,
            instrument_count=r.finance.instrument_count,
            breached_count=r.finance.breached_count,
        ),
        value_creation=ValueCreationRollupSchema(
            total_investment=r.value_creation.total_investment,
            total_realized_value=r.value_creation.total_realized_value,
            initiative_count=r.value_creation.initiative_count,
            avg_roi_percent=r.value_creation.avg_roi_percent,
        ),
    )


@router.get("/rollups/enterprise/{entity_id}", response_model=FinancialRollupResponse)
async def rollup_enterprise(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        r = await db.run_sync(
            lambda s: rollup_service.compute_financial_rollup("enterprise", entity_id, actor_id, s)
        )
    except FinancialESGError as exc:
        raise _err(exc)
    return _rollup_to_response(r)


@router.get("/rollups/business-unit/{entity_id}", response_model=FinancialRollupResponse)
async def rollup_business_unit(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        r = await db.run_sync(
            lambda s: rollup_service.compute_financial_rollup("business_unit", entity_id, actor_id, s)
        )
    except FinancialESGError as exc:
        raise _err(exc)
    return _rollup_to_response(r)


@router.get("/rollups/legal-entity/{entity_id}", response_model=FinancialRollupResponse)
async def rollup_legal_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        r = await db.run_sync(
            lambda s: rollup_service.compute_financial_rollup("legal_entity", entity_id, actor_id, s)
        )
    except FinancialESGError as exc:
        raise _err(exc)
    return _rollup_to_response(r)


@router.get("/rollups/region/{entity_id}", response_model=FinancialRollupResponse)
async def rollup_region(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(_require_actor),
):
    try:
        r = await db.run_sync(
            lambda s: rollup_service.compute_financial_rollup("region", entity_id, actor_id, s)
        )
    except FinancialESGError as exc:
        raise _err(exc)
    return _rollup_to_response(r)
