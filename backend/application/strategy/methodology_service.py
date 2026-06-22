"""M44.1 — Strategy Methodology Registry service with versioning and approval audit."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.digital_twin_service import StrategyError
from application.strategy.metrics import strategy_counters
from infrastructure.persistence.models.strategy import StrategyMethodologyModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


def create_methodology(
    organization_id: str,
    methodology_name: str,
    actor_id: str,
    session: Session,
    *,
    methodology_version: str = "1.0.0",
    formula_description: str | None = None,
    assumptions: dict | None = None,
    applicable_to: list[str] | None = None,
) -> StrategyMethodologyModel:
    now = _now()
    methodology = StrategyMethodologyModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        methodology_name=methodology_name,
        methodology_version=methodology_version,
        formula_description=formula_description,
        assumptions=assumptions or {},
        applicable_to={"types": applicable_to or []},
        approval_status="DRAFT",
        approved_by=None,
        approved_at=None,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(methodology)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.methodology.created",
        actor_id=actor_id,
        resource_type="strategy_methodology",
        resource_id=methodology.id,
        details={"methodology_name": methodology_name, "version": methodology_version},
    )
    strategy_counters.record_strategy_methodology()
    return methodology


def approve_methodology(
    organization_id: str,
    methodology_id: str,
    actor_id: str,
    session: Session,
) -> StrategyMethodologyModel:
    methodology = session.get(StrategyMethodologyModel, methodology_id)
    _assert_org(methodology, organization_id, "strategy methodology")
    if methodology.approval_status == "DEPRECATED":
        raise StrategyError("Cannot approve a deprecated methodology")
    now = _now()
    methodology.approval_status = "APPROVED"
    methodology.approved_by = actor_id
    methodology.approved_at = now
    methodology.updated_at = now
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.methodology.approved",
        actor_id=actor_id,
        resource_type="strategy_methodology",
        resource_id=methodology_id,
        details={"methodology_name": methodology.methodology_name},
    )
    return methodology


def deprecate_methodology(
    organization_id: str,
    methodology_id: str,
    actor_id: str,
    session: Session,
) -> StrategyMethodologyModel:
    methodology = session.get(StrategyMethodologyModel, methodology_id)
    _assert_org(methodology, organization_id, "strategy methodology")
    now = _now()
    methodology.approval_status = "DEPRECATED"
    methodology.updated_at = now
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.methodology.deprecated",
        actor_id=actor_id,
        resource_type="strategy_methodology",
        resource_id=methodology_id,
        details={"methodology_name": methodology.methodology_name},
    )
    return methodology


def list_methodologies(
    organization_id: str, session: Session
) -> list[StrategyMethodologyModel]:
    return (
        session.query(StrategyMethodologyModel)
        .filter(StrategyMethodologyModel.organization_id == organization_id)
        .order_by(StrategyMethodologyModel.created_at.desc())
        .all()
    )
