from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.risk import Risk
from domain.user import User
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.repositories import SQLAssessmentRepository, SQLRiskRepository
from interfaces.api.deps import (
    get_assessment_repo,
    get_current_user,
    get_db,
    get_risk_repo,
    require_admin,
    require_analyst,
    scope_gate,
)
from interfaces.api.routers.api_platform import dispatch_webhook_event
from interfaces.api.schemas.finding import FindingResponse
from interfaces.api.schemas.risk import RiskCreate, RiskPatch, RiskResponse

router = APIRouter(
    prefix="/risks",
    tags=["risks"],
    dependencies=[Depends(get_current_user), Depends(scope_gate("risks:read", "assessments:write"))],
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
    background_tasks: BackgroundTasks,
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
        severity_score=body.severity_score,
        probability_score=body.probability_score,
        created_by=current_user.id,
    )
    saved = await repo.save(risk)
    if current_user.organization_id:
        background_tasks.add_task(
            dispatch_webhook_event,
            current_user.organization_id,
            "risk.created",
            {"risk_id": saved.id, "title": saved.title, "risk_level": saved.risk_level},
        )
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


@router.patch(
    "/{risk_id}",
    response_model=RiskResponse,
    dependencies=[Depends(require_analyst)],
    summary="Update risk status, level, or owner inline",
)
async def patch_risk(
    risk_id: str,
    body: RiskPatch,
    current_user: User = Depends(get_current_user),
    repo: SQLRiskRepository = Depends(get_risk_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
    session: AsyncSession = Depends(get_db),
) -> RiskResponse:
    existing = await repo.get_by_id(risk_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    await _assert_risk_org_access(existing, current_user.organization_id, assessment_repo)

    _VALID_STATUSES = {"Active", "Reviewed", "Archived"}
    _VALID_LEVELS = {"Critical", "High", "Medium", "Low"}

    values: dict = {"updated_at": datetime.now(timezone.utc)}
    if body.status is not None:
        if body.status not in _VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of {_VALID_STATUSES}")
        values["status"] = body.status
    if body.risk_level is not None:
        if body.risk_level not in _VALID_LEVELS:
            raise HTTPException(status_code=422, detail=f"risk_level must be one of {_VALID_LEVELS}")
        values["risk_level"] = body.risk_level
    if body.owner is not None:
        values["owner"] = body.owner or None
    if body.severity_score is not None:
        values["severity_score"] = body.severity_score
    if body.probability_score is not None:
        values["probability_score"] = body.probability_score

    await session.execute(update(RiskModel).where(RiskModel.id == risk_id).values(**values))
    await session.commit()

    updated = await repo.get_by_id(risk_id)
    return RiskResponse.model_validate(updated)


@router.get(
    "/{risk_id}/findings",
    response_model=list[FindingResponse],
    summary="List findings linked to a risk via risk_finding association",
)
async def list_risk_findings(
    risk_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLRiskRepository = Depends(get_risk_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> list[FindingResponse]:
    from infrastructure.persistence.models.finding import FindingModel
    from infrastructure.persistence.models.associations import risk_finding
    from infrastructure.persistence.database import AsyncSessionFactory
    from sqlalchemy import select
    risk = await repo.get_by_id(risk_id)
    if risk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk not found")
    await _assert_risk_org_access(risk, current_user.organization_id, assessment_repo)
    async with AsyncSessionFactory() as session:
        rows = (await session.execute(
            select(FindingModel)
            .join(risk_finding, FindingModel.id == risk_finding.c.finding_id)
            .where(risk_finding.c.risk_id == risk_id)
        )).scalars().all()
    return [FindingResponse.model_validate(f) for f in rows]


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
