from fastapi import APIRouter, Depends, HTTPException, Query, status

from domain.finding import Finding
from domain.user import User
from infrastructure.persistence.repositories import SQLAssessmentRepository, SQLFindingRepository
from interfaces.api.deps import (
    get_assessment_repo,
    get_current_user,
    get_finding_repo,
    require_admin,
    require_analyst,
)
from interfaces.api.schemas.finding import FindingCreate, FindingResponse

router = APIRouter(
    prefix="/findings",
    tags=["findings"],
    dependencies=[Depends(get_current_user)],
)


async def _assert_finding_org_access(
    finding: Finding,
    user_org_id: str | None,
    assessment_repo: SQLAssessmentRepository,
) -> None:
    """Verify the finding's parent assessment belongs to the user's org."""
    if not finding.assessment_id or not user_org_id:
        return
    assessment = await assessment_repo.get_by_id(finding.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    if assessment.organization_id and assessment.organization_id != user_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")


@router.get("/", response_model=list[FindingResponse])
async def list_findings(
    assessment_id: str | None = Query(default=None),
    repo: SQLFindingRepository = Depends(get_finding_repo),
) -> list[FindingResponse]:
    if not assessment_id:
        return []
    results = await repo.list_by_assessment(assessment_id)
    return [FindingResponse.model_validate(f) for f in results]


@router.post(
    "/",
    response_model=FindingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_finding(
    body: FindingCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLFindingRepository = Depends(get_finding_repo),
) -> FindingResponse:
    finding = Finding(
        title=body.title,
        description=body.description,
        assessment_id=body.assessment_id,
        category=body.category,
        severity=body.severity,
        confidence=body.confidence,
        reasoning=body.reasoning,
        uncertainty=body.uncertainty,
        created_by=current_user.id,
    )
    saved = await repo.save(finding)
    return FindingResponse.model_validate(saved)


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLFindingRepository = Depends(get_finding_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> FindingResponse:
    finding = await repo.get_by_id(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await _assert_finding_org_access(finding, current_user.organization_id, assessment_repo)
    return FindingResponse.model_validate(finding)


@router.delete(
    "/{finding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLFindingRepository = Depends(get_finding_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> None:
    existing = await repo.get_by_id(finding_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await _assert_finding_org_access(existing, current_user.organization_id, assessment_repo)
    await repo.delete(finding_id)
