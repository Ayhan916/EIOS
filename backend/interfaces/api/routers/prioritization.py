"""Prioritisation API — GAP-18 / CSDDD Art. 10.

Endpoints:
  POST /prioritization/compute          Recompute full ranking for the org
  GET  /prioritization/                 Current ranking
  PATCH /prioritization/{id}/override   Manual override with mandatory comment
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.due_diligence.prioritization_engine import compute_prioritization
from domain.enums import EntityStatus
from domain.prioritization import PrioritizationDecision
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.repositories.prioritization import (
    SQLPrioritizationRepository,
)
from infrastructure.persistence.repositories.supplier import SQLSupplierRepository
from infrastructure.persistence.repositories.supplier_score import (
    SQLSupplierScoreRepository,
)
from interfaces.api.deps import get_current_user, get_db, require_analyst

router = APIRouter(prefix="/prioritization", tags=["prioritization"])

# ── Schemas ────────────────────────────────────────────────────────────────────


class PrioritizationComputeRequest(BaseModel):
    resource_capacity_per_quarter: int = Field(
        default=4,
        ge=1,
        le=100,
        description="Number of supplier audits/assessments possible per quarter",
    )


class PrioritizationDecisionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    organization_id: str
    supplier_id: str
    supplier_name: str
    severity_weight: float
    probability_weight: float
    people_affected_weight: float
    priority_score: float
    priority_rank: int
    resource_capacity_per_quarter: int
    reasoning: str
    overridden_manually: bool
    override_comment: str | None
    decided_by_user_id: str
    decided_at: datetime
    regulation_refs: str
    created_at: datetime
    updated_at: datetime


class OverrideRequest(BaseModel):
    new_rank: int = Field(ge=1, description="New rank to assign; other ranks are shifted")
    override_comment: str = Field(min_length=10, description="Mandatory justification for override")


class PrioritizationRankingResponse(BaseModel):
    organization_id: str
    total_suppliers: int
    resource_capacity_per_quarter: int
    decisions: list[PrioritizationDecisionResponse]
    computed_at: datetime | None


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_finding_counts(session: AsyncSession, organization_id: str) -> dict[str, int]:
    """Count open findings per supplier via assessment join."""
    stmt = (
        select(AssessmentModel.supplier_id, func.count(FindingModel.id).label("n"))
        .join(FindingModel, FindingModel.assessment_id == AssessmentModel.id)
        .where(
            AssessmentModel.organization_id == organization_id,
            AssessmentModel.supplier_id.isnot(None),
        )
        .group_by(AssessmentModel.supplier_id)
    )
    result = await session.execute(stmt)
    return {str(row.supplier_id): row.n for row in result.all()}


def _decision_to_response(d: PrioritizationDecision) -> PrioritizationDecisionResponse:
    return PrioritizationDecisionResponse(
        id=d.id,
        organization_id=d.organization_id,
        supplier_id=d.supplier_id,
        supplier_name=d.supplier_name,
        severity_weight=d.severity_weight,
        probability_weight=d.probability_weight,
        people_affected_weight=d.people_affected_weight,
        priority_score=d.priority_score,
        priority_rank=d.priority_rank,
        resource_capacity_per_quarter=d.resource_capacity_per_quarter,
        reasoning=d.reasoning,
        overridden_manually=d.overridden_manually,
        override_comment=d.override_comment,
        decided_by_user_id=d.decided_by_user_id,
        decided_at=d.decided_at,
        regulation_refs=d.regulation_refs,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post(
    "/compute",
    response_model=PrioritizationRankingResponse,
    dependencies=[Depends(require_analyst)],
    summary="Recompute prioritisation ranking for the organisation",
)
async def compute_ranking(
    body: PrioritizationComputeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> PrioritizationRankingResponse:
    """Runs the CSDDD Art. 10 scoring engine and persists a fresh ranking.

    Previous decisions are deleted before new ones are inserted so each
    compute call produces a complete, consistent snapshot.
    """
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No organisation associated with user")

    # Gather inputs
    supplier_repo = SQLSupplierRepository(db)
    score_repo = SQLSupplierScoreRepository(db)
    prio_repo = SQLPrioritizationRepository(db)

    suppliers = await supplier_repo.list_by_organization(org_id)
    supplier_dicts = [
        {"id": s.id, "name": s.name, "supplier_tier": getattr(s, "supplier_tier", "Tier 1")}
        for s in suppliers
    ]

    latest_scores = await score_repo.get_latest_for_org(org_id)
    scores_map: dict[str, dict] = {
        sc.supplier_id: {"risk_band": sc.risk_band.value, "risk_score": sc.risk_score}
        for sc in latest_scores
    }

    finding_counts = await _get_finding_counts(db, org_id)

    # Compute
    ranked = compute_prioritization(
        organization_id=org_id,
        suppliers=supplier_dicts,
        supplier_scores=scores_map,
        finding_counts=finding_counts,
        resource_capacity_per_quarter=body.resource_capacity_per_quarter,
        decided_by_user_id=str(current_user.id),
    )

    # Persist — clear old decisions first
    await prio_repo.delete_all_by_org(org_id)

    saved: list[PrioritizationDecision] = []
    now = datetime.now(UTC)
    for item in ranked:
        decision = PrioritizationDecision(
            organization_id=org_id,
            supplier_id=item["supplier_id"],
            supplier_name=item["supplier_name"],
            severity_weight=item["severity_weight"],
            probability_weight=item["probability_weight"],
            people_affected_weight=item["people_affected_weight"],
            priority_score=item["priority_score"],
            priority_rank=item["priority_rank"],
            resource_capacity_per_quarter=item["resource_capacity_per_quarter"],
            reasoning=item["reasoning"],
            decided_by_user_id=item["decided_by_user_id"],
            decided_at=now,
            regulation_refs=item["regulation_refs"],
            status=EntityStatus.ACTIVE,
            created_by=str(current_user.id),
        )
        await prio_repo.create(decision)
        saved.append(decision)

    await db.commit()

    return PrioritizationRankingResponse(
        organization_id=org_id,
        total_suppliers=len(saved),
        resource_capacity_per_quarter=body.resource_capacity_per_quarter,
        decisions=[_decision_to_response(d) for d in saved],
        computed_at=now,
    )


@router.get(
    "/",
    response_model=PrioritizationRankingResponse,
    dependencies=[Depends(require_analyst)],
    summary="Current prioritisation ranking",
)
async def get_ranking(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> PrioritizationRankingResponse:
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No organisation associated with user")

    repo = SQLPrioritizationRepository(db)
    decisions = await repo.list_by_org(org_id)

    capacity = decisions[0].resource_capacity_per_quarter if decisions else 4
    computed_at = decisions[0].decided_at if decisions else None

    return PrioritizationRankingResponse(
        organization_id=org_id,
        total_suppliers=len(decisions),
        resource_capacity_per_quarter=capacity,
        decisions=[_decision_to_response(d) for d in decisions],
        computed_at=computed_at,
    )


@router.patch(
    "/{decision_id}/override",
    response_model=PrioritizationDecisionResponse,
    dependencies=[Depends(require_analyst)],
    summary="Manual override of a supplier's priority rank",
)
async def override_rank(
    decision_id: str,
    body: OverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> PrioritizationDecisionResponse:
    """Override a supplier's auto-computed rank.

    The override_comment is mandatory (CSDDD Art. 10 requires documented
    justification for all prioritisation decisions). Other suppliers'
    ranks are adjusted to maintain a gapless sequence.
    """
    org_id = current_user.organization_id
    repo = SQLPrioritizationRepository(db)

    decision = await repo.get(decision_id)
    if decision is None or decision.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")

    old_rank = decision.priority_rank
    new_rank = body.new_rank

    # Shift other decisions to make room
    all_decisions = await repo.list_by_org(org_id)
    for d in all_decisions:
        if d.id == decision_id:
            continue
        if old_rank < new_rank:
            if old_rank < d.priority_rank <= new_rank:
                d.priority_rank -= 1
                d.updated_at = datetime.now(UTC)
                await repo.update(d)
        else:
            if new_rank <= d.priority_rank < old_rank:
                d.priority_rank += 1
                d.updated_at = datetime.now(UTC)
                await repo.update(d)

    # Apply override
    decision.priority_rank = new_rank
    decision.overridden_manually = True
    decision.override_comment = body.override_comment
    decision.decided_by_user_id = str(current_user.id)
    decision.decided_at = datetime.now(UTC)
    decision.updated_by = str(current_user.id)
    decision.updated_at = datetime.now(UTC)
    await repo.update(decision)

    await db.commit()
    return _decision_to_response(decision)
