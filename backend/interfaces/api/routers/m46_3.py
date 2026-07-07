"""M46.3 — Scheduling, Milestones, Certificates & AI Risk Drafts router.

Endpoints:
  G-040  POST/GET   /remediation/{plan_id}/milestones
         PATCH/DELETE /remediation/milestones/{milestone_id}
  G-041  POST/GET   /assessments/schedules
         DELETE     /assessments/schedules/{schedule_id}
  G-046  POST/GET   /suppliers/{supplier_id}/certificates
         DELETE     /suppliers/{supplier_id}/certificates/{cert_id}
  G-056  POST       /surveillance/signals/{signal_id}/draft-risk
         GET        /risks/drafts
         POST       /risks/drafts/{draft_id}/accept
         POST       /risks/drafts/{draft_id}/reject
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.user import User
from interfaces.api.deps import get_current_user, get_db, require_admin, require_analyst
from interfaces.api.schemas.m46_3 import (
    AcceptRiskDraftRequest,
    AssessmentScheduleCreate,
    AssessmentScheduleResponse,
    DraftRiskFromSignalRequest,
    RemediationMilestoneCreate,
    RemediationMilestoneResponse,
    RemediationMilestoneUpdate,
    RiskDraftResponse,
    SupplierCertificateCreate,
    SupplierCertificateResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["M46.3 — Scheduling & Alerts"])

_ANALYST = Depends(require_analyst)
_ADMIN = Depends(require_admin)


# ─────────────────────────────────────────────────────────────────────────────
# G-040 — Remediation Milestones
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/remediation/{plan_id}/milestones",
    response_model=RemediationMilestoneResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_milestone(
    plan_id: str,
    body: RemediationMilestoneCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RemediationMilestoneResponse:
    from infrastructure.persistence.models.m46_3 import RemediationMilestoneModel  # noqa: PLC0415
    from infrastructure.persistence.models.supplier_portal import (
        RemediationPlanModel,  # noqa: PLC0415
    )

    plan = (
        await session.execute(
            select(RemediationPlanModel).where(
                RemediationPlanModel.id == plan_id,
                RemediationPlanModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Remediation plan not found"
        )

    now = datetime.now(UTC)
    milestone = RemediationMilestoneModel(
        id=str(uuid.uuid4()),
        plan_id=plan_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        milestone_status="open",
        sort_order=body.sort_order,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    session.add(milestone)
    await session.flush()
    logger.info("milestone_created", milestone_id=milestone.id, plan_id=plan_id)
    return RemediationMilestoneResponse.model_validate(milestone)


@router.get(
    "/remediation/{plan_id}/milestones",
    response_model=list[RemediationMilestoneResponse],
    dependencies=[_ANALYST],
)
async def list_milestones(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[RemediationMilestoneResponse]:
    from infrastructure.persistence.models.m46_3 import RemediationMilestoneModel  # noqa: PLC0415
    from infrastructure.persistence.models.supplier_portal import (
        RemediationPlanModel,  # noqa: PLC0415
    )

    plan = (
        await session.execute(
            select(RemediationPlanModel).where(
                RemediationPlanModel.id == plan_id,
                RemediationPlanModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Remediation plan not found"
        )

    result = await session.execute(
        select(RemediationMilestoneModel)
        .where(RemediationMilestoneModel.plan_id == plan_id)
        .order_by(RemediationMilestoneModel.sort_order, RemediationMilestoneModel.created_at)
    )
    return [RemediationMilestoneResponse.model_validate(m) for m in result.scalars().all()]


@router.patch(
    "/remediation/milestones/{milestone_id}",
    response_model=RemediationMilestoneResponse,
    dependencies=[_ANALYST],
)
async def update_milestone(
    milestone_id: str,
    body: RemediationMilestoneUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RemediationMilestoneResponse:
    from infrastructure.persistence.models.m46_3 import RemediationMilestoneModel  # noqa: PLC0415
    from infrastructure.persistence.models.supplier_portal import (
        RemediationPlanModel,  # noqa: PLC0415
    )

    milestone = (
        await session.execute(
            select(RemediationMilestoneModel).where(RemediationMilestoneModel.id == milestone_id)
        )
    ).scalar_one_or_none()
    if milestone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    # Scope check via plan → org
    plan = (
        await session.execute(
            select(RemediationPlanModel).where(
                RemediationPlanModel.id == milestone.plan_id,
                RemediationPlanModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    now = datetime.now(UTC)
    if body.title is not None:
        milestone.title = body.title
    if body.description is not None:
        milestone.description = body.description
    if body.due_date is not None:
        milestone.due_date = body.due_date
    if body.sort_order is not None:
        milestone.sort_order = body.sort_order
    if body.milestone_status is not None:
        milestone.milestone_status = body.milestone_status
        if body.milestone_status == "completed" and milestone.completed_at is None:
            milestone.completed_at = now
            milestone.completed_by = current_user.id
    milestone.updated_at = now
    await session.flush()
    return RemediationMilestoneResponse.model_validate(milestone)


@router.delete(
    "/remediation/milestones/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ADMIN],
)
async def delete_milestone(
    milestone_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    from infrastructure.persistence.models.m46_3 import RemediationMilestoneModel  # noqa: PLC0415
    from infrastructure.persistence.models.supplier_portal import (
        RemediationPlanModel,  # noqa: PLC0415
    )

    milestone = (
        await session.execute(
            select(RemediationMilestoneModel).where(RemediationMilestoneModel.id == milestone_id)
        )
    ).scalar_one_or_none()
    if milestone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    plan = (
        await session.execute(
            select(RemediationPlanModel).where(
                RemediationPlanModel.id == milestone.plan_id,
                RemediationPlanModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    await session.delete(milestone)


# ─────────────────────────────────────────────────────────────────────────────
# G-041 — Assessment Schedules
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/assessments/schedules",
    response_model=AssessmentScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_assessment_schedule(
    body: AssessmentScheduleCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AssessmentScheduleResponse:
    from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel  # noqa: PLC0415

    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to an organization"
        )

    now = datetime.now(UTC)
    next_due = body.next_due_at or (now + timedelta(days=body.frequency_days))

    schedule = AssessmentScheduleModel(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        supplier_id=body.supplier_id,
        frequency_days=body.frequency_days,
        last_triggered_at=None,
        next_due_at=next_due,
        template_assessment_id=body.template_assessment_id,
        is_active=True,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    try:
        session.add(schedule)
        await session.flush()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An assessment schedule already exists for this supplier",
        )
    logger.info(
        "assessment_schedule_created", schedule_id=schedule.id, supplier_id=body.supplier_id
    )
    return AssessmentScheduleResponse.model_validate(schedule)


@router.get(
    "/assessments/schedules",
    response_model=list[AssessmentScheduleResponse],
    dependencies=[_ANALYST],
)
async def list_assessment_schedules(
    supplier_id: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[AssessmentScheduleResponse]:
    from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel  # noqa: PLC0415

    stmt = select(AssessmentScheduleModel).where(
        AssessmentScheduleModel.organization_id == current_user.organization_id
    )
    if supplier_id:
        stmt = stmt.where(AssessmentScheduleModel.supplier_id == supplier_id)
    if active_only:
        stmt = stmt.where(AssessmentScheduleModel.is_active.is_(True))
    stmt = stmt.order_by(AssessmentScheduleModel.next_due_at)
    result = await session.execute(stmt)
    return [AssessmentScheduleResponse.model_validate(s) for s in result.scalars().all()]


@router.delete(
    "/assessments/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ADMIN],
)
async def delete_assessment_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel  # noqa: PLC0415

    schedule = (
        await session.execute(
            select(AssessmentScheduleModel).where(
                AssessmentScheduleModel.id == schedule_id,
                AssessmentScheduleModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    await session.delete(schedule)


# ─────────────────────────────────────────────────────────────────────────────
# G-046 — Supplier Certificates
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/suppliers/{supplier_id}/certificates",
    response_model=SupplierCertificateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def create_certificate(
    supplier_id: str,
    body: SupplierCertificateCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupplierCertificateResponse:
    from infrastructure.persistence.models.m46_3 import SupplierCertificateModel  # noqa: PLC0415
    from infrastructure.persistence.models.supplier import SupplierModel  # noqa: PLC0415

    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to an organization"
        )

    supplier = (
        await session.execute(
            select(SupplierModel).where(
                SupplierModel.id == supplier_id,
                SupplierModel.organization_id == current_user.organization_id,
                SupplierModel.status != "Deleted",
            )
        )
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    now = datetime.now(UTC)
    cert = SupplierCertificateModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        name=body.name,
        cert_type=body.cert_type,
        issued_at=body.issued_at,
        expires_at=body.expires_at,
        alert_days_before=body.alert_days_before,
        last_alert_sent_at=None,
        issuer=body.issuer,
        certificate_number=body.certificate_number,
        notes=body.notes,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    session.add(cert)
    await session.flush()
    logger.info("certificate_created", cert_id=cert.id, supplier_id=supplier_id)
    return SupplierCertificateResponse.model_validate(cert)


@router.get(
    "/suppliers/{supplier_id}/certificates",
    response_model=list[SupplierCertificateResponse],
    dependencies=[_ANALYST],
)
async def list_certificates(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[SupplierCertificateResponse]:
    from infrastructure.persistence.models.m46_3 import SupplierCertificateModel  # noqa: PLC0415

    result = await session.execute(
        select(SupplierCertificateModel)
        .where(
            SupplierCertificateModel.supplier_id == supplier_id,
            SupplierCertificateModel.organization_id == current_user.organization_id,
        )
        .order_by(SupplierCertificateModel.expires_at)
    )
    return [SupplierCertificateResponse.model_validate(c) for c in result.scalars().all()]


@router.delete(
    "/suppliers/{supplier_id}/certificates/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_ADMIN],
)
async def delete_certificate(
    supplier_id: str,
    cert_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    from infrastructure.persistence.models.m46_3 import SupplierCertificateModel  # noqa: PLC0415

    cert = (
        await session.execute(
            select(SupplierCertificateModel).where(
                SupplierCertificateModel.id == cert_id,
                SupplierCertificateModel.supplier_id == supplier_id,
                SupplierCertificateModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    await session.delete(cert)


# ─────────────────────────────────────────────────────────────────────────────
# G-056 — AI Risk Drafts
# INVARIANT: Agents ONLY create RiskDraft (recommend). Never Risk (approve).
# Human promotion via /accept is the ONLY path to a real Risk record.
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/surveillance/signals/{signal_id}/draft-risk",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[_ANALYST],
)
async def queue_risk_draft(
    signal_id: str,
    body: DraftRiskFromSignalRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Queue an AI risk draft for a surveillance signal. Returns task_id for polling."""
    from infrastructure.celery.tasks.risk_draft import generate_risk_draft_task  # noqa: PLC0415
    from infrastructure.persistence.models.external_intelligence import (
        ExternalRiskSignalModel,  # noqa: PLC0415
    )

    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to an organization"
        )

    signal = (
        await session.execute(
            select(ExternalRiskSignalModel).where(
                ExternalRiskSignalModel.id == signal_id,
                ExternalRiskSignalModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")

    task = generate_risk_draft_task.delay(
        signal_id=signal_id,
        organization_id=current_user.organization_id,
        supplier_id=body.supplier_id or signal.supplier_id or None,
        signal_description=signal.description,
        signal_type=signal.signal_type,
        signal_severity=signal.severity,
        actor_id=current_user.id,
    )
    logger.info("risk_draft_queued", signal_id=signal_id, task_id=task.id)
    return {"task_id": task.id, "status": "processing", "message": "AI risk draft being generated"}


@router.get(
    "/risks/drafts",
    response_model=list[RiskDraftResponse],
    dependencies=[_ANALYST],
)
async def list_risk_drafts(
    review_status: str | None = Query(default="pending"),
    supplier_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[RiskDraftResponse]:
    from infrastructure.persistence.models.m46_3 import RiskDraftModel  # noqa: PLC0415

    stmt = select(RiskDraftModel).where(
        RiskDraftModel.organization_id == current_user.organization_id
    )
    if review_status:
        stmt = stmt.where(RiskDraftModel.review_status == review_status)
    if supplier_id:
        stmt = stmt.where(RiskDraftModel.supplier_id == supplier_id)
    stmt = stmt.order_by(RiskDraftModel.created_at.desc())
    result = await session.execute(stmt)
    return [RiskDraftResponse.model_validate(d) for d in result.scalars().all()]


@router.post(
    "/risks/drafts/{draft_id}/accept",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ANALYST],
)
async def accept_risk_draft(
    draft_id: str,
    body: AcceptRiskDraftRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Promote an AI risk draft to a real Risk record (human approval step).

    Creates a Risk with review_status=Draft. Human must explicitly approve it
    via the standard risk approval workflow.
    """
    from infrastructure.persistence.models.m46_3 import RiskDraftModel  # noqa: PLC0415
    from infrastructure.persistence.models.risk import RiskModel  # noqa: PLC0415

    draft = (
        await session.execute(
            select(RiskDraftModel).where(
                RiskDraftModel.id == draft_id,
                RiskDraftModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.review_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Draft already {draft.review_status}",
        )

    now = datetime.now(UTC)
    risk = RiskModel(
        id=str(uuid.uuid4()),
        status=EntityStatus.ACTIVE.value,
        version=1,
        owner=None,
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
        title=body.override_title or draft.draft_title,
        description=draft.draft_description,
        risk_level=body.override_severity or draft.draft_severity,
        category=draft.draft_category or "",
        confidence="Low",  # AI-generated — low confidence until human validates
        reasoning=f"AI-drafted from surveillance signal {draft.signal_id}. Reviewed by human.",
    )
    session.add(risk)

    draft.review_status = "accepted"
    draft.reviewed_by = current_user.id
    draft.reviewed_at = now
    draft.promoted_risk_id = risk.id
    await session.flush()

    logger.info("risk_draft_accepted", draft_id=draft_id, risk_id=risk.id, reviewer=current_user.id)
    return {"risk_id": risk.id, "draft_id": draft_id, "status": "accepted"}


@router.post(
    "/risks/drafts/{draft_id}/reject",
    status_code=status.HTTP_200_OK,
    dependencies=[_ANALYST],
)
async def reject_risk_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from infrastructure.persistence.models.m46_3 import RiskDraftModel  # noqa: PLC0415

    draft = (
        await session.execute(
            select(RiskDraftModel).where(
                RiskDraftModel.id == draft_id,
                RiskDraftModel.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.review_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Draft already {draft.review_status}",
        )

    now = datetime.now(UTC)
    draft.review_status = "rejected"
    draft.reviewed_by = current_user.id
    draft.reviewed_at = now
    await session.flush()

    logger.info("risk_draft_rejected", draft_id=draft_id, reviewer=current_user.id)
    return {"draft_id": draft_id, "status": "rejected"}
