"""M44 — Strategic Scenario Reporting service.

Reports are immutable once finalized (is_final=True).
Snapshots of assumptions, forecasts, stress tests, and pathways
are captured at generation time and stored in the report record.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.digital_twin_service import StrategyError
from application.strategy.metrics import strategy_counters
from infrastructure.persistence.models.strategy import (
    ClimateStressTestModel,
    FinancialStressTestModel,
    ForecastMethodologyRecordModel,
    ForecastResultModel,
    ScenarioAssumptionModel,
    StrategicForecastSummaryModel,
    StrategicScenarioReportModel,
    StrategyMethodologyModel,
    TransitionPathwayModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _assumptions_snapshot(organization_id: str, scenario_ids: list[str], session: Session) -> dict:
    rows = (
        session.query(ScenarioAssumptionModel)
        .filter(
            ScenarioAssumptionModel.organization_id == organization_id,
            ScenarioAssumptionModel.scenario_id.in_(scenario_ids),
        )
        .all()
    )
    return {
        "assumptions": [
            {
                "scenario_id": r.scenario_id,
                "assumption_key": r.assumption_key,
                "assumption_label": r.assumption_label,
                "value": r.value,
                "unit": r.unit,
                "source": r.source,
            }
            for r in rows
        ]
    }


def _forecasts_snapshot(organization_id: str, session: Session) -> dict:
    rows = (
        session.query(ForecastResultModel)
        .filter(ForecastResultModel.organization_id == organization_id)
        .order_by(ForecastResultModel.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "forecasts": [
            {
                "forecast_type": r.forecast_type,
                "target_metric": r.target_metric,
                "forecast_year": r.forecast_year,
                "baseline_value": r.baseline_value,
                "forecast_value": r.forecast_value,
                "confidence_level": r.confidence_level,
            }
            for r in rows
        ]
    }


def _stress_tests_snapshot(organization_id: str, session: Session) -> dict:
    climate = (
        session.query(ClimateStressTestModel)
        .filter(ClimateStressTestModel.organization_id == organization_id)
        .order_by(ClimateStressTestModel.created_at.desc())
        .limit(20)
        .all()
    )
    financial = (
        session.query(FinancialStressTestModel)
        .filter(FinancialStressTestModel.organization_id == organization_id)
        .order_by(FinancialStressTestModel.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "climate_stress_tests": [
            {"test_name": t.test_name, "stress_type": t.stress_type, "risk_impact": t.risk_impact}
            for t in climate
        ],
        "financial_stress_tests": [
            {
                "test_name": t.test_name,
                "stress_type": t.stress_type,
                "financial_impact": t.financial_impact,
            }
            for t in financial
        ],
    }


def _pathway_outcomes_snapshot(organization_id: str, session: Session) -> dict:
    rows = (
        session.query(TransitionPathwayModel)
        .filter(TransitionPathwayModel.organization_id == organization_id)
        .order_by(TransitionPathwayModel.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "pathways": [
            {
                "pathway_name": r.pathway_name,
                "pathway_type": r.pathway_type,
                "target_year": r.target_year,
                "reduction_pct": r.reduction_pct,
            }
            for r in rows
        ]
    }


def _methodology_appendix(organization_id: str, session: Session) -> dict:
    methodology_records = (
        session.query(ForecastMethodologyRecordModel)
        .filter(ForecastMethodologyRecordModel.organization_id == organization_id)
        .order_by(ForecastMethodologyRecordModel.created_at.desc())
        .limit(10)
        .all()
    )
    strategy_methodologies = (
        session.query(StrategyMethodologyModel)
        .filter(
            StrategyMethodologyModel.organization_id == organization_id,
            StrategyMethodologyModel.approval_status == "APPROVED",
        )
        .order_by(StrategyMethodologyModel.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "forecast_methodologies": [
            {
                "name": m.methodology_name,
                "version": m.methodology_version,
                "algorithm_type": m.algorithm_type,
                "is_approved": m.is_approved,
                "explainability_notes": m.explainability_notes,
            }
            for m in methodology_records
        ],
        "strategy_methodologies": [
            {
                "name": m.methodology_name,
                "version": m.methodology_version,
                "formula_description": m.formula_description,
                "applicable_to": m.applicable_to,
                "approval_status": m.approval_status,
            }
            for m in strategy_methodologies
        ],
    }


def _assumption_appendix(organization_id: str, scenario_ids: list[str], session: Session) -> dict:
    rows = (
        (
            session.query(ScenarioAssumptionModel)
            .filter(
                ScenarioAssumptionModel.organization_id == organization_id,
                ScenarioAssumptionModel.scenario_id.in_(scenario_ids) if scenario_ids else False,
            )
            .all()
        )
        if scenario_ids
        else []
    )
    return {
        "total_assumptions": len(rows),
        "assumptions_by_key": {
            r.assumption_key: {
                "label": r.assumption_label,
                "value": r.value,
                "unit": r.unit,
                "source": r.source,
                "rationale": r.rationale,
            }
            for r in rows
        },
    }


def generate_strategic_report(
    organization_id: str,
    report_title: str,
    report_period: str,
    actor_id: str,
    session: Session,
    *,
    included_scenario_ids: list[str] | None = None,
    board_comparison: dict | None = None,
    report_methodology: str | None = None,
) -> StrategicScenarioReportModel:
    scenario_ids = included_scenario_ids or []

    assumptions_snap = _assumptions_snapshot(organization_id, scenario_ids, session)
    forecasts_snap = _forecasts_snapshot(organization_id, session)
    stress_snap = _stress_tests_snapshot(organization_id, session)
    pathway_snap = _pathway_outcomes_snapshot(organization_id, session)
    methodology_app = _methodology_appendix(organization_id, session)
    assumption_app = _assumption_appendix(organization_id, scenario_ids, session)

    now = _now()
    report = StrategicScenarioReportModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        report_title=report_title,
        report_period=report_period,
        included_scenarios={"scenario_ids": scenario_ids},
        assumptions_snapshot=assumptions_snap,
        forecasts_snapshot=forecasts_snap,
        stress_tests_snapshot=stress_snap,
        pathway_outcomes=pathway_snap,
        board_comparison=board_comparison,
        report_methodology=report_methodology or "deterministic_snapshot",
        methodology_appendix=methodology_app,
        assumption_appendix=assumption_app,
        sensitivity_analysis=None,
        comparison_summary=None,
        is_final=False,
        finalized_at=None,
        finalized_by=None,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(report)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.report.generated",
        actor_id=actor_id,
        resource_type="strategic_scenario_report",
        resource_id=report.id,
        details={"report_title": report_title, "report_period": report_period},
    )
    strategy_counters.record_strategic_report()
    return report


def finalize_report(
    organization_id: str,
    report_id: str,
    actor_id: str,
    session: Session,
) -> StrategicScenarioReportModel:
    report = session.get(StrategicScenarioReportModel, report_id)
    if report is None or report.organization_id != organization_id:
        raise StrategyError("strategic scenario report not found")
    if report.is_final:
        raise StrategyError("Report is already finalized")
    now = _now()
    report.is_final = True
    report.finalized_at = now
    report.finalized_by = actor_id
    report.updated_at = now
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.report.finalized",
        actor_id=actor_id,
        resource_type="strategic_scenario_report",
        resource_id=report.id,
        details={"report_title": report.report_title},
    )
    strategy_counters.record_strategic_report_finalized()
    return report


def generate_forecast_summary(
    organization_id: str,
    summary_period: str,
    actor_id: str,
    session: Session,
) -> StrategicForecastSummaryModel:
    """Aggregate the latest forecast results into an executive summary."""

    rows = (
        session.query(ForecastResultModel)
        .filter(ForecastResultModel.organization_id == organization_id)
        .all()
    )

    def _avg_by_type(ftype: str) -> float | None:
        vals = [
            r.forecast_value
            for r in rows
            if r.forecast_type == ftype and r.forecast_value is not None
        ]
        return round(sum(vals) / len(vals), 4) if vals else None

    esg = _avg_by_type("KPI")
    emissions = _avg_by_type("EMISSIONS")
    green_rev = _avg_by_type("GREEN_REVENUE")
    taxonomy = _avg_by_type("TAXONOMY")

    # Trend direction: compare forecast vs baseline for emissions
    trend_direction: str | None = None
    forecast_delta: float | None = None
    scenario_confidence: float | None = None

    emission_rows = [
        r for r in rows if r.forecast_type == "EMISSIONS" and r.forecast_value is not None
    ]
    if emission_rows:
        avg_baseline = sum(
            r.baseline_value for r in emission_rows if r.baseline_value is not None
        ) / max(len(emission_rows), 1)
        avg_forecast = sum(r.forecast_value for r in emission_rows) / len(emission_rows)
        if avg_baseline and avg_baseline != 0:
            delta = (avg_forecast - avg_baseline) / abs(avg_baseline) * 100
            forecast_delta = round(delta, 4)
            trend_direction = (
                "IMPROVING" if delta < -2 else ("DECLINING" if delta > 2 else "STABLE")
            )

    conf_vals = [r.confidence_level for r in rows if r.confidence_level is not None]
    if conf_vals:
        scenario_confidence = round(sum(conf_vals) / len(conf_vals), 4)

    now = _now()
    summary = StrategicForecastSummaryModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        summary_period=summary_period,
        forecast_esg_score=esg,
        forecast_emissions_tco2e=emissions,
        forecast_green_revenue=green_rev,
        forecast_risk_exposure=None,
        forecast_value_creation=None,
        forecast_taxonomy_alignment_pct=taxonomy,
        data_sources={"forecast_count": len(rows), "methodology": "average_by_type"},
        generated_at=now,
        trend_direction=trend_direction,
        forecast_delta=forecast_delta,
        pathway_progress_pct=None,
        scenario_confidence=scenario_confidence,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(summary)
    session.flush()
    return summary


def list_reports(organization_id: str, session: Session) -> list[StrategicScenarioReportModel]:
    return (
        session.query(StrategicScenarioReportModel)
        .filter(StrategicScenarioReportModel.organization_id == organization_id)
        .order_by(StrategicScenarioReportModel.created_at.desc())
        .all()
    )
