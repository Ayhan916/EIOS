"""M44 — Climate, Supplier, and Financial Stress Testing services.

All calculations are deterministic, explainable, and formula-based.
No ML or LLM involved.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.metrics import strategy_counters
from application.strategy.digital_twin_service import StrategyError
from infrastructure.persistence.models.strategy import (
    CLIMATE_STRESS_TYPES,
    FINANCIAL_STRESS_TYPES,
    PROPAGATION_MODELS,
    SUPPLIER_SHOCK_TYPES,
    ClimateStressTestModel,
    FinancialStressTestModel,
    SupplierShockScenarioModel,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Deterministic stress calculation formulas ─────────────────────────────────

def _compute_climate_impacts(
    stress_type: str,
    carbon_price_shock_pct: float,
    physical_risk_multiplier: float,
    regulatory_intensity_score: float,
    transition_cost_pct: float,
) -> tuple[dict, dict, dict]:
    """
    Deterministic linear sensitivity formulas per stress type.

    TRANSITION_SHOCK:
      risk_impact_pct  = carbon_price * 0.15 + transition_cost * 0.10
      emissions_change = -carbon_price * 0.05  (higher price → lower emissions)
      fin_cost_pct     = transition_cost * 0.20

    PHYSICAL_RISK:
      risk_impact_pct  = multiplier * 15
      emissions_change = multiplier * 2
      fin_cost_pct     = multiplier * 8

    CARBON_PRICE:
      risk_impact_pct  = carbon_price * 0.20
      emissions_change = -carbon_price * 0.08
      fin_cost_pct     = carbon_price * 0.12

    REGULATORY:
      risk_impact_pct  = intensity * 10
      emissions_change = -intensity * 3
      fin_cost_pct     = intensity * 6
    """
    cp = carbon_price_shock_pct or 0.0
    pr = physical_risk_multiplier or 0.0
    ri = regulatory_intensity_score or 0.0
    tc = transition_cost_pct or 0.0

    if stress_type == "TRANSITION_SHOCK":
        risk_pct = cp * 0.15 + tc * 0.10
        em_change_pct = -cp * 0.05
        fin_cost_pct = tc * 0.20
    elif stress_type == "PHYSICAL_RISK":
        risk_pct = pr * 15.0
        em_change_pct = pr * 2.0
        fin_cost_pct = pr * 8.0
    elif stress_type == "CARBON_PRICE":
        risk_pct = cp * 0.20
        em_change_pct = -cp * 0.08
        fin_cost_pct = cp * 0.12
    elif stress_type == "REGULATORY":
        risk_pct = ri * 10.0
        em_change_pct = -ri * 3.0
        fin_cost_pct = ri * 6.0
    else:
        risk_pct = em_change_pct = fin_cost_pct = 0.0

    risk_impact = {
        "total_risk_increase_pct": round(risk_pct, 4),
        "methodology": "linear_sensitivity",
    }
    emissions_impact = {
        "emissions_change_pct": round(em_change_pct, 4),
        "methodology": "linear_sensitivity",
    }
    financial_impact = {
        "financial_cost_pct": round(fin_cost_pct, 4),
        "methodology": "linear_sensitivity",
    }
    return risk_impact, emissions_impact, financial_impact


def _compute_supplier_impacts(
    shock_severity: float,
    propagation_model: str,
) -> tuple[dict, dict, dict]:
    """
    Deterministic supplier shock propagation:

    LINEAR:  financial_impact_pct = severity * 15
    NETWORK: financial_impact_pct = severity * 15 * 1.5  (network amplification)
    supply_disruption_pct = severity * 100
    esg_score_impact      = severity * 3.0
    """
    sev = max(0.0, min(1.0, shock_severity))
    disruption_pct = round(sev * 100, 4)
    esg_impact = round(sev * 3.0, 4)

    if propagation_model == "NETWORK":
        fin_pct = round(sev * 15.0 * 1.5, 4)
    else:
        fin_pct = round(sev * 15.0, 4)

    supply_chain_impact = {
        "supply_disruption_pct": disruption_pct,
        "propagation_model": propagation_model,
    }
    financial_impact = {
        "financial_impact_pct": fin_pct,
        "methodology": "severity_linear" if propagation_model == "LINEAR" else "network_amplified",
    }
    esg_impact_out = {
        "esg_score_degradation": esg_impact,
    }
    return supply_chain_impact, financial_impact, esg_impact_out


def _compute_financial_stress_impacts(
    stress_type: str,
    financing_cost_increase_bps: float,
    green_revenue_decline_pct: float,
    carbon_tax_increase_pct: float,
    transition_delay_months: int,
) -> tuple[dict, dict]:
    """
    Deterministic financial stress formulas:

    FINANCING_COST:    cost_increase_pct = bps / 100
    GREEN_REVENUE:     revenue_impact_pct = -decline_pct
    CARBON_TAX:        cost_increase_pct = carbon_tax_pct * 0.5
    TRANSITION_DELAY:  cost_pct = delay_months * 2.0
    """
    fcb = financing_cost_increase_bps or 0.0
    grd = green_revenue_decline_pct or 0.0
    ctax = carbon_tax_increase_pct or 0.0
    td = transition_delay_months or 0

    if stress_type == "FINANCING_COST":
        revenue_impact_pct = 0.0
        cost_increase_pct = round(fcb / 100, 4)
        ebitda_impact_pct = round(-fcb / 100, 4)
    elif stress_type == "GREEN_REVENUE_DECLINE":
        revenue_impact_pct = round(-grd, 4)
        cost_increase_pct = 0.0
        ebitda_impact_pct = round(-grd * 0.6, 4)
    elif stress_type == "CARBON_TAX":
        revenue_impact_pct = 0.0
        cost_increase_pct = round(ctax * 0.5, 4)
        ebitda_impact_pct = round(-ctax * 0.5, 4)
    elif stress_type == "TRANSITION_DELAY":
        revenue_impact_pct = 0.0
        cost_increase_pct = round(td * 2.0, 4)
        ebitda_impact_pct = round(-td * 2.0, 4)
    else:
        revenue_impact_pct = cost_increase_pct = ebitda_impact_pct = 0.0

    financial_impact = {
        "revenue_impact_pct": revenue_impact_pct,
        "cost_increase_pct": cost_increase_pct,
        "ebitda_impact_pct": ebitda_impact_pct,
        "methodology": "deterministic_linear",
    }
    esg_impact = {
        "taxonomy_alignment_risk": round(abs(cost_increase_pct) * 0.3, 4),
    }
    return financial_impact, esg_impact


# ── Climate Stress Test ───────────────────────────────────────────────────────

def create_climate_stress_test(
    organization_id: str,
    test_name: str,
    stress_type: str,
    actor_id: str,
    session: Session,
    *,
    scenario_id: str | None = None,
    carbon_price_shock_pct: float | None = None,
    physical_risk_multiplier: float | None = None,
    regulatory_intensity_score: float | None = None,
    transition_cost_pct: float | None = None,
    test_methodology: str | None = None,
) -> ClimateStressTestModel:
    if stress_type not in CLIMATE_STRESS_TYPES:
        raise StrategyError(f"Invalid stress_type: {stress_type}")

    risk_impact, emissions_impact, financial_impact = _compute_climate_impacts(
        stress_type,
        carbon_price_shock_pct or 0.0,
        physical_risk_multiplier or 0.0,
        regulatory_intensity_score or 0.0,
        transition_cost_pct or 0.0,
    )

    now = _now()
    test = ClimateStressTestModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        test_name=test_name,
        stress_type=stress_type,
        scenario_id=scenario_id,
        carbon_price_shock_pct=carbon_price_shock_pct,
        physical_risk_multiplier=physical_risk_multiplier,
        regulatory_intensity_score=regulatory_intensity_score,
        transition_cost_pct=transition_cost_pct,
        risk_impact=risk_impact,
        emissions_impact=emissions_impact,
        financial_impact=financial_impact,
        test_methodology=test_methodology or f"deterministic_{stress_type.lower()}",
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(test)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.stress_test.created",
        actor_id=actor_id,
        resource_type="climate_stress_test",
        resource_id=test.id,
        details={"test_name": test_name, "stress_type": stress_type},
    )
    strategy_counters.record_climate_stress_test()
    return test


def list_climate_stress_tests(
    organization_id: str, session: Session
) -> list[ClimateStressTestModel]:
    return (
        session.query(ClimateStressTestModel)
        .filter(ClimateStressTestModel.organization_id == organization_id)
        .order_by(ClimateStressTestModel.created_at.desc())
        .all()
    )


# ── Supplier Shock Scenario ───────────────────────────────────────────────────

def create_supplier_shock(
    organization_id: str,
    scenario_name: str,
    shock_type: str,
    shock_severity: float,
    actor_id: str,
    session: Session,
    *,
    affected_supplier_ids: list | None = None,
    affected_region: str | None = None,
    propagation_model: str = "LINEAR",
    recovery_timeline_months: int | None = None,
) -> SupplierShockScenarioModel:
    if shock_type not in SUPPLIER_SHOCK_TYPES:
        raise StrategyError(f"Invalid shock_type: {shock_type}")
    if propagation_model not in PROPAGATION_MODELS:
        raise StrategyError(f"Invalid propagation_model: {propagation_model}")

    supply_chain_impact, financial_impact, esg_impact = _compute_supplier_impacts(
        shock_severity, propagation_model
    )

    now = _now()
    shock = SupplierShockScenarioModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        scenario_name=scenario_name,
        shock_type=shock_type,
        affected_supplier_ids={"supplier_ids": affected_supplier_ids or []},
        affected_region=affected_region,
        shock_severity=shock_severity,
        propagation_model=propagation_model,
        supply_chain_impact=supply_chain_impact,
        financial_impact=financial_impact,
        esg_impact=esg_impact,
        recovery_timeline_months=recovery_timeline_months,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(shock)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.supplier_shock.created",
        actor_id=actor_id,
        resource_type="supplier_shock_scenario",
        resource_id=shock.id,
        details={"scenario_name": scenario_name, "shock_type": shock_type},
    )
    strategy_counters.record_supplier_shock()
    return shock


def list_supplier_shocks(
    organization_id: str, session: Session
) -> list[SupplierShockScenarioModel]:
    return (
        session.query(SupplierShockScenarioModel)
        .filter(SupplierShockScenarioModel.organization_id == organization_id)
        .order_by(SupplierShockScenarioModel.created_at.desc())
        .all()
    )


# ── Financial Stress Test ─────────────────────────────────────────────────────

def create_financial_stress_test(
    organization_id: str,
    test_name: str,
    stress_type: str,
    actor_id: str,
    session: Session,
    *,
    financing_cost_increase_bps: float | None = None,
    green_revenue_decline_pct: float | None = None,
    carbon_tax_increase_pct: float | None = None,
    transition_delay_months: int | None = None,
    recovery_pathway: str | None = None,
) -> FinancialStressTestModel:
    if stress_type not in FINANCIAL_STRESS_TYPES:
        raise StrategyError(f"Invalid stress_type: {stress_type}")

    financial_impact, esg_impact = _compute_financial_stress_impacts(
        stress_type,
        financing_cost_increase_bps or 0.0,
        green_revenue_decline_pct or 0.0,
        carbon_tax_increase_pct or 0.0,
        transition_delay_months or 0,
    )

    now = _now()
    test = FinancialStressTestModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        test_name=test_name,
        stress_type=stress_type,
        financing_cost_increase_bps=financing_cost_increase_bps,
        green_revenue_decline_pct=green_revenue_decline_pct,
        carbon_tax_increase_pct=carbon_tax_increase_pct,
        transition_delay_months=transition_delay_months,
        financial_impact=financial_impact,
        esg_impact=esg_impact,
        recovery_pathway=recovery_pathway,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(test)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.financial_stress_test.created",
        actor_id=actor_id,
        resource_type="financial_stress_test",
        resource_id=test.id,
        details={"test_name": test_name, "stress_type": stress_type},
    )
    strategy_counters.record_financial_stress_test()
    return test


def list_financial_stress_tests(
    organization_id: str, session: Session
) -> list[FinancialStressTestModel]:
    return (
        session.query(FinancialStressTestModel)
        .filter(FinancialStressTestModel.organization_id == organization_id)
        .order_by(FinancialStressTestModel.created_at.desc())
        .all()
    )
