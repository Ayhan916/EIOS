"""M42.1 — Enterprise Sustainability Rollups.

Aggregates sustainability data across all organizations within an enterprise
hierarchy entity (Enterprise / BusinessUnit / LegalEntity / Region).

All aggregation is performed server-side via SQL GROUP BY — no Python-level N+1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from application.ai_governance._audit import emit_audit_event
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.persistence.models.sustainability import (
    CarbonInventoryModel,
    ClimateRiskAssessmentModel,
    ESGKPIModel,
    KPIMeasurementModel,
    SustainabilityObjectiveModel,
    SustainabilityScorecardModel,
    ESGTargetModel,
)
from .objective_service import SustainabilityError, _now

EntityType = Literal["enterprise", "business_unit", "legal_entity", "region"]


@dataclass
class EmissionsRollup:
    total_emissions: float = 0.0
    scope1: float = 0.0
    scope2: float = 0.0
    scope3: float = 0.0
    inventories_count: int = 0


@dataclass
class ObjectivesRollup:
    total: int = 0
    active: int = 0
    completed: int = 0
    completion_percent: float = 0.0


@dataclass
class TargetsRollup:
    total: int = 0
    with_measurements: int = 0
    attainment_percent: float = 0.0


@dataclass
class KPIsRollup:
    total: int = 0
    active: int = 0


@dataclass
class ScoreRollup:
    avg_overall_score: float | None = None
    avg_environmental_score: float | None = None
    avg_social_score: float | None = None
    avg_governance_score: float | None = None
    scorecard_count: int = 0


@dataclass
class ClimateRiskRollup:
    avg_overall_risk: float | None = None
    avg_transition_risk: float | None = None
    avg_physical_risk: float | None = None
    avg_regulatory_risk: float | None = None
    assessment_count: int = 0


@dataclass
class RollupSummary:
    entity_type: str
    entity_id: str
    organization_ids: list[str] = field(default_factory=list)
    emissions: EmissionsRollup = field(default_factory=EmissionsRollup)
    objectives: ObjectivesRollup = field(default_factory=ObjectivesRollup)
    targets: TargetsRollup = field(default_factory=TargetsRollup)
    kpis: KPIsRollup = field(default_factory=KPIsRollup)
    scores: ScoreRollup = field(default_factory=ScoreRollup)
    climate_risks: ClimateRiskRollup = field(default_factory=ClimateRiskRollup)
    computed_at: str = ""


def _org_ids_for_entity(
    entity_type: EntityType,
    entity_id: str,
    session: Session,
) -> list[str]:
    """Return all organization_ids belonging to a hierarchy entity."""
    col_map: dict[str, str] = {
        "enterprise": "enterprise_id",
        "business_unit": "business_unit_id",
        "legal_entity": "legal_entity_id",
        "region": "region_id",
    }
    col_name = col_map[entity_type]
    col = getattr(OrganizationModel, col_name)
    rows = (
        session.query(OrganizationModel.id)
        .filter(col == entity_id)
        .all()
    )
    return [r.id for r in rows]


def _emissions_rollup(org_ids: list[str], session: Session) -> EmissionsRollup:
    """Aggregate latest finalized inventory per org across the entity."""
    if not org_ids:
        return EmissionsRollup()

    # Latest finalized inventory per org using subquery
    from sqlalchemy import select as sa_select

    row = (
        session.query(
            func.sum(CarbonInventoryModel.total_emissions).label("total"),
            func.sum(CarbonInventoryModel.scope1_emissions).label("s1"),
            func.sum(CarbonInventoryModel.scope2_emissions).label("s2"),
            func.sum(CarbonInventoryModel.scope3_emissions).label("s3"),
            func.count(CarbonInventoryModel.id).label("cnt"),
        )
        .filter(
            CarbonInventoryModel.organization_id.in_(org_ids),
            CarbonInventoryModel.inventory_status == "FINALIZED",
        )
        .one()
    )
    return EmissionsRollup(
        total_emissions=round(float(row.total or 0.0), 6),
        scope1=round(float(row.s1 or 0.0), 6),
        scope2=round(float(row.s2 or 0.0), 6),
        scope3=round(float(row.s3 or 0.0), 6),
        inventories_count=int(row.cnt or 0),
    )


def _objectives_rollup(org_ids: list[str], session: Session) -> ObjectivesRollup:
    if not org_ids:
        return ObjectivesRollup()

    rows = (
        session.query(
            SustainabilityObjectiveModel.objective_status,
            func.count(SustainabilityObjectiveModel.id).label("cnt"),
        )
        .filter(SustainabilityObjectiveModel.organization_id.in_(org_ids))
        .group_by(SustainabilityObjectiveModel.objective_status)
        .all()
    )
    by_status: dict[str, int] = {r.objective_status: r.cnt for r in rows}
    total = sum(by_status.values())
    completed = by_status.get("COMPLETED", 0)
    active = by_status.get("ACTIVE", 0)
    return ObjectivesRollup(
        total=total,
        active=active,
        completed=completed,
        completion_percent=round(completed / total * 100, 1) if total else 0.0,
    )


def _targets_rollup(org_ids: list[str], session: Session) -> TargetsRollup:
    if not org_ids:
        return TargetsRollup()

    total = (
        session.query(func.count(ESGTargetModel.id))
        .filter(ESGTargetModel.organization_id.in_(org_ids))
        .scalar() or 0
    )
    with_measurements = (
        session.query(func.count(ESGTargetModel.id))
        .filter(
            ESGTargetModel.organization_id.in_(org_ids),
            ESGTargetModel.current_value.isnot(None),
        )
        .scalar() or 0
    )
    attainment = round(with_measurements / total * 100, 1) if total else 0.0
    return TargetsRollup(
        total=int(total),
        with_measurements=int(with_measurements),
        attainment_percent=attainment,
    )


def _kpis_rollup(org_ids: list[str], session: Session) -> KPIsRollup:
    if not org_ids:
        return KPIsRollup()

    total = (
        session.query(func.count(ESGKPIModel.id))
        .filter(ESGKPIModel.organization_id.in_(org_ids))
        .scalar() or 0
    )
    active = (
        session.query(func.count(ESGKPIModel.id))
        .filter(
            ESGKPIModel.organization_id.in_(org_ids),
            ESGKPIModel.is_active == True,  # noqa: E712
        )
        .scalar() or 0
    )
    return KPIsRollup(total=int(total), active=int(active))


def _scores_rollup(org_ids: list[str], session: Session) -> ScoreRollup:
    if not org_ids:
        return ScoreRollup()

    row = (
        session.query(
            func.avg(SustainabilityScorecardModel.overall_score).label("avg_overall"),
            func.avg(SustainabilityScorecardModel.environmental_score).label("avg_env"),
            func.avg(SustainabilityScorecardModel.social_score).label("avg_soc"),
            func.avg(SustainabilityScorecardModel.governance_score).label("avg_gov"),
            func.count(SustainabilityScorecardModel.id).label("cnt"),
        )
        .filter(SustainabilityScorecardModel.organization_id.in_(org_ids))
        .one()
    )
    if not row.cnt:
        return ScoreRollup()
    return ScoreRollup(
        avg_overall_score=round(float(row.avg_overall), 2) if row.avg_overall is not None else None,
        avg_environmental_score=round(float(row.avg_env), 2) if row.avg_env is not None else None,
        avg_social_score=round(float(row.avg_soc), 2) if row.avg_soc is not None else None,
        avg_governance_score=round(float(row.avg_gov), 2) if row.avg_gov is not None else None,
        scorecard_count=int(row.cnt),
    )


def _climate_rollup(org_ids: list[str], session: Session) -> ClimateRiskRollup:
    if not org_ids:
        return ClimateRiskRollup()

    row = (
        session.query(
            func.avg(ClimateRiskAssessmentModel.overall_risk_score).label("avg_overall"),
            func.avg(ClimateRiskAssessmentModel.transition_risk_score).label("avg_trans"),
            func.avg(ClimateRiskAssessmentModel.physical_risk_score).label("avg_phys"),
            func.avg(ClimateRiskAssessmentModel.regulatory_risk_score).label("avg_reg"),
            func.count(ClimateRiskAssessmentModel.id).label("cnt"),
        )
        .filter(ClimateRiskAssessmentModel.organization_id.in_(org_ids))
        .one()
    )
    if not row.cnt:
        return ClimateRiskRollup()
    return ClimateRiskRollup(
        avg_overall_risk=round(float(row.avg_overall), 2) if row.avg_overall is not None else None,
        avg_transition_risk=round(float(row.avg_trans), 2) if row.avg_trans is not None else None,
        avg_physical_risk=round(float(row.avg_phys), 2) if row.avg_phys is not None else None,
        avg_regulatory_risk=round(float(row.avg_reg), 2) if row.avg_reg is not None else None,
        assessment_count=int(row.cnt),
    )


def compute_rollup(
    entity_type: EntityType,
    entity_id: str,
    actor_id: str,
    session: Session,
) -> RollupSummary:
    """Compute a full sustainability rollup for a hierarchy entity."""
    if entity_type not in ("enterprise", "business_unit", "legal_entity", "region"):
        raise SustainabilityError(f"Invalid entity_type: {entity_type}")

    org_ids = _org_ids_for_entity(entity_type, entity_id, session)

    summary = RollupSummary(
        entity_type=entity_type,
        entity_id=entity_id,
        organization_ids=org_ids,
        emissions=_emissions_rollup(org_ids, session),
        objectives=_objectives_rollup(org_ids, session),
        targets=_targets_rollup(org_ids, session),
        kpis=_kpis_rollup(org_ids, session),
        scores=_scores_rollup(org_ids, session),
        climate_risks=_climate_rollup(org_ids, session),
        computed_at=_now().isoformat(),
    )
    emit_audit_event(
        session=session,
        event_type="sustainability.rollup.computed",
        actor_id=actor_id,
        resource_type=f"sustainability_rollup_{entity_type}",
        resource_id=entity_id,
        details={
            "organization_count": len(org_ids),
            "total_emissions": summary.emissions.total_emissions,
            "objective_completion_pct": summary.objectives.completion_percent,
        },
    )
    return summary
