"""M44.1 — Scenario Comparison Engine.

Compares 2–10 scenarios by their latest completed executions.
Persists deltas for KPI, emissions, risk, and financial value.
All calculations are deterministic — simple arithmetic over projected outputs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.digital_twin_service import StrategyError
from application.strategy.metrics import strategy_counters
from infrastructure.persistence.models.strategy import (
    ScenarioComparisonModel,
    ScenarioExecutionModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


def compare_scenarios(
    organization_id: str,
    comparison_name: str,
    scenario_ids: list[str],
    actor_id: str,
    session: Session,
    *,
    comparison_methodology: str = "delta_vs_baseline",
) -> ScenarioComparisonModel:
    if len(scenario_ids) < 2:
        raise StrategyError("Scenario comparison requires at least 2 scenarios")
    if len(scenario_ids) > 10:
        raise StrategyError("Scenario comparison supports at most 10 scenarios")

    # Gather the latest completed execution per scenario
    executions: dict[str, ScenarioExecutionModel] = {}
    for sid in scenario_ids:
        exec_rec = (
            session.query(ScenarioExecutionModel)
            .filter(
                ScenarioExecutionModel.organization_id == organization_id,
                ScenarioExecutionModel.scenario_id == sid,
                ScenarioExecutionModel.execution_status == "Completed",
            )
            .order_by(ScenarioExecutionModel.executed_at.desc())
            .first()
        )
        if exec_rec:
            executions[sid] = exec_rec

    if len(executions) < 2:
        raise StrategyError("At least 2 scenarios must have completed executions to compare")

    # First scenario with an execution is the base
    base_sid = next(sid for sid in scenario_ids if sid in executions)
    base_exec = executions[base_sid]

    kpi_delta: dict = {}
    emissions_delta: dict = {}
    risk_delta: dict = {}
    value_delta: dict = {}

    for sid in scenario_ids:
        if sid == base_sid or sid not in executions:
            continue
        comp = executions[sid]

        base_kpis = base_exec.projected_kpis or {}
        comp_kpis = comp.projected_kpis or {}
        kpi_delta[sid] = {
            k: round(float(comp_kpis.get(k, 0)) - float(base_kpis.get(k, 0)), 4)
            for k in set(base_kpis) | set(comp_kpis)
            if isinstance(base_kpis.get(k, 0), (int, float))
            and isinstance(comp_kpis.get(k, 0), (int, float))
        }

        base_em = float((base_exec.projected_emissions or {}).get("emissions_tco2e", 0))
        comp_em = float((comp.projected_emissions or {}).get("emissions_tco2e", 0))
        emissions_delta[sid] = {"emissions_tco2e_delta": round(comp_em - base_em, 4)}

        base_risk = float((base_exec.projected_risks or {}).get("risk_score", 0))
        comp_risk = float((comp.projected_risks or {}).get("risk_score", 0))
        risk_delta[sid] = {"risk_score_delta": round(comp_risk - base_risk, 4)}

        base_val = float((base_exec.projected_financial or {}).get("revenue", 0))
        comp_val = float((comp.projected_financial or {}).get("revenue", 0))
        value_delta[sid] = {"revenue_delta": round(comp_val - base_val, 4)}

    now = _now()
    comparison = ScenarioComparisonModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        comparison_name=comparison_name,
        scenario_ids={"scenario_ids": scenario_ids, "base_scenario_id": base_sid},
        kpi_delta=kpi_delta,
        emissions_delta=emissions_delta,
        risk_delta=risk_delta,
        value_delta=value_delta,
        comparison_methodology=comparison_methodology,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(comparison)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.scenario_comparison.created",
        actor_id=actor_id,
        resource_type="scenario_comparison",
        resource_id=comparison.id,
        details={"comparison_name": comparison_name, "scenario_count": len(scenario_ids)},
    )
    strategy_counters.record_scenario_comparison()
    return comparison


def list_comparisons(organization_id: str, session: Session) -> list[ScenarioComparisonModel]:
    return (
        session.query(ScenarioComparisonModel)
        .filter(ScenarioComparisonModel.organization_id == organization_id)
        .order_by(ScenarioComparisonModel.created_at.desc())
        .all()
    )
