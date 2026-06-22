"""M44 — Digital Twin, Strategic Planning & Scenario Intelligence Router.

All endpoints scoped to /strategy/{org_id}/ for tenant isolation.
"""

from __future__ import annotations

import jwt as _jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from application.strategy import (
    board_simulation_service,
    comparison_service,
    digital_twin_service,
    forecast_service,
    methodology_service,
    pathway_service,
    planning_service,
    reporting_service,
    rollup_service,
    scenario_service,
    stress_test_service,
    template_service,
)
from application.strategy.digital_twin_service import StrategyError
from interfaces.api.deps import get_db
from interfaces.api.schemas.strategy import (
    AssumptionCreate,
    AssumptionResponse,
    BoardSimulationCreate,
    BoardSimulationResponse,
    ClimateStressTestCreate,
    ClimateStressTestResponse,
    DigitalTwinCreate,
    DigitalTwinResponse,
    ExecutionCreate,
    ExecutionResponse,
    FinancialStressTestCreate,
    FinancialStressTestResponse,
    ForecastModelCreate,
    ForecastModelResponse,
    ForecastResultResponse,
    ForecastRunCreate,
    ForecastWindowPolicyCreate,
    ForecastWindowPolicyResponse,
    NetZeroPathwayCreate,
    NetZeroPathwayResponse,
    ScenarioComparisonCreate,
    ScenarioComparisonResponse,
    ScenarioCreate,
    ScenarioResponse,
    ScenarioTemplateCreate,
    ScenarioTemplateResponse,
    SnapshotCreate,
    SnapshotResponse,
    StrategicObjectiveCreate,
    StrategicObjectiveResponse,
    StrategicPlanCreate,
    StrategicPlanResponse,
    StrategicReportCreate,
    StrategicReportResponse,
    StrategyMethodologyCreate,
    StrategyMethodologyResponse,
    StrategyRollupResponse,
    StressTestTemplateCreate,
    StressTestTemplateResponse,
    SupplierShockCreate,
    SupplierShockResponse,
    TemplateInstantiateCreate,
    TransitionPathwayCreate,
    TransitionPathwayResponse,
)

router = APIRouter(prefix="/strategy", tags=["strategy"])


def _actor(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = _jwt.decode(auth[7:], options={"verify_signature": False})
            return str(payload.get("sub", "unknown"))
        except Exception:
            pass
    return "unknown"


def _err(exc: StrategyError) -> HTTPException:
    msg = str(exc)
    if "not found" in msg:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ── Digital Twin ──────────────────────────────────────────────────────────────

@router.get("/{org_id}/digital-twin", response_model=list[DigitalTwinResponse])
def list_twins(org_id: str, db: Session = Depends(get_db)):
    return digital_twin_service.list_digital_twins(org_id, db)


@router.post("/{org_id}/digital-twin", response_model=DigitalTwinResponse, status_code=201)
def create_twin(org_id: str, body: DigitalTwinCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = digital_twin_service.create_digital_twin(
            org_id, body.name, _actor(request), db,
            description=body.description,
            twin_version=body.twin_version,
            supplier_count=body.supplier_count,
            kpi_count=body.kpi_count,
            risk_count=body.risk_count,
            emissions_baseline_tco2e=body.emissions_baseline_tco2e,
            financial_baseline=body.financial_baseline,
            assumptions=body.assumptions,
            business_units=body.business_units,
            legal_entities=body.legal_entities,
            regions=body.regions,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/digital-twin/{twin_id}/snapshots", response_model=list[SnapshotResponse])
def list_snapshots(org_id: str, twin_id: str, db: Session = Depends(get_db)):
    try:
        return digital_twin_service.list_snapshots(org_id, twin_id, db)
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/digital-twin/{twin_id}/snapshots", response_model=SnapshotResponse, status_code=201)
def create_snapshot(org_id: str, twin_id: str, body: SnapshotCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = digital_twin_service.create_snapshot(
            org_id, twin_id, body.snapshot_type, body.snapshot_period, _actor(request), db,
            sustainability_state=body.sustainability_state,
            financial_esg_state=body.financial_esg_state,
            hierarchy_state=body.hierarchy_state,
            climate_risk_state=body.climate_risk_state,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── Strategic Plans ───────────────────────────────────────────────────────────

@router.get("/{org_id}/plans", response_model=list[StrategicPlanResponse])
def list_plans(org_id: str, db: Session = Depends(get_db)):
    return planning_service.list_plans(org_id, db)


@router.post("/{org_id}/plans", response_model=StrategicPlanResponse, status_code=201)
def create_plan(org_id: str, body: StrategicPlanCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = planning_service.create_plan(
            org_id, body.title, body.planning_horizon, _actor(request), db,
            description=body.description,
            baseline_snapshot_id=body.baseline_snapshot_id,
            target_snapshot_id=body.target_snapshot_id,
            plan_owner=body.plan_owner,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/plans/{plan_id}/objectives", response_model=list[StrategicObjectiveResponse])
def list_objectives(org_id: str, plan_id: str, db: Session = Depends(get_db)):
    try:
        return planning_service.list_objectives(org_id, plan_id, db)
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/plans/{plan_id}/objectives", response_model=StrategicObjectiveResponse, status_code=201)
def create_objective(org_id: str, plan_id: str, body: StrategicObjectiveCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = planning_service.create_objective(
            org_id, plan_id, body.title, body.objective_type, _actor(request), db,
            linked_esg_objective_id=body.linked_esg_objective_id,
            linked_financial_kpi_id=body.linked_financial_kpi_id,
            linked_risk_id=body.linked_risk_id,
            current_value=body.current_value,
            target_value=body.target_value,
            confidence=body.confidence,
            unit=body.unit,
            target_year=body.target_year,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── Scenarios ─────────────────────────────────────────────────────────────────

@router.get("/{org_id}/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(org_id: str, db: Session = Depends(get_db)):
    return scenario_service.list_scenarios(org_id, db)


@router.post("/{org_id}/scenarios", response_model=ScenarioResponse, status_code=201)
def create_scenario(org_id: str, body: ScenarioCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = scenario_service.create_scenario(
            org_id, body.name, body.scenario_type, _actor(request), db,
            description=body.description,
            baseline_twin_id=body.baseline_twin_id,
            time_horizon_years=body.time_horizon_years,
            is_template=body.is_template,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/scenarios/{scenario_id}/assumptions", response_model=list[AssumptionResponse])
def list_assumptions(org_id: str, scenario_id: str, db: Session = Depends(get_db)):
    try:
        return scenario_service.list_assumptions(org_id, scenario_id, db)
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/scenarios/{scenario_id}/assumptions", response_model=AssumptionResponse, status_code=201)
def create_assumption(org_id: str, scenario_id: str, body: AssumptionCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = scenario_service.create_assumption(
            org_id, scenario_id, body.assumption_key, body.assumption_label,
            body.value, _actor(request), db,
            unit=body.unit,
            rationale=body.rationale,
            source=body.source,
            assumption_year=body.assumption_year,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/scenarios/{scenario_id}/execute", response_model=ExecutionResponse, status_code=201)
def execute_scenario(org_id: str, scenario_id: str, body: ExecutionCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = scenario_service.execute_scenario(
            org_id, scenario_id, _actor(request), db,
            twin_id=body.twin_id,
            baseline_override=body.baseline_override,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/executions", response_model=list[ExecutionResponse])
def list_executions(org_id: str, db: Session = Depends(get_db)):
    return scenario_service.list_executions(org_id, db)


# ── Stress Tests ──────────────────────────────────────────────────────────────

@router.get("/{org_id}/stress-tests/climate", response_model=list[ClimateStressTestResponse])
def list_climate_tests(org_id: str, db: Session = Depends(get_db)):
    return stress_test_service.list_climate_stress_tests(org_id, db)


@router.post("/{org_id}/stress-tests/climate", response_model=ClimateStressTestResponse, status_code=201)
def create_climate_test(org_id: str, body: ClimateStressTestCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = stress_test_service.create_climate_stress_test(
            org_id, body.test_name, body.stress_type, _actor(request), db,
            scenario_id=body.scenario_id,
            carbon_price_shock_pct=body.carbon_price_shock_pct,
            physical_risk_multiplier=body.physical_risk_multiplier,
            regulatory_intensity_score=body.regulatory_intensity_score,
            transition_cost_pct=body.transition_cost_pct,
            test_methodology=body.test_methodology,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/stress-tests/supplier-shock", response_model=list[SupplierShockResponse])
def list_supplier_shocks(org_id: str, db: Session = Depends(get_db)):
    return stress_test_service.list_supplier_shocks(org_id, db)


@router.post("/{org_id}/stress-tests/supplier-shock", response_model=SupplierShockResponse, status_code=201)
def create_supplier_shock(org_id: str, body: SupplierShockCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = stress_test_service.create_supplier_shock(
            org_id, body.scenario_name, body.shock_type, body.shock_severity, _actor(request), db,
            affected_supplier_ids=body.affected_supplier_ids,
            affected_region=body.affected_region,
            propagation_model=body.propagation_model,
            recovery_timeline_months=body.recovery_timeline_months,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/stress-tests/financial", response_model=list[FinancialStressTestResponse])
def list_financial_tests(org_id: str, db: Session = Depends(get_db)):
    return stress_test_service.list_financial_stress_tests(org_id, db)


@router.post("/{org_id}/stress-tests/financial", response_model=FinancialStressTestResponse, status_code=201)
def create_financial_test(org_id: str, body: FinancialStressTestCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = stress_test_service.create_financial_stress_test(
            org_id, body.test_name, body.stress_type, _actor(request), db,
            financing_cost_increase_bps=body.financing_cost_increase_bps,
            green_revenue_decline_pct=body.green_revenue_decline_pct,
            carbon_tax_increase_pct=body.carbon_tax_increase_pct,
            transition_delay_months=body.transition_delay_months,
            recovery_pathway=body.recovery_pathway,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── Pathways ──────────────────────────────────────────────────────────────────

@router.get("/{org_id}/pathways", response_model=list[TransitionPathwayResponse])
def list_pathways(org_id: str, db: Session = Depends(get_db)):
    return pathway_service.list_pathways(org_id, db)


@router.post("/{org_id}/pathways", response_model=TransitionPathwayResponse, status_code=201)
def create_pathway(org_id: str, body: TransitionPathwayCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = pathway_service.create_pathway(
            org_id, body.pathway_name, body.pathway_type, body.target_year, _actor(request), db,
            baseline_emissions_tco2e=body.baseline_emissions_tco2e,
            target_emissions_tco2e=body.target_emissions_tco2e,
            strategic_plan_id=body.strategic_plan_id,
            is_primary=body.is_primary,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/pathways/{pathway_id}/net-zero", response_model=list[NetZeroPathwayResponse])
def list_net_zero(org_id: str, pathway_id: str, db: Session = Depends(get_db)):
    try:
        return pathway_service.list_net_zero_pathways(org_id, pathway_id, db)
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/pathways/{pathway_id}/net-zero", response_model=NetZeroPathwayResponse, status_code=201)
def create_net_zero(org_id: str, pathway_id: str, body: NetZeroPathwayCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = pathway_service.create_net_zero_pathway(
            org_id, pathway_id, body.net_zero_year, _actor(request), db,
            interim_targets=body.interim_targets,
            assumptions=body.assumptions,
            abatement_cost=body.abatement_cost,
            methodology=body.methodology,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── Forecasts ─────────────────────────────────────────────────────────────────

@router.get("/{org_id}/forecasts/models", response_model=list[ForecastModelResponse])
def list_forecast_models(org_id: str, db: Session = Depends(get_db)):
    return forecast_service.list_forecast_models(org_id, db)


@router.post("/{org_id}/forecasts/models", response_model=ForecastModelResponse, status_code=201)
def create_forecast_model(org_id: str, body: ForecastModelCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = forecast_service.create_forecast_model(
            org_id, body.model_name, body.methodology, _actor(request), db,
            description=body.description,
            parameters=body.parameters,
            model_version=body.model_version,
            methodology_record_id=body.methodology_record_id,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.get("/{org_id}/forecasts/results", response_model=list[ForecastResultResponse])
def list_forecast_results(org_id: str, db: Session = Depends(get_db)):
    return forecast_service.list_forecast_results(org_id, db)


@router.post("/{org_id}/forecasts/run", response_model=ForecastResultResponse, status_code=201)
def run_forecast(org_id: str, body: ForecastRunCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = forecast_service.run_forecast(
            org_id, body.forecast_model_id, body.forecast_type, body.target_metric,
            body.forecast_year, body.baseline_value, _actor(request), db,
            scenario_id=body.scenario_id,
            parameter_overrides=body.parameter_overrides,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── Board Simulation ──────────────────────────────────────────────────────────

@router.get("/{org_id}/board-simulations", response_model=list[BoardSimulationResponse])
def list_board_simulations(org_id: str, db: Session = Depends(get_db)):
    return board_simulation_service.list_board_simulations(org_id, db)


@router.post("/{org_id}/board-simulations", response_model=BoardSimulationResponse, status_code=201)
def create_board_simulation(org_id: str, body: BoardSimulationCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = board_simulation_service.create_board_simulation(
            org_id, body.simulation_name, _actor(request), db,
            scenario_a_id=body.scenario_a_id,
            scenario_b_id=body.scenario_b_id,
            scenario_c_id=body.scenario_c_id,
            recommendation=body.recommendation,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/{org_id}/reports", response_model=list[StrategicReportResponse])
def list_reports(org_id: str, db: Session = Depends(get_db)):
    return reporting_service.list_reports(org_id, db)


@router.post("/{org_id}/reports", response_model=StrategicReportResponse, status_code=201)
def generate_report(org_id: str, body: StrategicReportCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = reporting_service.generate_strategic_report(
            org_id, body.report_title, body.report_period, _actor(request), db,
            included_scenario_ids=body.included_scenario_ids,
            board_comparison=body.board_comparison,
            report_methodology=body.report_methodology,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/reports/{report_id}/finalize", response_model=StrategicReportResponse)
def finalize_report(org_id: str, report_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        rec = reporting_service.finalize_report(org_id, report_id, _actor(request), db)
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── Rollup ────────────────────────────────────────────────────────────────────

@router.get("/{org_id}/rollup", response_model=StrategyRollupResponse)
def strategy_rollup(org_id: str, db: Session = Depends(get_db)):
    return rollup_service.strategy_rollup(org_id, db)


# ── M44.1: Scenario Templates ─────────────────────────────────────────────────

@router.get("/{org_id}/templates/scenarios", response_model=list[ScenarioTemplateResponse])
def list_scenario_templates(org_id: str, db: Session = Depends(get_db)):
    return template_service.list_scenario_templates(org_id, db)


@router.post("/{org_id}/templates/scenarios", response_model=ScenarioTemplateResponse, status_code=201)
def create_scenario_template(org_id: str, body: ScenarioTemplateCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = template_service.create_scenario_template(
            org_id, body.template_name, body.template_type, body.scenario_type, _actor(request), db,
            description=body.description,
            default_assumptions=body.default_assumptions,
            default_time_horizon_years=body.default_time_horizon_years,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/templates/scenarios/{template_id}/instantiate", response_model=ScenarioResponse, status_code=201)
def instantiate_scenario_from_template(
    org_id: str, template_id: str, body: TemplateInstantiateCreate,
    request: Request, db: Session = Depends(get_db)
):
    try:
        rec = template_service.instantiate_from_template(
            org_id, template_id, body.scenario_name, _actor(request), db,
            assumption_overrides=body.assumption_overrides,
            time_horizon_years=body.time_horizon_years,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── M44.1: Stress Test Templates ─────────────────────────────────────────────

@router.get("/{org_id}/templates/stress-tests", response_model=list[StressTestTemplateResponse])
def list_stress_test_templates(org_id: str, db: Session = Depends(get_db)):
    return template_service.list_stress_test_templates(org_id, db)


@router.post("/{org_id}/templates/stress-tests", response_model=StressTestTemplateResponse, status_code=201)
def create_stress_test_template(org_id: str, body: StressTestTemplateCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = template_service.create_stress_test_template(
            org_id, body.template_name, body.template_type, _actor(request), db,
            default_assumptions=body.default_assumptions,
            methodology=body.methodology,
            severity_level=body.severity_level,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── M44.1: Strategy Methodologies ─────────────────────────────────────────────

@router.get("/{org_id}/methodologies", response_model=list[StrategyMethodologyResponse])
def list_methodologies(org_id: str, db: Session = Depends(get_db)):
    return methodology_service.list_methodologies(org_id, db)


@router.post("/{org_id}/methodologies", response_model=StrategyMethodologyResponse, status_code=201)
def create_methodology(org_id: str, body: StrategyMethodologyCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = methodology_service.create_methodology(
            org_id, body.methodology_name, _actor(request), db,
            methodology_version=body.methodology_version,
            formula_description=body.formula_description,
            assumptions=body.assumptions,
            applicable_to=body.applicable_to,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/methodologies/{methodology_id}/approve", response_model=StrategyMethodologyResponse)
def approve_methodology(org_id: str, methodology_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        rec = methodology_service.approve_methodology(org_id, methodology_id, _actor(request), db)
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


@router.post("/{org_id}/methodologies/{methodology_id}/deprecate", response_model=StrategyMethodologyResponse)
def deprecate_methodology(org_id: str, methodology_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        rec = methodology_service.deprecate_methodology(org_id, methodology_id, _actor(request), db)
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── M44.1: Scenario Comparisons ───────────────────────────────────────────────

@router.get("/{org_id}/comparisons", response_model=list[ScenarioComparisonResponse])
def list_comparisons(org_id: str, db: Session = Depends(get_db)):
    return comparison_service.list_comparisons(org_id, db)


@router.post("/{org_id}/comparisons", response_model=ScenarioComparisonResponse, status_code=201)
def create_comparison(org_id: str, body: ScenarioComparisonCreate, request: Request, db: Session = Depends(get_db)):
    try:
        rec = comparison_service.compare_scenarios(
            org_id, body.comparison_name, body.scenario_ids, _actor(request), db,
            comparison_methodology=body.comparison_methodology,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)


# ── M44.1: Forecast Window Policies ───────────────────────────────────────────

@router.get("/{org_id}/forecast-window-policies", response_model=list[ForecastWindowPolicyResponse])
def list_forecast_window_policies(org_id: str, db: Session = Depends(get_db)):
    return forecast_service.list_forecast_window_policies(org_id, db)


@router.post("/{org_id}/forecast-window-policies", response_model=ForecastWindowPolicyResponse, status_code=201)
def create_forecast_window_policy(
    org_id: str, body: ForecastWindowPolicyCreate, request: Request, db: Session = Depends(get_db)
):
    try:
        rec = forecast_service.create_forecast_window_policy(
            org_id, body.policy_name, body.min_window, body.max_window,
            body.default_window, _actor(request), db,
            applicable_methodology=body.applicable_methodology,
        )
        db.commit()
        db.refresh(rec)
        return rec
    except StrategyError as e:
        raise _err(e)
