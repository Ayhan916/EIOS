"""M44.1 — Scenario Template and Stress Test Template CRUD services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.digital_twin_service import StrategyError
from application.strategy.metrics import strategy_counters
from infrastructure.persistence.models.strategy import (
    SCENARIO_TEMPLATE_TYPES,
    SCENARIO_TYPES,
    SEVERITY_LEVELS,
    STRESS_TEST_TEMPLATE_TYPES,
    ScenarioTemplateModel,
    StressTestTemplateModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


# ── Scenario Templates ────────────────────────────────────────────────────────


def create_scenario_template(
    organization_id: str,
    template_name: str,
    template_type: str,
    scenario_type: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    default_assumptions: dict | None = None,
    default_time_horizon_years: int = 5,
) -> ScenarioTemplateModel:
    if template_type not in SCENARIO_TEMPLATE_TYPES:
        raise StrategyError(f"Invalid template_type: {template_type}")
    if scenario_type not in SCENARIO_TYPES:
        raise StrategyError(f"Invalid scenario_type: {scenario_type}")
    now = _now()
    template = ScenarioTemplateModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        template_name=template_name,
        template_type=template_type,
        description=description,
        default_assumptions=default_assumptions or {},
        default_time_horizon_years=default_time_horizon_years,
        scenario_type=scenario_type,
        usage_count=0,
        is_approved=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(template)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.scenario_template.created",
        actor_id=actor_id,
        resource_type="scenario_template",
        resource_id=template.id,
        details={"template_name": template_name, "template_type": template_type},
    )
    strategy_counters.record_scenario_template()
    return template


def instantiate_from_template(
    organization_id: str,
    template_id: str,
    scenario_name: str,
    actor_id: str,
    session: Session,
    *,
    assumption_overrides: dict | None = None,
    time_horizon_years: int | None = None,
):
    from application.strategy.scenario_service import create_assumption, create_scenario

    template = session.get(ScenarioTemplateModel, template_id)
    _assert_org(template, organization_id, "scenario template")

    scenario = create_scenario(
        organization_id,
        scenario_name,
        template.scenario_type,
        actor_id,
        session,
        description=f"Instantiated from template: {template.template_name}",
        time_horizon_years=time_horizon_years or template.default_time_horizon_years,
    )

    merged = {**(template.default_assumptions or {}), **(assumption_overrides or {})}
    for key, val in merged.items():
        if isinstance(val, (int, float)):
            create_assumption(
                organization_id,
                scenario.id,
                assumption_key=key,
                assumption_label=key.replace("_", " ").title(),
                value=float(val),
                actor_id=actor_id,
                session=session,
            )

    template.usage_count = (template.usage_count or 0) + 1
    template.updated_at = _now()
    session.flush()

    emit_audit_event(
        session=session,
        event_type="strategy.scenario_template.instantiated",
        actor_id=actor_id,
        resource_type="scenario_template",
        resource_id=template_id,
        details={"scenario_id": scenario.id, "scenario_name": scenario_name},
    )
    return scenario


def list_scenario_templates(organization_id: str, session: Session) -> list[ScenarioTemplateModel]:
    return (
        session.query(ScenarioTemplateModel)
        .filter(ScenarioTemplateModel.organization_id == organization_id)
        .order_by(ScenarioTemplateModel.created_at.desc())
        .all()
    )


# ── Stress Test Templates ─────────────────────────────────────────────────────


def create_stress_test_template(
    organization_id: str,
    template_name: str,
    template_type: str,
    actor_id: str,
    session: Session,
    *,
    default_assumptions: dict | None = None,
    methodology: str | None = None,
    severity_level: str = "MEDIUM",
) -> StressTestTemplateModel:
    if template_type not in STRESS_TEST_TEMPLATE_TYPES:
        raise StrategyError(f"Invalid template_type: {template_type}")
    if severity_level not in SEVERITY_LEVELS:
        raise StrategyError(f"Invalid severity_level: {severity_level}")
    now = _now()
    template = StressTestTemplateModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        template_name=template_name,
        template_type=template_type,
        default_assumptions=default_assumptions or {},
        methodology=methodology,
        severity_level=severity_level,
        usage_count=0,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(template)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.stress_test_template.created",
        actor_id=actor_id,
        resource_type="stress_test_template",
        resource_id=template.id,
        details={"template_name": template_name, "template_type": template_type},
    )
    strategy_counters.record_stress_test_template()
    return template


def list_stress_test_templates(
    organization_id: str, session: Session
) -> list[StressTestTemplateModel]:
    return (
        session.query(StressTestTemplateModel)
        .filter(StressTestTemplateModel.organization_id == organization_id)
        .order_by(StressTestTemplateModel.created_at.desc())
        .all()
    )
