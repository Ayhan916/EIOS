"""M44 — Scenario Framework and Execution Engine service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.metrics import strategy_counters
from application.strategy.digital_twin_service import StrategyError
from infrastructure.persistence.models.strategy import (
    SCENARIO_STATUSES,
    SCENARIO_TYPES,
    DigitalTwinSnapshotModel,
    EnterpriseDigitalTwinModel,
    ScenarioAssumptionModel,
    ScenarioExecutionModel,
    StrategyScenarioModel,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


def _project_from_assumptions(
    baseline: dict,
    assumptions: list[ScenarioAssumptionModel],
    horizon_years: int,
) -> tuple[dict, dict, dict, dict]:
    """Apply assumption multipliers to baseline to produce deterministic projections."""
    assumption_map = {a.assumption_key: a.value for a in assumptions}

    emissions_growth = assumption_map.get("emissions_growth_pct_annual", 0.0)
    revenue_growth = assumption_map.get("revenue_growth_pct_annual", 2.0)
    risk_change = assumption_map.get("risk_change_pct_annual", 0.0)
    carbon_price = assumption_map.get("carbon_price_usd_per_tco2e", 50.0)

    base_emissions = baseline.get("emissions_tco2e", 0.0)
    base_revenue = baseline.get("revenue", 0.0)
    base_risk_score = baseline.get("risk_score", 5.0)

    projected_emissions = round(base_emissions * ((1 + emissions_growth / 100) ** horizon_years), 4)
    projected_revenue = round(base_revenue * ((1 + revenue_growth / 100) ** horizon_years), 4)
    projected_risk = round(min(10.0, base_risk_score * ((1 + risk_change / 100) ** horizon_years)), 4)
    projected_carbon_cost = round(projected_emissions * carbon_price, 4)

    projected_kpis = {
        "revenue": projected_revenue,
        "carbon_cost": projected_carbon_cost,
        "horizon_years": horizon_years,
        "methodology": "assumption_compound",
    }
    projected_risks = {
        "risk_score": projected_risk,
        "risk_change_pct": round(risk_change * horizon_years, 4),
    }
    projected_emissions_out = {
        "emissions_tco2e": projected_emissions,
        "emissions_growth_pct": round(emissions_growth * horizon_years, 4),
    }
    projected_financial = {
        "carbon_cost": projected_carbon_cost,
        "revenue": projected_revenue,
        "carbon_price_usd_per_tco2e": carbon_price,
    }
    return projected_kpis, projected_risks, projected_emissions_out, projected_financial


def resolve_strategy_baseline(
    organization_id: str,
    session: Session,
    *,
    baseline_override: dict | None = None,
) -> dict:
    """Resolve a baseline for scenario execution.

    Priority chain:
    1. baseline_override (if provided and non-empty)
    2. Latest finalized DigitalTwinSnapshot for the active twin
    3. Latest active EnterpriseDigitalTwin baseline fields
    4. StrategyError — no baseline available
    """
    if baseline_override:
        return baseline_override

    twin = (
        session.query(EnterpriseDigitalTwinModel)
        .filter(
            EnterpriseDigitalTwinModel.organization_id == organization_id,
            EnterpriseDigitalTwinModel.is_active.is_(True),
        )
        .order_by(EnterpriseDigitalTwinModel.created_at.desc())
        .first()
    )

    if twin:
        snapshot = (
            session.query(DigitalTwinSnapshotModel)
            .filter(
                DigitalTwinSnapshotModel.twin_id == twin.id,
                DigitalTwinSnapshotModel.organization_id == organization_id,
                DigitalTwinSnapshotModel.is_final.is_(True),
            )
            .order_by(DigitalTwinSnapshotModel.captured_at.desc())
            .first()
        )
        if snapshot:
            baseline: dict = {}
            if snapshot.sustainability_state:
                baseline.update(snapshot.sustainability_state)
            if snapshot.financial_esg_state:
                baseline.update(snapshot.financial_esg_state)
            return baseline

        # Fall back to twin-level fields
        baseline = {}
        if twin.emissions_baseline_tco2e is not None:
            baseline["emissions_tco2e"] = twin.emissions_baseline_tco2e
        if twin.financial_baseline:
            baseline.update(twin.financial_baseline)
        if baseline:
            return baseline

    raise StrategyError(
        "No baseline found — supply baseline_override or create an Enterprise Digital Twin"
    )


def create_scenario(
    organization_id: str,
    name: str,
    scenario_type: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    baseline_twin_id: str | None = None,
    time_horizon_years: int = 5,
    is_template: bool = False,
) -> StrategyScenarioModel:
    if scenario_type not in SCENARIO_TYPES:
        raise StrategyError(f"Invalid scenario_type: {scenario_type}")
    now = _now()
    scenario = StrategyScenarioModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        description=description,
        scenario_type=scenario_type,
        scenario_status="Draft",
        baseline_twin_id=baseline_twin_id,
        time_horizon_years=time_horizon_years,
        created_by_user=actor_id,
        is_template=is_template,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(scenario)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.scenario.created",
        actor_id=actor_id,
        resource_type="strategy_scenario",
        resource_id=scenario.id,
        details={"name": name, "scenario_type": scenario_type},
    )
    strategy_counters.record_scenario()
    return scenario


def create_assumption(
    organization_id: str,
    scenario_id: str,
    assumption_key: str,
    assumption_label: str,
    value: float,
    actor_id: str,
    session: Session,
    *,
    unit: str | None = None,
    rationale: str | None = None,
    source: str | None = None,
    assumption_year: int | None = None,
) -> ScenarioAssumptionModel:
    scenario = session.get(StrategyScenarioModel, scenario_id)
    _assert_org(scenario, organization_id, "scenario")
    now = _now()
    assumption = ScenarioAssumptionModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        scenario_id=scenario_id,
        assumption_key=assumption_key,
        assumption_label=assumption_label,
        value=value,
        unit=unit,
        rationale=rationale,
        source=source,
        assumption_year=assumption_year,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(assumption)
    session.flush()
    strategy_counters.record_assumption()
    return assumption


def execute_scenario(
    organization_id: str,
    scenario_id: str,
    actor_id: str,
    session: Session,
    *,
    twin_id: str | None = None,
    baseline_override: dict | None = None,
) -> ScenarioExecutionModel:
    scenario = session.get(StrategyScenarioModel, scenario_id)
    _assert_org(scenario, organization_id, "scenario")

    assumptions = (
        session.query(ScenarioAssumptionModel)
        .filter(
            ScenarioAssumptionModel.organization_id == organization_id,
            ScenarioAssumptionModel.scenario_id == scenario_id,
        )
        .all()
    )

    baseline = baseline_override or {}
    proj_kpis, proj_risks, proj_emissions, proj_financial = _project_from_assumptions(
        baseline, assumptions, scenario.time_horizon_years
    )

    now = _now()
    execution = ScenarioExecutionModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        scenario_id=scenario_id,
        twin_id=twin_id,
        execution_status="Completed",
        executed_at=now,
        projected_kpis=proj_kpis,
        projected_risks=proj_risks,
        projected_emissions=proj_emissions,
        projected_financial=proj_financial,
        execution_metadata={
            "assumption_count": len(assumptions),
            "horizon_years": scenario.time_horizon_years,
            "methodology": "deterministic_assumption_projection",
        },
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(execution)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.scenario.executed",
        actor_id=actor_id,
        resource_type="scenario_execution",
        resource_id=execution.id,
        details={"scenario_id": scenario_id, "assumption_count": len(assumptions)},
    )
    strategy_counters.record_scenario_execution()
    return execution


def list_scenarios(organization_id: str, session: Session) -> list[StrategyScenarioModel]:
    return (
        session.query(StrategyScenarioModel)
        .filter(StrategyScenarioModel.organization_id == organization_id)
        .order_by(StrategyScenarioModel.created_at.desc())
        .all()
    )


def list_assumptions(
    organization_id: str,
    scenario_id: str,
    session: Session,
) -> list[ScenarioAssumptionModel]:
    scenario = session.get(StrategyScenarioModel, scenario_id)
    _assert_org(scenario, organization_id, "scenario")
    return (
        session.query(ScenarioAssumptionModel)
        .filter(
            ScenarioAssumptionModel.organization_id == organization_id,
            ScenarioAssumptionModel.scenario_id == scenario_id,
        )
        .all()
    )


def list_executions(organization_id: str, session: Session) -> list[ScenarioExecutionModel]:
    return (
        session.query(ScenarioExecutionModel)
        .filter(ScenarioExecutionModel.organization_id == organization_id)
        .order_by(ScenarioExecutionModel.executed_at.desc())
        .all()
    )
