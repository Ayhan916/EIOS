"""ESG Objectives and Targets management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.sustainability.metrics import sustainability_counters
from infrastructure.persistence.models.operating_system import ESGProgramModel
from infrastructure.persistence.models.sustainability import (
    ESG_CATEGORIES,
    MEASUREMENT_FREQUENCIES,
    OBJECTIVE_STATUSES,
    ESGTargetModel,
    SustainabilityObjectiveModel,
)


class SustainabilityError(Exception):
    pass


class SustainabilityConflict(SustainabilityError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise SustainabilityError(f"{label} not found")


# ── ESG Objectives ─────────────────────────────────────────────────────────────


def validate_program_assignment(
    program_id: str,
    organization_id: str,
    actor_id: str,
    session: Session,
) -> None:
    prog = session.get(ESGProgramModel, program_id)
    if prog is None or prog.organization_id != organization_id:
        raise SustainabilityError("program_id must reference a program in this organization")
    emit_audit_event(
        session=session,
        event_type="sustainability.program.linked",
        actor_id=actor_id,
        resource_type="esg_program",
        resource_id=program_id,
        details={"organization_id": organization_id},
    )


def create_objective(
    organization_id: str,
    title: str,
    category: str,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    owner_user_id: str | None = None,
    start_date: datetime | None = None,
    target_date: datetime | None = None,
    program_id: str | None = None,
) -> SustainabilityObjectiveModel:
    if category not in ESG_CATEGORIES:
        raise SustainabilityError(f"Invalid category: {category}")
    if program_id:
        validate_program_assignment(program_id, organization_id, actor_id, session)
    now = _now()
    obj = SustainabilityObjectiveModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        title=title,
        description=description,
        category=category,
        owner_user_id=owner_user_id,
        start_date=start_date,
        target_date=target_date,
        objective_status="DRAFT",
        program_id=program_id,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(obj)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.objective.created",
        actor_id=actor_id,
        resource_type="esg_objective",
        resource_id=obj.id,
        details={"title": title, "category": category},
    )
    sustainability_counters.record_objective_created()
    return obj


def update_objective_status(
    objective_id: str,
    new_status: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> SustainabilityObjectiveModel:
    if new_status not in OBJECTIVE_STATUSES:
        raise SustainabilityError(f"Invalid status: {new_status}")
    obj = session.get(SustainabilityObjectiveModel, objective_id)
    _assert_org(obj, organization_id, "Objective")
    old_status = obj.objective_status
    obj.objective_status = new_status
    obj.updated_by = actor_id
    obj.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.objective.status_changed",
        actor_id=actor_id,
        resource_type="esg_objective",
        resource_id=objective_id,
        details={"old_status": old_status, "new_status": new_status},
    )
    return obj


def get_objective(objective_id: str, session: Session) -> SustainabilityObjectiveModel | None:
    return session.get(SustainabilityObjectiveModel, objective_id)


def list_objectives(
    organization_id: str,
    session: Session,
    *,
    category: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SustainabilityObjectiveModel]:
    q = session.query(SustainabilityObjectiveModel).filter(
        SustainabilityObjectiveModel.organization_id == organization_id
    )
    if category:
        q = q.filter(SustainabilityObjectiveModel.category == category)
    if status:
        q = q.filter(SustainabilityObjectiveModel.objective_status == status)
    return (
        q.order_by(SustainabilityObjectiveModel.created_at.desc()).limit(limit).offset(offset).all()
    )


# ── ESG Targets ───────────────────────────────────────────────────────────────


def compute_progress(baseline: float, target: float, current: float | None) -> float:
    """Deterministic progress calculation: 0-100 percent."""
    if current is None:
        return 0.0
    span = target - baseline
    if span == 0:
        return 100.0 if current >= target else 0.0
    progress = (current - baseline) / span * 100.0
    return max(0.0, min(100.0, round(progress, 2)))


def create_target(
    organization_id: str,
    objective_id: str,
    metric_name: str,
    baseline_value: float,
    target_value: float,
    actor_id: str,
    session: Session,
    *,
    target_unit: str | None = None,
    measurement_frequency: str = "QUARTERLY",
    target_date: datetime | None = None,
    notes: str | None = None,
) -> ESGTargetModel:
    if measurement_frequency not in MEASUREMENT_FREQUENCIES:
        raise SustainabilityError(f"Invalid measurement_frequency: {measurement_frequency}")
    now = _now()
    target = ESGTargetModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        objective_id=objective_id,
        metric_name=metric_name,
        baseline_value=baseline_value,
        target_value=target_value,
        target_unit=target_unit,
        current_value=None,
        measurement_frequency=measurement_frequency,
        target_date=target_date,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(target)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.target.created",
        actor_id=actor_id,
        resource_type="esg_target",
        resource_id=target.id,
        details={"metric_name": metric_name, "target_value": target_value},
    )
    sustainability_counters.record_target_created()
    return target


def update_target_value(
    target_id: str,
    current_value: float,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> tuple[ESGTargetModel, float]:
    """Update current_value and return (target, computed_progress_percent)."""
    t = session.get(ESGTargetModel, target_id)
    _assert_org(t, organization_id, "Target")
    t.current_value = current_value
    t.updated_by = actor_id
    t.updated_at = _now()
    session.flush()
    progress = compute_progress(t.baseline_value, t.target_value, current_value)
    emit_audit_event(
        session=session,
        event_type="sustainability.target.updated",
        actor_id=actor_id,
        resource_type="esg_target",
        resource_id=target_id,
        details={"current_value": current_value, "progress_percent": progress},
    )
    return t, progress


def list_targets(
    objective_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[ESGTargetModel, float]]:
    """Returns (target, progress_percent) tuples."""
    targets = (
        session.query(ESGTargetModel)
        .filter(ESGTargetModel.objective_id == objective_id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [
        (t, compute_progress(t.baseline_value, t.target_value, t.current_value)) for t in targets
    ]


def list_all_targets(
    organization_id: str,
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[tuple[ESGTargetModel, float]]:
    """Returns (target, progress_percent) tuples for all targets in an org."""
    targets = (
        session.query(ESGTargetModel)
        .filter(ESGTargetModel.organization_id == organization_id)
        .order_by(ESGTargetModel.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [
        (t, compute_progress(t.baseline_value, t.target_value, t.current_value)) for t in targets
    ]
