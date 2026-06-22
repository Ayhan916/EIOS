"""M44 — Enterprise Strategy Rollup service.

Aggregates scenario executions, forecasts, and stress tests
per organization. All SQL, deterministic, no N+1.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from infrastructure.persistence.models.strategy import (
    BoardSimulationModel,
    ClimateStressTestModel,
    EnterpriseDigitalTwinModel,
    FinancialStressTestModel,
    ForecastResultModel,
    ScenarioComparisonModel,
    ScenarioExecutionModel,
    ScenarioTemplateModel,
    StrategyMethodologyModel,
    StrategyScenarioModel,
    StrategicScenarioReportModel,
    StressTestTemplateModel,
    TransitionPathwayModel,
)


def strategy_rollup(organization_id: str, session: Session) -> dict:
    """Single-pass aggregation — no N+1 queries."""

    twin_count = (
        session.query(func.count(EnterpriseDigitalTwinModel.id))
        .filter(EnterpriseDigitalTwinModel.organization_id == organization_id)
        .scalar()
    ) or 0

    scenario_count = (
        session.query(func.count(StrategyScenarioModel.id))
        .filter(StrategyScenarioModel.organization_id == organization_id)
        .scalar()
    ) or 0

    execution_count = (
        session.query(func.count(ScenarioExecutionModel.id))
        .filter(ScenarioExecutionModel.organization_id == organization_id)
        .scalar()
    ) or 0

    climate_test_count = (
        session.query(func.count(ClimateStressTestModel.id))
        .filter(ClimateStressTestModel.organization_id == organization_id)
        .scalar()
    ) or 0

    financial_test_count = (
        session.query(func.count(FinancialStressTestModel.id))
        .filter(FinancialStressTestModel.organization_id == organization_id)
        .scalar()
    ) or 0

    forecast_count = (
        session.query(func.count(ForecastResultModel.id))
        .filter(ForecastResultModel.organization_id == organization_id)
        .scalar()
    ) or 0

    board_sim_count = (
        session.query(func.count(BoardSimulationModel.id))
        .filter(BoardSimulationModel.organization_id == organization_id)
        .scalar()
    ) or 0

    pathway_count = (
        session.query(func.count(TransitionPathwayModel.id))
        .filter(TransitionPathwayModel.organization_id == organization_id)
        .scalar()
    ) or 0

    finalized_reports = (
        session.query(func.count(StrategicScenarioReportModel.id))
        .filter(
            StrategicScenarioReportModel.organization_id == organization_id,
            StrategicScenarioReportModel.is_final.is_(True),
        )
        .scalar()
    ) or 0

    avg_forecast_value = (
        session.query(func.avg(ForecastResultModel.forecast_value))
        .filter(ForecastResultModel.organization_id == organization_id)
        .scalar()
    )

    avg_forecast_emissions = (
        session.query(func.avg(ForecastResultModel.forecast_value))
        .filter(
            ForecastResultModel.organization_id == organization_id,
            ForecastResultModel.forecast_type == "EMISSIONS",
        )
        .scalar()
    )

    avg_pathway_reduction_pct = (
        session.query(func.avg(TransitionPathwayModel.reduction_pct))
        .filter(TransitionPathwayModel.organization_id == organization_id)
        .scalar()
    )

    scenario_template_count = (
        session.query(func.count(ScenarioTemplateModel.id))
        .filter(ScenarioTemplateModel.organization_id == organization_id)
        .scalar()
    ) or 0

    stress_test_template_count = (
        session.query(func.count(StressTestTemplateModel.id))
        .filter(StressTestTemplateModel.organization_id == organization_id)
        .scalar()
    ) or 0

    methodology_count = (
        session.query(func.count(StrategyMethodologyModel.id))
        .filter(StrategyMethodologyModel.organization_id == organization_id)
        .scalar()
    ) or 0

    comparison_count = (
        session.query(func.count(ScenarioComparisonModel.id))
        .filter(ScenarioComparisonModel.organization_id == organization_id)
        .scalar()
    ) or 0

    return {
        "organization_id": organization_id,
        "digital_twins": twin_count,
        "scenarios": scenario_count,
        "scenario_executions": execution_count,
        "climate_stress_tests": climate_test_count,
        "financial_stress_tests": financial_test_count,
        "total_stress_tests": climate_test_count + financial_test_count,
        "forecasts": forecast_count,
        "board_simulations": board_sim_count,
        "transition_pathways": pathway_count,
        "finalized_reports": finalized_reports,
        "avg_forecast_value": round(float(avg_forecast_value), 4) if avg_forecast_value else None,
        "avg_forecast_emissions": round(float(avg_forecast_emissions), 4) if avg_forecast_emissions else None,
        "avg_pathway_reduction_pct": round(float(avg_pathway_reduction_pct), 4) if avg_pathway_reduction_pct else None,
        "scenario_templates": scenario_template_count,
        "stress_test_templates": stress_test_template_count,
        "strategy_methodologies": methodology_count,
        "scenario_comparisons": comparison_count,
    }
