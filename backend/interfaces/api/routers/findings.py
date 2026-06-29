from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from domain.finding import Finding
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLFindingEvidenceLinkRepository,
    SQLFindingRepository,
)
from interfaces.api.deps import (
    get_assessment_repo,
    get_current_user,
    get_finding_evidence_link_repo,
    get_finding_repo,
    require_admin,
    require_analyst,
    scope_gate,
)
from interfaces.api.routers.api_platform import dispatch_webhook_event
from interfaces.api.schemas.finding import (
    FindingCreate,
    FindingEvidenceLinkResponse,
    FindingResponse,
)
from interfaces.api.schemas.risk import RiskResponse

router = APIRouter(
    prefix="/findings",
    tags=["findings"],
    dependencies=[Depends(get_current_user), Depends(scope_gate("findings:read", "assessments:write"))],
)


async def _assert_finding_org_access(
    finding: Finding,
    user_org_id: str | None,
    assessment_repo: SQLAssessmentRepository,
) -> None:
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
    background_tasks: BackgroundTasks,
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
    if current_user.organization_id:
        background_tasks.add_task(
            dispatch_webhook_event,
            current_user.organization_id,
            "finding.created",
            {"finding_id": saved.id, "title": saved.title, "severity": saved.severity},
        )
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


@router.get(
    "/{finding_id}/evidence-links",
    response_model=list[FindingEvidenceLinkResponse],
    summary="List evidence links for a finding (M25 traceability)",
)
async def list_finding_evidence_links(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLFindingRepository = Depends(get_finding_repo),
    link_repo: SQLFindingEvidenceLinkRepository = Depends(get_finding_evidence_link_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> list[FindingEvidenceLinkResponse]:
    finding = await repo.get_by_id(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await _assert_finding_org_access(finding, current_user.organization_id, assessment_repo)
    links = await link_repo.list_by_finding(finding_id)
    return [FindingEvidenceLinkResponse.model_validate(lnk) for lnk in links]


@router.get(
    "/{finding_id}/risks",
    response_model=list[RiskResponse],
    summary="List risks linked to a finding via risk_finding association",
)
async def list_finding_risks(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLFindingRepository = Depends(get_finding_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> list[RiskResponse]:
    from sqlalchemy.ext.asyncio import AsyncSession
    from interfaces.api.deps import get_db
    from infrastructure.persistence.models.finding import FindingModel
    from infrastructure.persistence.models.risk import RiskModel
    from sqlalchemy import select
    finding = await repo.get_by_id(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await _assert_finding_org_access(finding, current_user.organization_id, assessment_repo)
    # Load via ORM relationship using a raw query on the association table
    from infrastructure.persistence.models.associations import risk_finding
    from infrastructure.persistence.database import AsyncSessionFactory
    async with AsyncSessionFactory() as session:
        rows = (await session.execute(
            select(RiskModel)
            .join(risk_finding, RiskModel.id == risk_finding.c.risk_id)
            .where(risk_finding.c.finding_id == finding_id)
        )).scalars().all()
    return [RiskResponse.model_validate(r) for r in rows]


@router.post(
    "/{finding_id}/risks/{risk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Link a risk to a finding",
)
async def link_finding_risk(
    finding_id: str,
    risk_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLFindingRepository = Depends(get_finding_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> None:
    finding = await repo.get_by_id(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await _assert_finding_org_access(finding, current_user.organization_id, assessment_repo)
    from infrastructure.persistence.models.associations import risk_finding
    from infrastructure.persistence.database import AsyncSessionFactory
    from sqlalchemy import select, insert
    from infrastructure.persistence.models.risk import RiskModel
    async with AsyncSessionFactory() as session:
        risk_row = (await session.execute(
            select(RiskModel).where(RiskModel.id == risk_id)
        )).scalar_one_or_none()
        if risk_row is None:
            raise HTTPException(status_code=404, detail="Risk not found")
        existing = (await session.execute(
            select(risk_finding).where(
                risk_finding.c.risk_id == risk_id,
                risk_finding.c.finding_id == finding_id,
            )
        )).first()
        if not existing:
            await session.execute(insert(risk_finding).values(risk_id=risk_id, finding_id=finding_id))
            await session.commit()


@router.delete(
    "/{finding_id}/risks/{risk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlink a risk from a finding",
)
async def unlink_finding_risk(
    finding_id: str,
    risk_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLFindingRepository = Depends(get_finding_repo),
    assessment_repo: SQLAssessmentRepository = Depends(get_assessment_repo),
) -> None:
    finding = await repo.get_by_id(finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await _assert_finding_org_access(finding, current_user.organization_id, assessment_repo)
    from infrastructure.persistence.models.associations import risk_finding
    from infrastructure.persistence.database import AsyncSessionFactory
    from sqlalchemy import delete as sa_delete
    async with AsyncSessionFactory() as session:
        await session.execute(
            sa_delete(risk_finding).where(
                risk_finding.c.risk_id == risk_id,
                risk_finding.c.finding_id == finding_id,
            )
        )
        await session.commit()


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
