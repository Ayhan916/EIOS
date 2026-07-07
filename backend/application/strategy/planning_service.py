"""M44 — Strategic Planning service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.digital_twin_service import StrategyError
from application.strategy.metrics import strategy_counters
from infrastructure.persistence.models.strategy import (
    OBJECTIVE_TYPES,
    PLANNING_HORIZONS,
    StrategicObjectiveModel,
    StrategicPlanModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


def create_plan(
    organization_id: str,
    title: str,
    planning_horizon: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    baseline_snapshot_id: str | None = None,
    target_snapshot_id: str | None = None,
    plan_owner: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> StrategicPlanModel:
    if planning_horizon not in PLANNING_HORIZONS:
        raise StrategyError(f"Invalid planning_horizon: {planning_horizon}")
    now = _now()
    plan = StrategicPlanModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        title=title,
        description=description,
        planning_horizon=planning_horizon,
        baseline_snapshot_id=baseline_snapshot_id,
        target_snapshot_id=target_snapshot_id,
        plan_owner=plan_owner,
        plan_status="Draft",
        start_date=start_date,
        end_date=end_date,
        objectives_count=0,
        is_approved=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(plan)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.plan.created",
        actor_id=actor_id,
        resource_type="strategic_plan",
        resource_id=plan.id,
        details={"title": title, "planning_horizon": planning_horizon},
    )
    strategy_counters.record_plan()
    return plan


def create_objective(
    organization_id: str,
    plan_id: str,
    title: str,
    objective_type: str,
    actor_id: str,
    session: Session,
    *,
    linked_esg_objective_id: str | None = None,
    linked_financial_kpi_id: str | None = None,
    linked_risk_id: str | None = None,
    current_value: float | None = None,
    target_value: float | None = None,
    confidence: float | None = None,
    unit: str | None = None,
    target_year: int | None = None,
) -> StrategicObjectiveModel:
    if objective_type not in OBJECTIVE_TYPES:
        raise StrategyError(f"Invalid objective_type: {objective_type}")
    plan = session.get(StrategicPlanModel, plan_id)
    _assert_org(plan, organization_id, "strategic plan")
    progress_pct: float | None = None
    if current_value is not None and target_value is not None and target_value != 0:
        progress_pct = round(min(100.0, (current_value / target_value) * 100), 2)
    now = _now()
    obj = StrategicObjectiveModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        plan_id=plan_id,
        title=title,
        objective_type=objective_type,
        linked_esg_objective_id=linked_esg_objective_id,
        linked_financial_kpi_id=linked_financial_kpi_id,
        linked_risk_id=linked_risk_id,
        current_value=current_value,
        target_value=target_value,
        confidence=confidence,
        unit=unit,
        target_year=target_year,
        progress_pct=progress_pct,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(obj)
    session.flush()
    plan.objectives_count = (plan.objectives_count or 0) + 1
    plan.updated_at = now
    strategy_counters.record_objective()
    return obj


def list_plans(organization_id: str, session: Session) -> list[StrategicPlanModel]:
    return (
        session.query(StrategicPlanModel)
        .filter(StrategicPlanModel.organization_id == organization_id)
        .order_by(StrategicPlanModel.created_at.desc())
        .all()
    )


def list_objectives(
    organization_id: str,
    plan_id: str,
    session: Session,
) -> list[StrategicObjectiveModel]:
    plan = session.get(StrategicPlanModel, plan_id)
    _assert_org(plan, organization_id, "strategic plan")
    return (
        session.query(StrategicObjectiveModel)
        .filter(
            StrategicObjectiveModel.organization_id == organization_id,
            StrategicObjectiveModel.plan_id == plan_id,
        )
        .all()
    )
