"""Self-Improvement Loop API (GAP-05).

Endpoints:
  POST /self-improvement/detect              — detect weaknesses + generate proposals (admin)
  GET  /self-improvement/proposals           — list proposals
  GET  /self-improvement/proposals/{id}      — single proposal
  PATCH /self-improvement/proposals/{id}/approve  — Founder approves (admin)
  PATCH /self-improvement/proposals/{id}/reject   — Founder rejects (admin)
  PATCH /self-improvement/proposals/{id}/verify   — compare before/after eval (admin)
  GET  /self-improvement/summary             — status counts + health delta

Security:
  - detect/approve/reject/verify require admin role
  - list/get require analyst role
  - AI agents MUST NOT call approve/reject/verify
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.evaluation.weakness_detector import detect_weaknesses
from domain.improvement import ImprovementProposal
from domain.user import User
from infrastructure.persistence.repositories.evaluation import (
    SQLBenchmarkResultRepository,
    SQLEvaluationRunRepository,
)
from infrastructure.persistence.repositories.improvement import SQLImprovementRepository
from interfaces.api.deps import get_current_user, get_db, require_admin, require_analyst

router = APIRouter(prefix="/self-improvement", tags=["self-improvement"])


# ── Response schemas ──────────────────────────────────────────────────────────


class ProposalResponse(BaseModel):
    id: str
    weakness_type: str
    affected_module: str
    current_value: float
    target_value: float
    expected_impact: float
    priority_score: float
    title: str
    description: str
    suggested_action: str
    approval_status: str
    approved_by_user_id: str | None
    approved_at: datetime | None
    rejected_by_user_id: str | None
    rejected_at: datetime | None
    reject_reason: str | None
    before_evaluation_run_id: str | None
    after_evaluation_run_id: str | None
    verified_improvement: float | None
    verified_at: datetime | None
    created_at: datetime


class DetectResponse(BaseModel):
    proposals_created: int
    proposals: list[ProposalResponse]
    evaluation_run_id: str | None
    message: str


class SummaryResponse(BaseModel):
    status_counts: dict[str, int]
    total: int
    open_draft: int
    approved: int
    verified: int
    rejected: int
    latest_health_score: float | None
    latest_benchmark_status: str | None


class ApproveRequest(BaseModel):
    pass


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)


class VerifyRequest(BaseModel):
    after_evaluation_run_id: str = Field(..., min_length=36, max_length=36)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_response(p: ImprovementProposal) -> ProposalResponse:
    return ProposalResponse(
        id=p.id,
        weakness_type=p.weakness_type,
        affected_module=p.affected_module,
        current_value=p.current_value,
        target_value=p.target_value,
        expected_impact=p.expected_impact,
        priority_score=p.priority_score,
        title=p.title,
        description=p.description,
        suggested_action=p.suggested_action,
        approval_status=p.approval_status,
        approved_by_user_id=p.approved_by_user_id,
        approved_at=p.approved_at,
        rejected_by_user_id=p.rejected_by_user_id,
        rejected_at=p.rejected_at,
        reject_reason=p.reject_reason,
        before_evaluation_run_id=p.before_evaluation_run_id,
        after_evaluation_run_id=p.after_evaluation_run_id,
        verified_improvement=p.verified_improvement,
        verified_at=p.verified_at,
        created_at=p.created_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/detect",
    response_model=DetectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Detect platform weaknesses and generate improvement proposals",
)
async def detect(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> DetectResponse:
    """Runs the deterministic weakness detector against the latest evaluation run.

    Creates DRAFT proposals for each detected weakness. Existing DRAFT proposals
    for the same weakness_type + affected_module are not duplicated — only new
    weaknesses generate new proposals.
    """
    run_repo = SQLEvaluationRunRepository(db)
    bm_repo = SQLBenchmarkResultRepository(db)
    imp_repo = SQLImprovementRepository(db)

    latest = await run_repo.get_latest()
    if latest is None:
        return DetectResponse(
            proposals_created=0,
            proposals=[],
            evaluation_run_id=None,
            message="No evaluation run found. Trigger an evaluation first.",
        )

    trends = await run_repo.list_recent(limit=6)
    trends_asc = list(reversed(trends))  # oldest first for trend analysis
    bm_results = await bm_repo.list_by_run(latest.id)

    new_proposals = detect_weaknesses(latest, bm_results, trends_asc)

    # Dedup: skip if same weakness_type + affected_module already has a DRAFT
    existing = await imp_repo.list_all(status_filter="DRAFT")
    existing_keys = {(p.weakness_type, p.affected_module) for p in existing}

    saved = []
    for proposal in new_proposals:
        key = (proposal.weakness_type, proposal.affected_module)
        if key in existing_keys:
            continue
        await imp_repo.save(proposal)
        saved.append(proposal)

    await db.commit()

    return DetectResponse(
        proposals_created=len(saved),
        proposals=[_to_response(p) for p in saved],
        evaluation_run_id=latest.id,
        message=(
            f"{len(saved)} new proposal(s) created from {len(new_proposals)} detected weakness(es)."
            if saved
            else "No new weaknesses detected (or all already have open DRAFT proposals)."
        ),
    )


@router.get(
    "/proposals",
    response_model=list[ProposalResponse],
    dependencies=[Depends(require_analyst)],
    summary="List improvement proposals",
)
async def list_proposals(
    approval_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> list[ProposalResponse]:
    imp_repo = SQLImprovementRepository(db)
    proposals = await imp_repo.list_all(status_filter=approval_status, limit=limit)
    return [_to_response(p) for p in proposals]


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalResponse,
    dependencies=[Depends(require_analyst)],
)
async def get_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> ProposalResponse:
    imp_repo = SQLImprovementRepository(db)
    proposal = await imp_repo.get_by_id(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return _to_response(proposal)


@router.patch(
    "/proposals/{proposal_id}/approve",
    response_model=ProposalResponse,
    dependencies=[Depends(require_admin)],
    summary="Founder approves an improvement proposal",
)
async def approve_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProposalResponse:
    """Human-only: Founder approves a DRAFT proposal → status becomes APPROVED.

    AI agents MUST NOT call this endpoint.
    """
    imp_repo = SQLImprovementRepository(db)
    proposal = await imp_repo.get_by_id(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.approval_status != "DRAFT":
        raise HTTPException(
            status_code=400,
            detail=f"Can only approve DRAFT proposals (current status: {proposal.approval_status})",
        )
    now = datetime.now(UTC)
    proposal.approval_status = "APPROVED"
    proposal.approved_by_user_id = str(current_user.id)
    proposal.approved_at = now
    proposal.updated_at = now
    await imp_repo.save(proposal)
    await db.commit()
    return _to_response(proposal)


@router.patch(
    "/proposals/{proposal_id}/reject",
    response_model=ProposalResponse,
    dependencies=[Depends(require_admin)],
    summary="Founder rejects an improvement proposal",
)
async def reject_proposal(
    proposal_id: str,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProposalResponse:
    """Human-only: Founder rejects a DRAFT proposal with a mandatory reason.

    AI agents MUST NOT call this endpoint.
    """
    imp_repo = SQLImprovementRepository(db)
    proposal = await imp_repo.get_by_id(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.approval_status not in ("DRAFT", "APPROVED"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject proposal with status: {proposal.approval_status}",
        )
    now = datetime.now(UTC)
    proposal.approval_status = "REJECTED"
    proposal.rejected_by_user_id = str(current_user.id)
    proposal.rejected_at = now
    proposal.reject_reason = body.reason
    proposal.updated_at = now
    await imp_repo.save(proposal)
    await db.commit()
    return _to_response(proposal)


@router.patch(
    "/proposals/{proposal_id}/verify",
    response_model=ProposalResponse,
    dependencies=[Depends(require_admin)],
    summary="Verify improvement — compare before and after evaluation runs",
)
async def verify_proposal(
    proposal_id: str,
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProposalResponse:
    """Human-triggered: compare before/after evaluation runs to measure improvement.

    The platform_health_score delta is stored as verified_improvement.
    Status becomes VERIFIED if improvement is positive, stays APPROVED otherwise.
    AI agents MUST NOT call this endpoint.
    """
    imp_repo = SQLImprovementRepository(db)
    run_repo = SQLEvaluationRunRepository(db)

    proposal = await imp_repo.get_by_id(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.approval_status not in ("APPROVED", "IN_PROGRESS"):
        raise HTTPException(
            status_code=400,
            detail="Only APPROVED or IN_PROGRESS proposals can be verified",
        )

    after_run = await run_repo.get_by_id(body.after_evaluation_run_id)
    if after_run is None:
        raise HTTPException(status_code=404, detail="After-evaluation run not found")

    # Compute improvement delta
    before_score = 0.0
    if proposal.before_evaluation_run_id:
        before_run = await run_repo.get_by_id(proposal.before_evaluation_run_id)
        if before_run:
            before_score = before_run.platform_health_score

    delta = after_run.platform_health_score - before_score
    now = datetime.now(UTC)
    proposal.after_evaluation_run_id = body.after_evaluation_run_id
    proposal.verified_improvement = round(delta, 2)
    proposal.verified_at = now
    proposal.approval_status = "VERIFIED" if delta > 0 else "APPROVED"
    proposal.updated_at = now
    await imp_repo.save(proposal)
    await db.commit()
    return _to_response(proposal)


@router.get(
    "/summary",
    response_model=SummaryResponse,
    dependencies=[Depends(require_analyst)],
    summary="Improvement proposal status summary",
)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> SummaryResponse:
    imp_repo = SQLImprovementRepository(db)
    run_repo = SQLEvaluationRunRepository(db)

    counts = await imp_repo.count_by_status()
    latest = await run_repo.get_latest()

    return SummaryResponse(
        status_counts=counts,
        total=sum(counts.values()),
        open_draft=counts.get("DRAFT", 0),
        approved=counts.get("APPROVED", 0),
        verified=counts.get("VERIFIED", 0),
        rejected=counts.get("REJECTED", 0),
        latest_health_score=latest.platform_health_score if latest else None,
        latest_benchmark_status=latest.benchmark_status if latest else None,
    )
