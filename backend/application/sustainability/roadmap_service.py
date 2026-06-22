"""Decarbonization Initiatives, Net Zero Roadmaps, and Science Based Targets."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.sustainability.metrics import sustainability_counters
from infrastructure.persistence.models.sustainability import (
    INITIATIVE_STATUSES,
    INITIATIVE_TYPES,
    MILESTONE_STATUSES,
    ROADMAP_STATUSES,
    SBT_FRAMEWORKS,
    SBT_SCOPES,
    SBT_STATUSES,
    SBT_TYPES,
    DecarbonizationInitiativeModel,
    NetZeroMilestoneModel,
    NetZeroRoadmapModel,
    ScienceBasedTargetModel,
)

from .objective_service import SustainabilityConflict, SustainabilityError, _assert_org, _now


# ── Decarbonization Initiatives ───────────────────────────────────────────────

def create_initiative(
    organization_id: str,
    name: str,
    initiative_type: str,
    expected_reduction: float,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
    roadmap_id: str | None = None,
    cost_estimate: float | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    notes: str | None = None,
) -> DecarbonizationInitiativeModel:
    if initiative_type not in INITIATIVE_TYPES:
        raise SustainabilityError(f"Invalid initiative_type: {initiative_type}")
    now = _now()
    init = DecarbonizationInitiativeModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        roadmap_id=roadmap_id,
        name=name,
        initiative_type=initiative_type,
        description=description,
        expected_reduction=expected_reduction,
        actual_reduction=None,
        cost_estimate=cost_estimate,
        initiative_status="PLANNED",
        start_date=start_date,
        end_date=end_date,
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(init)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.initiative.created",
        actor_id=actor_id,
        resource_type="decarbonization_initiative",
        resource_id=init.id,
        details={"name": name, "initiative_type": initiative_type, "expected_reduction": expected_reduction},
    )
    sustainability_counters.record_initiative_created()
    return init


def update_initiative_progress(
    initiative_id: str,
    actual_reduction: float,
    new_status: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> DecarbonizationInitiativeModel:
    if new_status not in INITIATIVE_STATUSES:
        raise SustainabilityError(f"Invalid initiative status: {new_status}")
    init = session.get(DecarbonizationInitiativeModel, initiative_id)
    _assert_org(init, organization_id, "Initiative")
    init.actual_reduction = actual_reduction
    init.initiative_status = new_status
    init.updated_by = actor_id
    init.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.initiative.updated",
        actor_id=actor_id,
        resource_type="decarbonization_initiative",
        resource_id=initiative_id,
        details={"actual_reduction": actual_reduction, "status": new_status},
    )
    return init


def list_initiatives(
    organization_id: str,
    session: Session,
    *,
    roadmap_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[DecarbonizationInitiativeModel]:
    q = session.query(DecarbonizationInitiativeModel).filter(
        DecarbonizationInitiativeModel.organization_id == organization_id
    )
    if roadmap_id:
        q = q.filter(DecarbonizationInitiativeModel.roadmap_id == roadmap_id)
    if status:
        q = q.filter(DecarbonizationInitiativeModel.initiative_status == status)
    return q.order_by(DecarbonizationInitiativeModel.created_at.desc()).limit(limit).offset(offset).all()


# ── Net Zero Roadmaps ─────────────────────────────────────────────────────────

def _compute_target_emissions(baseline: float, reduction_pct: float) -> float:
    """target = baseline × (1 - reduction_pct / 100)"""
    return round(baseline * (1 - reduction_pct / 100.0), 6)


def create_roadmap(
    organization_id: str,
    name: str,
    baseline_year: int,
    target_year: int,
    baseline_emissions: float,
    target_reduction_percent: float,
    actor_id: str,
    session: Session,
    *,
    description: str | None = None,
) -> NetZeroRoadmapModel:
    if target_year <= baseline_year:
        raise SustainabilityError("target_year must be after baseline_year")
    target_emissions = _compute_target_emissions(baseline_emissions, target_reduction_percent)
    now = _now()
    roadmap = NetZeroRoadmapModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=name,
        baseline_year=baseline_year,
        target_year=target_year,
        baseline_emissions=baseline_emissions,
        target_reduction_percent=target_reduction_percent,
        target_emissions=target_emissions,
        roadmap_status="DRAFT",
        description=description,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(roadmap)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.roadmap.created",
        actor_id=actor_id,
        resource_type="net_zero_roadmap",
        resource_id=roadmap.id,
        details={
            "name": name,
            "baseline_year": baseline_year,
            "target_year": target_year,
            "target_emissions": target_emissions,
        },
    )
    return roadmap


def add_milestone(
    roadmap_id: str,
    milestone_year: int,
    target_emissions: float,
    actor_id: str,
    session: Session,
    *,
    notes: str | None = None,
) -> NetZeroMilestoneModel:
    now = _now()
    ms = NetZeroMilestoneModel(
        id=str(uuid.uuid4()),
        roadmap_id=roadmap_id,
        milestone_year=milestone_year,
        target_emissions=target_emissions,
        actual_emissions=None,
        milestone_status="PENDING",
        notes=notes,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(ms)
    session.flush()
    return ms


def update_milestone(
    milestone_id: str,
    actual_emissions: float,
    new_status: str,
    actor_id: str,
    session: Session,
) -> NetZeroMilestoneModel:
    if new_status not in MILESTONE_STATUSES:
        raise SustainabilityError(f"Invalid milestone_status: {new_status}")
    ms = session.get(NetZeroMilestoneModel, milestone_id)
    if not ms:
        raise SustainabilityError("Milestone not found")
    ms.actual_emissions = actual_emissions
    ms.milestone_status = new_status
    ms.updated_by = actor_id
    ms.updated_at = _now()
    session.flush()
    return ms


def get_roadmap(roadmap_id: str, session: Session) -> NetZeroRoadmapModel | None:
    return session.get(NetZeroRoadmapModel, roadmap_id)


def list_roadmaps(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[NetZeroRoadmapModel]:
    return (
        session.query(NetZeroRoadmapModel)
        .filter(NetZeroRoadmapModel.organization_id == organization_id)
        .order_by(NetZeroRoadmapModel.target_year)
        .limit(limit)
        .offset(offset)
        .all()
    )


def list_milestones(
    roadmap_id: str,
    session: Session,
) -> list[NetZeroMilestoneModel]:
    return (
        session.query(NetZeroMilestoneModel)
        .filter(NetZeroMilestoneModel.roadmap_id == roadmap_id)
        .order_by(NetZeroMilestoneModel.milestone_year)
        .all()
    )


def update_roadmap_status(
    roadmap_id: str,
    new_status: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
) -> NetZeroRoadmapModel:
    if new_status not in ROADMAP_STATUSES:
        raise SustainabilityError(f"Invalid roadmap status: {new_status}")
    roadmap = session.get(NetZeroRoadmapModel, roadmap_id)
    _assert_org(roadmap, organization_id, "Roadmap")
    roadmap.roadmap_status = new_status
    roadmap.updated_by = actor_id
    roadmap.updated_at = _now()
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.roadmap.status_changed",
        actor_id=actor_id,
        resource_type="net_zero_roadmap",
        resource_id=roadmap_id,
        details={"new_status": new_status},
    )
    return roadmap


# ── Science Based Targets ─────────────────────────────────────────────────────

def create_science_based_target(
    organization_id: str,
    scope: str,
    target_type: str,
    baseline_year: int,
    baseline_emissions: float,
    target_reduction_percent: float,
    target_year: int,
    actor_id: str,
    session: Session,
    *,
    sbt_framework: str = "SBTi",
    description: str | None = None,
    commitment_date: datetime | None = None,
) -> ScienceBasedTargetModel:
    for val, choices, label in [
        (scope, SBT_SCOPES, "scope"),
        (target_type, SBT_TYPES, "target_type"),
        (sbt_framework, SBT_FRAMEWORKS, "sbt_framework"),
    ]:
        if val not in choices:
            raise SustainabilityError(f"Invalid {label}: {val}")
    if target_year <= baseline_year:
        raise SustainabilityError("target_year must be after baseline_year")
    now = _now()
    sbt = ScienceBasedTargetModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        scope=scope,
        target_type=target_type,
        baseline_year=baseline_year,
        baseline_emissions=baseline_emissions,
        target_reduction_percent=target_reduction_percent,
        target_year=target_year,
        sbt_status="DRAFT",
        sbt_framework=sbt_framework,
        commitment_date=commitment_date,
        approval_date=None,
        description=description,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(sbt)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="sustainability.sbt.created",
        actor_id=actor_id,
        resource_type="science_based_target",
        resource_id=sbt.id,
        details={
            "scope": scope,
            "target_reduction_percent": target_reduction_percent,
            "target_year": target_year,
            "sbt_framework": sbt_framework,
        },
    )
    sustainability_counters.record_sbt_created()
    return sbt


def update_sbt_status(
    sbt_id: str,
    new_status: str,
    actor_id: str,
    session: Session,
    *,
    organization_id: str,
    approval_date: datetime | None = None,
) -> ScienceBasedTargetModel:
    if new_status not in SBT_STATUSES:
        raise SustainabilityError(f"Invalid SBT status: {new_status}")
    sbt = session.get(ScienceBasedTargetModel, sbt_id)
    _assert_org(sbt, organization_id, "Science based target")
    sbt.sbt_status = new_status
    if approval_date:
        sbt.approval_date = approval_date
    sbt.updated_by = actor_id
    sbt.updated_at = _now()
    session.flush()
    return sbt


def list_science_based_targets(
    organization_id: str,
    session: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ScienceBasedTargetModel]:
    return (
        session.query(ScienceBasedTargetModel)
        .filter(ScienceBasedTargetModel.organization_id == organization_id)
        .order_by(ScienceBasedTargetModel.target_year)
        .limit(limit)
        .offset(offset)
        .all()
    )
