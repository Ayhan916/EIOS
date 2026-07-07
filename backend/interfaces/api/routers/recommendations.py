from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

import application.audit as audit_factory
import application.notification_service as notification_service
from domain.enums import NotificationType
from domain.recommendation import Recommendation
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLAuditEventRepository,
    SQLRecommendationRepository,
    SQLUserRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_audit_event_repo,
    get_current_user,
    get_db,
    get_recommendation_repo,
    get_user_repo,
    require_admin,
    require_analyst,
    scope_gate,
)
from interfaces.api.routers.api_platform import dispatch_webhook_event
from interfaces.api.schemas.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    RecommendationUpdate,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("recommendations:read", "assessments:write")),
    ],
)


async def _assert_rec_org_access(
    rec: Recommendation,
    user_org_id: str | None,
    assessment_repo: SQLAssessmentRepository,
) -> None:
    """Verify the recommendation's parent assessment belongs to the user's org."""
    if not rec.assessment_id or not user_org_id:
        return
    assessment = await assessment_repo.get_by_id(rec.assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        )
    if assessment.organization_id and assessment.organization_id != user_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        )


@router.get("/", response_model=list[RecommendationResponse])
async def list_recommendations(
    assessment_id: str | None = Query(default=None),
    repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
) -> list[RecommendationResponse]:
    if not assessment_id:
        return []
    results = await repo.list_by_assessment(assessment_id)
    return [RecommendationResponse.model_validate(r) for r in results]


@router.post(
    "/",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_recommendation(
    body: RecommendationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
) -> RecommendationResponse:
    recommendation = Recommendation(
        title=body.title,
        description=body.description,
        priority=body.priority,
        confidence=body.confidence,
        reasoning=body.reasoning,
        action_required=body.action_required,
        due_date=body.due_date,
        assessment_id=body.assessment_id,
        created_by=current_user.id,
        expected_benefit=body.expected_benefit,
        expected_risk=body.expected_risk,
        expected_roi=body.expected_roi,
        implementation_complexity=body.implementation_complexity,
    )
    saved = await repo.save(recommendation)
    if current_user.organization_id:
        background_tasks.add_task(
            dispatch_webhook_event,
            current_user.organization_id,
            "recommendation.created",
            {"recommendation_id": saved.id, "title": saved.title, "priority": saved.priority},
        )
    return RecommendationResponse.model_validate(saved)


_DECISION_MAP = {
    "in_progress": "ChangesRequested",
    "resolved": "Approved",
    "verified": "Approved",
}


@router.get("/decisions")
async def list_decisions(
    limit: int = Query(default=100, le=500),
    current_user: User = Depends(get_current_user),
    repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
) -> list[dict]:
    if not current_user.organization_id:
        return []
    results = []
    for rec_status in (
        "in_progress",
        "resolved",
        "verified",
    ):
        from domain.enums import ActionStatus as _AS

        recs = await repo.list_by_org_and_status(
            current_user.organization_id,
            _AS(rec_status),
        )
        results.extend(recs)
    results = results[:limit]
    return [
        {
            "id": r.id,
            "title": r.title,
            "decision": _DECISION_MAP.get(r.action_status.value, "ChangesRequested"),
            "decided_by": r.approved_by or r.created_by or "",
            "decided_at": r.updated_at.isoformat() if r.updated_at else "",
            "comment": r.description[:120] if r.description else None,
            "priority": r.priority.value if hasattr(r.priority, "value") else str(r.priority),
            "entity_type": "recommendation",
        }
        for r in results
    ]


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> RecommendationResponse:
    recommendation = await repo.get_by_id(recommendation_id)
    if recommendation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        )
    await _assert_rec_org_access(recommendation, current_user.organization_id, assessment_repo)
    return RecommendationResponse.model_validate(recommendation)


@router.patch("/{recommendation_id}", response_model=RecommendationResponse)
async def update_recommendation_action(
    recommendation_id: str,
    body: RecommendationUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    audit_repo: SQLAuditEventRepository = Depends(get_audit_event_repo),
    user_repo: SQLUserRepository = Depends(get_user_repo),
) -> RecommendationResponse:
    existing = await repo.get_by_id(recommendation_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        )
    await _assert_rec_org_access(existing, current_user.organization_id, assessment_repo)

    changed = body.model_fields_set

    if "action_status" in changed and body.action_status is not None:
        old_status = existing.action_status.value
        existing.action_status = body.action_status
        await audit_repo.save(
            audit_factory.recommendation_status_changed(
                recommendation_id=recommendation_id,
                actor_id=current_user.id,
                old_status=old_status,
                new_status=body.action_status.value,
                actor_email=current_user.email,
            )
        )

    if "due_date" in changed:
        existing.due_date = body.due_date
        await audit_repo.save(
            audit_factory.recommendation_due_date_changed(
                recommendation_id=recommendation_id,
                actor_id=current_user.id,
                new_due_date=str(body.due_date),
                actor_email=current_user.email,
            )
        )

    for field in ("expected_benefit", "expected_risk", "expected_roi", "implementation_complexity"):
        if field in changed:
            setattr(existing, field, getattr(body, field))

    if "assigned_to_id" in changed and body.assigned_to_id is not None:
        existing.assigned_to_id = body.assigned_to_id
        await audit_repo.save(
            audit_factory.recommendation_assigned(
                recommendation_id=recommendation_id,
                actor_id=current_user.id,
                assigned_to_id=body.assigned_to_id,
                actor_email=current_user.email,
            )
        )
        assignee = await user_repo.get_by_id(body.assigned_to_id)
        if assignee and assignee.organization_id == current_user.organization_id:
            await notification_service.notify(
                session=session,
                user_id=assignee.id,
                organization_id=assignee.organization_id or "",
                notification_type=NotificationType.RECOMMENDATION_ASSIGNED,
                title="New recommendation assigned to you",
                body=f"'{existing.title}' has been assigned to you by {current_user.display_name}.",
                entity_type="recommendation",
                entity_id=recommendation_id,
                dedupe_key=f"rec_assigned:{recommendation_id}:{assignee.id}",
                user_email=assignee.email,
            )

    existing.updated_by = current_user.id
    saved = await repo.save(existing)
    return RecommendationResponse.model_validate(saved)


@router.delete(
    "/{recommendation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_recommendation(
    recommendation_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> None:
    existing = await repo.get_by_id(recommendation_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        )
    await _assert_rec_org_access(existing, current_user.organization_id, assessment_repo)
    await repo.delete(recommendation_id)
