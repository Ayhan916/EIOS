from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from domain.recommendation import Recommendation
from domain.user import User
from infrastructure.persistence.repositories import SQLAssessmentRepository, SQLRecommendationRepository
from interfaces.api.deps import (
    get_assessment_repo,
    get_current_user,
    get_recommendation_repo,
    require_analyst,
    require_admin,
)
from interfaces.api.schemas.recommendation import RecommendationCreate, RecommendationResponse

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    dependencies=[Depends(get_current_user)],
)


async def _assert_rec_org_access(
    rec: Recommendation,
    user_org_id: Optional[str],
    assessment_repo: SQLAssessmentRepository,
) -> None:
    """Verify the recommendation's parent assessment belongs to the user's org."""
    if not rec.assessment_id or not user_org_id:
        return
    assessment = await assessment_repo.get_by_id(rec.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    if assessment.organization_id and assessment.organization_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")


@router.get("/", response_model=list[RecommendationResponse])
async def list_recommendations(
    assessment_id: Optional[str] = Query(default=None),
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
        created_by=current_user.id,
    )
    saved = await repo.save(recommendation)
    return RecommendationResponse.model_validate(saved)


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLRecommendationRepository = Depends(get_recommendation_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> RecommendationResponse:
    recommendation = await repo.get_by_id(recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    await _assert_rec_org_access(recommendation, current_user.organization_id, assessment_repo)
    return RecommendationResponse.model_validate(recommendation)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    await _assert_rec_org_access(existing, current_user.organization_id, assessment_repo)
    await repo.delete(recommendation_id)
