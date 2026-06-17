from fastapi import APIRouter, Depends, HTTPException, Query, status

from domain.risk import Risk
from domain.user import User
from infrastructure.persistence.repositories import SQLAssessmentRepository, SQLRiskRepository
from interfaces.api.deps import (
    get_assessment_repo,
    get_current_user,
    get_risk_repo,
    require_admin,
    require_analyst,
)
from interfaces.api.schemas.risk import RiskCreate, RiskResponse

router = APIRouter(
    prefix="/risks",
    tags=["risks"],
    dependencies=[Depends(get_current_user)],
)


async def _assert_risk_org_access(
    risk: Risk,
    user_org_id: str | None,
    assessment_repo: SQLAssessmentRepository,
) -> None:
    """Verify the risk's parent assessment belongs to the user's org."""
    if not risk.assessment_id or not user_org_id:
        return
    assessment = await assessment_repo.get_by_id(risk.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    if assessment.organization_id and assessment.organization_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")


@router.post(
    "/",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_risk(
    body: RiskCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLRiskRepository = Depends(get_risk_repo),
) -> RiskResponse:
    risk = Risk(
        title=body.title,
        description=body.description,
        risk_level=body.risk_level,
        category=body.category,
        assessment_id=body.assessment_id,
        sector_id=body.sector_id,
        probability=body.probability,
        impact=body.impact,
        confidence=body.confidence,
        reasoning=body.reasoning,
        uncertainty=body.uncertainty,
        created_by=current_user.id,
    )
    saved = await repo.save(risk)
    return RiskResponse.model_validate(saved)


@router.get("/", response_model=list[RiskResponse])
async def list_risks(
    sector_id: str | None = Query(default=None),
    assessment_id: str | None = Query(default=None),
    repo: SQLRiskRepository = Depends(get_risk_repo),
) -> list[RiskResponse]:
    if sector_id:
        results = await repo.list_by_sector(sector_id)
    elif assessment_id:
        results = await repo.list_by_assessment(assessment_id)
    else:
        results = []
    return [RiskResponse.model_validate(r) for r in results]


@router.get("/{risk_id}", response_model=RiskResponse)
async def get_risk(
    risk_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLRiskRepository = Depends(get_risk_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> RiskResponse:
    risk = await repo.get_by_id(risk_id)
    if risk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    await _assert_risk_org_access(risk, current_user.organization_id, assessment_repo)
    return RiskResponse.model_validate(risk)


@router.delete(
    "/{risk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_risk(
    risk_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLRiskRepository = Depends(get_risk_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> None:
    existing = await repo.get_by_id(risk_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    await _assert_risk_org_access(existing, current_user.organization_id, assessment_repo)
    await repo.delete(risk_id)
