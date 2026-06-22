"""M44 — Board Simulation Center service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.metrics import strategy_counters
from application.strategy.digital_twin_service import StrategyError
from application.strategy.scenario_service import list_executions
from infrastructure.persistence.models.strategy import (
    BoardSimulationModel,
    ScenarioExecutionModel,
    StrategyScenarioModel,
)

_DIMENSIONS = ["risk", "esg_score", "emissions", "value_creation", "financial_outcomes"]


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _latest_execution_for(
    organization_id: str,
    scenario_id: str | None,
    session: Session,
) -> dict:
    """Pull the most recent completed execution for a scenario."""
    if not scenario_id:
        return {}
    exec_rec = (
        session.query(ScenarioExecutionModel)
        .filter(
            ScenarioExecutionModel.organization_id == organization_id,
            ScenarioExecutionModel.scenario_id == scenario_id,
            ScenarioExecutionModel.execution_status == "Completed",
        )
        .order_by(ScenarioExecutionModel.executed_at.desc())
        .first()
    )
    if exec_rec is None:
        return {"scenario_id": scenario_id, "status": "no_execution"}
    return {
        "scenario_id": scenario_id,
        "projected_kpis": exec_rec.projected_kpis,
        "projected_risks": exec_rec.projected_risks,
        "projected_emissions": exec_rec.projected_emissions,
        "projected_financial": exec_rec.projected_financial,
        "executed_at": exec_rec.executed_at.isoformat() if exec_rec.executed_at else None,
    }


def create_board_simulation(
    organization_id: str,
    simulation_name: str,
    actor_id: str,
    session: Session,
    *,
    scenario_a_id: str | None = None,
    scenario_b_id: str | None = None,
    scenario_c_id: str | None = None,
    recommendation: str | None = None,
) -> BoardSimulationModel:
    scenario_a_results = _latest_execution_for(organization_id, scenario_a_id, session)
    scenario_b_results = _latest_execution_for(organization_id, scenario_b_id, session)
    scenario_c_results = _latest_execution_for(organization_id, scenario_c_id, session)

    now = _now()
    simulation = BoardSimulationModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        simulation_name=simulation_name,
        scenario_a_id=scenario_a_id,
        scenario_b_id=scenario_b_id,
        scenario_c_id=scenario_c_id,
        comparison_dimensions={"dimensions": _DIMENSIONS},
        scenario_a_results=scenario_a_results,
        scenario_b_results=scenario_b_results,
        scenario_c_results=scenario_c_results,
        recommendation=recommendation,
        simulated_by=actor_id,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(simulation)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.board_simulation.generated",
        actor_id=actor_id,
        resource_type="board_simulation",
        resource_id=simulation.id,
        details={
            "simulation_name": simulation_name,
            "scenarios": [s for s in [scenario_a_id, scenario_b_id, scenario_c_id] if s],
        },
    )
    strategy_counters.record_board_simulation()
    return simulation


def list_board_simulations(
    organization_id: str, session: Session
) -> list[BoardSimulationModel]:
    return (
        session.query(BoardSimulationModel)
        .filter(BoardSimulationModel.organization_id == organization_id)
        .order_by(BoardSimulationModel.created_at.desc())
        .all()
    )
