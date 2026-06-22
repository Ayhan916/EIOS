"""M44 — Transition Pathway and Net Zero Pathway Modeling service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from application.strategy.metrics import strategy_counters
from application.strategy.digital_twin_service import StrategyError
from infrastructure.persistence.models.strategy import (
    MILESTONE_FREQUENCIES,
    PATHWAY_TYPES,
    NetZeroPathwayRecord,
    TransitionPathwayModel,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_org(record, organization_id: str, label: str = "resource") -> None:
    if record is None or getattr(record, "organization_id", None) != organization_id:
        raise StrategyError(f"{label} not found")


def _compute_milestones(
    baseline_emissions: float,
    target_emissions: float,
    baseline_year: int,
    target_year: int,
    num_milestones: int = 5,
) -> list[dict]:
    """Legacy 5-milestone linear interpolation. Preserved for ANNUAL backward compatibility."""
    if target_year <= baseline_year or num_milestones < 1:
        return []
    total_years = target_year - baseline_year
    milestones = []
    for i in range(1, num_milestones + 1):
        frac = i / num_milestones
        year = baseline_year + round(frac * total_years)
        em = round(baseline_emissions + (target_emissions - baseline_emissions) * frac, 2)
        milestones.append({"step": i, "year": year, "emissions_tco2e": em, "frequency": "ANNUAL"})
    return milestones


def _compute_milestones_v2(
    baseline_emissions: float,
    target_emissions: float,
    baseline_year: int,
    target_year: int,
    frequency: str = "ANNUAL",
) -> list[dict]:
    """Linear interpolation with configurable frequency (ANNUAL/SEMIANNUAL/QUARTERLY).

    ANNUAL    → one milestone per year
    SEMIANNUAL → two milestones per year (H1 / H2)
    QUARTERLY  → four milestones per year (Q1–Q4)
    """
    if target_year <= baseline_year:
        return []
    total_years = target_year - baseline_year

    if frequency == "QUARTERLY":
        steps_per_year = 4
    elif frequency == "SEMIANNUAL":
        steps_per_year = 2
    else:
        steps_per_year = 1

    total_steps = total_years * steps_per_year
    if total_steps < 1:
        return []

    milestones = []
    for i in range(1, total_steps + 1):
        frac = i / total_steps
        em = round(baseline_emissions + (target_emissions - baseline_emissions) * frac, 2)
        years_elapsed = (i - 1) // steps_per_year
        sub_step = (i - 1) % steps_per_year
        year = baseline_year + years_elapsed + (1 if sub_step == steps_per_year - 1 else 0)

        if frequency == "QUARTERLY":
            period = f"{baseline_year + (i - 1) // 4}-Q{sub_step + 1}"
        elif frequency == "SEMIANNUAL":
            period = f"{baseline_year + (i - 1) // 2}-H{sub_step + 1}"
        else:
            period = str(baseline_year + i)

        milestones.append({
            "step": i,
            "year": baseline_year + (i * total_years) // total_steps,
            "period": period,
            "emissions_tco2e": em,
            "frequency": frequency,
        })
    return milestones


def create_pathway(
    organization_id: str,
    pathway_name: str,
    pathway_type: str,
    target_year: int,
    actor_id: str,
    session: Session,
    *,
    baseline_emissions_tco2e: float | None = None,
    target_emissions_tco2e: float | None = None,
    strategic_plan_id: str | None = None,
    is_primary: bool = False,
    milestone_frequency: str = "ANNUAL",
) -> TransitionPathwayModel:
    if pathway_type not in PATHWAY_TYPES:
        raise StrategyError(f"Invalid pathway_type: {pathway_type}")
    if milestone_frequency not in MILESTONE_FREQUENCIES:
        raise StrategyError(f"Invalid milestone_frequency: {milestone_frequency}")

    reduction_pct: float | None = None
    milestones: list[dict] | None = None

    if baseline_emissions_tco2e is not None and target_emissions_tco2e is not None:
        if baseline_emissions_tco2e > 0:
            reduction_pct = round(
                (baseline_emissions_tco2e - target_emissions_tco2e) / baseline_emissions_tco2e * 100, 4
            )
        import datetime as _dt
        baseline_year = _dt.datetime.now(_dt.timezone.utc).year
        if milestone_frequency == "ANNUAL":
            # Backward-compatible: 5 evenly-spaced annual milestones
            milestones = _compute_milestones(
                baseline_emissions_tco2e,
                target_emissions_tco2e,
                baseline_year,
                target_year,
            )
        else:
            milestones = _compute_milestones_v2(
                baseline_emissions_tco2e,
                target_emissions_tco2e,
                baseline_year,
                target_year,
                frequency=milestone_frequency,
            )

    now = _now()
    pathway = TransitionPathwayModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        pathway_name=pathway_name,
        pathway_type=pathway_type,
        baseline_emissions_tco2e=baseline_emissions_tco2e,
        target_year=target_year,
        target_emissions_tco2e=target_emissions_tco2e,
        reduction_pct=reduction_pct,
        milestones={"milestones": milestones or []},
        strategic_plan_id=strategic_plan_id,
        is_primary=is_primary,
        milestone_frequency=milestone_frequency,
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(pathway)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.pathway.created",
        actor_id=actor_id,
        resource_type="transition_pathway",
        resource_id=pathway.id,
        details={"pathway_name": pathway_name, "pathway_type": pathway_type, "target_year": target_year},
    )
    strategy_counters.record_transition_pathway()
    return pathway


def create_net_zero_pathway(
    organization_id: str,
    pathway_id: str,
    net_zero_year: int,
    actor_id: str,
    session: Session,
    *,
    interim_targets: list[dict] | None = None,
    assumptions: dict | None = None,
    abatement_cost: float | None = None,
    methodology: str | None = None,
) -> NetZeroPathwayRecord:
    pathway = session.get(TransitionPathwayModel, pathway_id)
    _assert_org(pathway, organization_id, "transition pathway")

    now = _now()
    nz = NetZeroPathwayRecord(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        pathway_id=pathway_id,
        net_zero_year=net_zero_year,
        interim_targets={"targets": interim_targets or []},
        assumptions=assumptions,
        abatement_cost=abatement_cost,
        methodology=methodology or "SBTi_1.5C",
        is_final=False,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    session.add(nz)
    session.flush()
    emit_audit_event(
        session=session,
        event_type="strategy.net_zero_pathway.created",
        actor_id=actor_id,
        resource_type="net_zero_pathway",
        resource_id=nz.id,
        details={"pathway_id": pathway_id, "net_zero_year": net_zero_year},
    )
    strategy_counters.record_net_zero_pathway()
    return nz


def list_pathways(organization_id: str, session: Session) -> list[TransitionPathwayModel]:
    return (
        session.query(TransitionPathwayModel)
        .filter(TransitionPathwayModel.organization_id == organization_id)
        .order_by(TransitionPathwayModel.created_at.desc())
        .all()
    )


def list_net_zero_pathways(
    organization_id: str,
    pathway_id: str,
    session: Session,
) -> list[NetZeroPathwayRecord]:
    pathway = session.get(TransitionPathwayModel, pathway_id)
    _assert_org(pathway, organization_id, "transition pathway")
    return (
        session.query(NetZeroPathwayRecord)
        .filter(
            NetZeroPathwayRecord.organization_id == organization_id,
            NetZeroPathwayRecord.pathway_id == pathway_id,
        )
        .all()
    )
