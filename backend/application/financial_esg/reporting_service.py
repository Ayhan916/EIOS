"""M43 — Financial ESG Reporting, Scenario Analysis, ESG-Financial Correlation.

Reports are immutable once finalized (is_final=True).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.financial_esg.kpi_service import (
    FinancialESGConflict,
    FinancialESGError,
    _assert_org,
    _now,
)
from application.financial_esg.metrics import financial_esg_counters
from infrastructure.persistence.models.financial_esg import (
    SCENARIO_TYPES_FIN,
    CapitalMarketsAssessmentModel,
    CarbonCostModelRecord,
    ESGFinancialCorrelationModel,
    FinancialESGReportModel,
    FinancialScenarioAnalysisModel,
    GreenRevenueRecordModel,
    SustainableFinanceInstrumentModel,
    TaxonomyAlignmentAssessmentModel,
    ValueCreationInitiativeModel,
)

# ── Financial ESG Reports ─────────────────────────────────────────────────────


def generate_financial_esg_report(
    organization_id: str,
    title: str,
    report_period_start: datetime,
    report_period_end: datetime,
    actor_id: str,
    session: Session,
) -> FinancialESGReportModel:
    # Build snapshots from current org data
    value_snap = _value_creation_snapshot(organization_id, session)
    carbon_snap = _carbon_economics_snapshot(organization_id, session)
    taxonomy_snap = _taxonomy_snapshot(organization_id, session)
    revenue_snap = _green_revenue_snapshot(organization_id, session)
    finance_snap = _sustainable_finance_snapshot(organization_id, session)
    readiness_snap = _readiness_snapshot(organization_id, session)

    now = _now()
    report = FinancialESGReportModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        title=title,
        report_period_start=report_period_start,
        report_period_end=report_period_end,
        value_creation_snapshot=value_snap,
        carbon_economics_snapshot=carbon_snap,
        taxonomy_snapshot=taxonomy_snap,
        green_revenue_snapshot=revenue_snap,
        sustainable_finance_snapshot=finance_snap,
        readiness_snapshot=readiness_snap,
        overall_status="DRAFT",
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(report)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.report.generated",
        actor_id=actor_id,
        resource_type="financial_esg_report",
        resource_id=report.id,
        details={"title": title},
    )
    financial_esg_counters.record_report_generated()
    return report


def finalize_financial_esg_report(
    report_id: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> FinancialESGReportModel:
    report = session.get(FinancialESGReportModel, report_id)
    _assert_org(report, organization_id, "Financial ESG report")
    if report.is_final:
        raise FinancialESGConflict("Report is already finalized")
    report.is_final = True
    report.overall_status = "FINAL"
    report.finalized_at = _now()
    report.updated_by = actor_id
    report.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.report.finalized",
        actor_id=actor_id,
        resource_type="financial_esg_report",
        resource_id=report_id,
        details={"finalized_at": report.finalized_at.isoformat()},
    )
    financial_esg_counters.record_report_finalized()
    return report


def list_financial_esg_reports(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[FinancialESGReportModel]:
    return (
        session.query(FinancialESGReportModel)
        .filter(FinancialESGReportModel.organization_id == organization_id)
        .order_by(FinancialESGReportModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── Snapshot helpers ──────────────────────────────────────────────────────────


def _value_creation_snapshot(org_id: str, session: Session) -> dict:
    rows = (
        session.query(ValueCreationInitiativeModel)
        .filter(ValueCreationInitiativeModel.organization_id == org_id)
        .all()
    )
    total_investment = sum(r.investment_amount for r in rows)
    total_realized = sum(r.realized_value for r in rows)
    return {
        "total_initiatives": len(rows),
        "total_investment": total_investment,
        "total_realized_value": total_realized,
        "avg_roi_percent": (
            round(sum(r.roi_percent for r in rows if r.roi_percent is not None) / len(rows), 2)
            if rows
            else None
        ),
    }


def _carbon_economics_snapshot(org_id: str, session: Session) -> dict:
    rows = (
        session.query(CarbonCostModelRecord)
        .filter(CarbonCostModelRecord.organization_id == org_id)
        .all()
    )
    return {
        "total_carbon_cost_models": len(rows),
        "total_carbon_cost": sum(r.total_carbon_cost for r in rows),
        "total_regulatory_exposure": sum(r.regulatory_exposure for r in rows),
        "total_avoided_cost": sum(r.avoided_cost for r in rows),
    }


def _taxonomy_snapshot(org_id: str, session: Session) -> dict:
    latest = (
        session.query(TaxonomyAlignmentAssessmentModel)
        .filter(TaxonomyAlignmentAssessmentModel.organization_id == org_id)
        .order_by(TaxonomyAlignmentAssessmentModel.assessment_year.desc())
        .first()
    )
    if not latest:
        return {"aligned_percent": None, "eligible_percent": None}
    return {
        "assessment_year": latest.assessment_year,
        "aligned_percent": latest.aligned_percent,
        "eligible_percent": latest.eligible_percent,
        "taxonomy_framework": latest.taxonomy_framework,
    }


def _green_revenue_snapshot(org_id: str, session: Session) -> dict:
    rows = (
        session.query(GreenRevenueRecordModel)
        .filter(GreenRevenueRecordModel.organization_id == org_id)
        .all()
    )
    total_green = sum(r.amount for r in rows if r.alignment_status in ("ALIGNED", "ELIGIBLE"))
    total_rev = rows[0].total_revenue if rows else 0.0
    return {
        "records_count": len(rows),
        "total_green_amount": total_green,
        "total_revenue": total_rev,
        "green_revenue_percent": round(total_green / total_rev * 100, 4) if total_rev > 0 else 0.0,
    }


def _sustainable_finance_snapshot(org_id: str, session: Session) -> dict:
    rows = (
        session.query(SustainableFinanceInstrumentModel)
        .filter(SustainableFinanceInstrumentModel.organization_id == org_id)
        .all()
    )
    return {
        "total_instruments": len(rows),
        "total_exposure": sum(r.amount for r in rows),
        "breached_count": sum(1 for r in rows if r.covenant_status == "BREACHED"),
        "compliant_count": sum(1 for r in rows if r.covenant_status == "COMPLIANT"),
    }


def _readiness_snapshot(org_id: str, session: Session) -> dict:
    latest = (
        session.query(CapitalMarketsAssessmentModel)
        .filter(CapitalMarketsAssessmentModel.organization_id == org_id)
        .order_by(CapitalMarketsAssessmentModel.assessed_at.desc())
        .first()
    )
    if not latest:
        return {"overall_readiness": "NOT_READY"}
    return {
        "overall_readiness": latest.overall_readiness,
        "disclosure_readiness": latest.disclosure_readiness,
        "taxonomy_readiness": latest.taxonomy_readiness,
    }


# ── Scenario Analysis ─────────────────────────────────────────────────────────


def create_scenario_analysis(
    organization_id: str,
    scenario_name: str,
    scenario_type: str,
    inputs: dict,
    assumptions: dict,
    actor_id: str,
    session: Session,
    *,
    notes: str | None = None,
) -> FinancialScenarioAnalysisModel:
    if scenario_type not in SCENARIO_TYPES_FIN:
        raise FinancialESGError(f"Invalid scenario_type: {scenario_type}")
    outputs = _run_scenario(scenario_type, inputs, assumptions)
    now = _now()
    rec = FinancialScenarioAnalysisModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        scenario_name=scenario_name,
        scenario_type=scenario_type,
        inputs=inputs,
        assumptions=assumptions,
        outputs=outputs,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.scenario.created",
        actor_id=actor_id,
        resource_type="financial_scenario_analysis",
        resource_id=rec.id,
        details={"scenario_type": scenario_type, "scenario_name": scenario_name},
    )
    return rec


def _run_scenario(scenario_type: str, inputs: dict, assumptions: dict) -> dict:
    """Deterministic scenario outputs derived from inputs and assumptions."""
    if scenario_type == "CARBON_PRICE_INCREASE":
        base_price = float(inputs.get("current_carbon_price", 0))
        price_increase_pct = float(assumptions.get("price_increase_percent", 0))
        emissions = float(inputs.get("total_emissions", 0))
        new_price = round(base_price * (1 + price_increase_pct / 100), 4)
        additional_cost = round(emissions * (new_price - base_price), 6)
        return {
            "new_carbon_price": new_price,
            "additional_annual_cost": additional_cost,
            "formula": "emissions × (new_price - base_price)",
        }
    elif scenario_type == "SUPPLIER_DISRUPTION":
        exposure = float(inputs.get("supplier_exposure", 0))
        disruption_pct = float(assumptions.get("disruption_probability_percent", 0))
        impact_pct = float(assumptions.get("revenue_impact_percent", 0))
        expected_impact = round(exposure * (disruption_pct / 100) * (impact_pct / 100), 6)
        return {
            "expected_financial_impact": expected_impact,
            "formula": "supplier_exposure × disruption_probability × revenue_impact",
        }
    elif scenario_type == "CLIMATE_REGULATION":
        compliance_cost = float(inputs.get("estimated_compliance_cost", 0))
        penalty_risk = float(inputs.get("penalty_risk", 0))
        probability = float(assumptions.get("regulation_probability_percent", 50))
        expected_cost = round((compliance_cost + penalty_risk) * (probability / 100), 6)
        return {
            "expected_regulatory_cost": expected_cost,
            "formula": "(compliance_cost + penalty_risk) × regulation_probability",
        }
    elif scenario_type == "ACCELERATED_TRANSITION":
        capex = float(inputs.get("transition_capex", 0))
        opex_savings = float(inputs.get("annual_opex_savings", 0))
        years = int(assumptions.get("time_horizon_years", 5))
        total_savings = round(opex_savings * years, 6)
        net_benefit = round(total_savings - capex, 6)
        return {
            "total_savings": total_savings,
            "net_benefit": net_benefit,
            "formula": "(annual_opex_savings × years) - transition_capex",
        }
    return {"computed": True, "scenario_type": scenario_type}


def list_scenario_analyses(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[FinancialScenarioAnalysisModel]:
    return (
        session.query(FinancialScenarioAnalysisModel)
        .filter(FinancialScenarioAnalysisModel.organization_id == organization_id)
        .order_by(FinancialScenarioAnalysisModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ── ESG Financial Correlation ─────────────────────────────────────────────────


def create_esg_correlation(
    organization_id: str,
    esg_score: float,
    risk_reduction: float,
    cost_reduction: float,
    financial_performance: float,
    correlation_period: str,
    actor_id: str,
    session: Session,
    *,
    scorecard_id: str | None = None,
    methodology: str | None = None,
    assumptions: dict | None = None,
) -> ESGFinancialCorrelationModel:
    # Pearson-style simple linear correlation proxy
    # r = (ESG - baseline_esg) / 100 × weighted_financial_avg
    # Stored as an explainable coefficient, not AI-generated
    weighted_fin = round(
        risk_reduction * 0.4 + cost_reduction * 0.3 + financial_performance * 0.3, 4
    )
    coefficient = round(
        esg_score / 100.0 * (1 if weighted_fin >= 0 else -1) * min(abs(weighted_fin) / 100.0, 1.0),
        6,
    )

    now = _now()
    rec = ESGFinancialCorrelationModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        scorecard_id=scorecard_id,
        correlation_period=correlation_period,
        esg_score=esg_score,
        risk_reduction=risk_reduction,
        cost_reduction=cost_reduction,
        financial_performance=financial_performance,
        correlation_coefficient=coefficient,
        methodology=methodology or "weighted_financial_avg: risk×0.4 + cost×0.3 + financial×0.3",
        assumptions=assumptions or {},
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="financial_esg.correlation.created",
        actor_id=actor_id,
        resource_type="esg_financial_correlation",
        resource_id=rec.id,
        details={"correlation_coefficient": coefficient, "esg_score": esg_score},
    )
    return rec


def list_correlations(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ESGFinancialCorrelationModel]:
    return (
        session.query(ESGFinancialCorrelationModel)
        .filter(ESGFinancialCorrelationModel.organization_id == organization_id)
        .order_by(ESGFinancialCorrelationModel.correlation_period.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
