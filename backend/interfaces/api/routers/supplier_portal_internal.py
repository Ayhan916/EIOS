"""M35 Supplier Portal — Internal admin router.

All endpoints require internal auth (require_admin or require_analyst).
These endpoints are used by EIOS internal users to manage supplier collaboration.

Prefix: /api/v1/supplier-portal/internal

Areas:
  /invitations        — invite supplier users
  /evidence           — create evidence requests, review submissions
  /questionnaires     — assign templates, review submissions
  /remediation        — create plans, verify completed plans
  /messages           — start conversations with suppliers
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.api.deps import get_current_user, get_db, require_admin
from interfaces.api.schemas.supplier_portal import (
    ConversationCreate,
    ConversationResponse,
    EvidenceRequestCreate,
    EvidenceRequestResponse,
    EvidenceSubmissionResponse,
    InviteSupplierUserRequest,
    MessageResponse,
    QuestionnaireAssignmentResponse,
    QuestionnaireAssignRequest,
    QuestionnaireTemplateResponse,
    RemediationPlanCreate,
    RemediationPlanResponse,
    ReviewAssignmentRequest,
    ReviewSubmissionRequest,
    SendMessageRequest,
    VerifyPlanRequest,
)

router = APIRouter(prefix="/supplier-portal/internal", tags=["Supplier Portal (Internal)"])

_ADMIN = Depends(require_admin)


# ── Invitations ───────────────────────────────────────────────────────────────

@router.post(
    "/invitations",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def invite_supplier_user(
    body: InviteSupplierUserRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    from application.supplier_portal.supplier_auth_service import invite_supplier_user  # noqa: PLC0415
    from infrastructure.persistence.models.supplier import SupplierModel  # noqa: PLC0415
    from infrastructure.persistence.models.organization import OrganizationModel  # noqa: PLC0415
    from infrastructure.celery.tasks.email import send_supplier_invitation_email  # noqa: PLC0415
    from shared.config import settings  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    raw_token = await invite_supplier_user(
        supplier_id=body.supplier_id,
        email=body.email,
        role=body.role,
        invited_by_user_id=current_user.id,
        organization_id=current_user.organization_id,
        session=session,
    )
    await session.commit()

    # Queue invitation email (G-009) — fire-and-forget; skips if SMTP not configured
    try:
        supplier_row = (
            await session.execute(select(SupplierModel).where(SupplierModel.id == body.supplier_id))
        ).scalar_one_or_none()
        org_row = (
            await session.execute(
                select(OrganizationModel).where(OrganizationModel.id == current_user.organization_id)
            )
        ).scalar_one_or_none()
        supplier_name = supplier_row.name if supplier_row else body.supplier_id
        org_name = org_row.name if org_row else (current_user.organization_id or "")
        invite_url = f"{settings.app_base_url}/supplier/accept?token={raw_token}"
        send_supplier_invitation_email(
            to_email=body.email,
            supplier_name=supplier_name,
            organization_name=org_name,
            invite_url=invite_url,
        )
    except Exception:
        pass  # email failure never blocks the invitation creation

    return {"invite_token": raw_token, "message": "Invitation created — email queued"}


# ── Evidence Requests ─────────────────────────────────────────────────────────

@router.post(
    "/suppliers/{supplier_id}/evidence/requests",
    response_model=EvidenceRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_evidence_request(
    supplier_id: str,
    body: EvidenceRequestCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EvidenceRequestResponse:
    from application.supplier_portal.evidence_service import create_evidence_request

    req = await create_evidence_request(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        title=body.title,
        description=body.description,
        created_by_user_id=current_user.id,
        due_date=body.due_date,
        assessment_id=body.assessment_id,
        assigned_to_supplier_user_id=body.assigned_to_supplier_user_id,
        session=session,
    )
    await session.commit()
    return EvidenceRequestResponse.model_validate(req)


@router.get(
    "/suppliers/{supplier_id}/evidence/requests",
    response_model=list[EvidenceRequestResponse],
    dependencies=[_ADMIN],
)
async def list_evidence_requests(
    supplier_id: str,
    ev_status: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[EvidenceRequestResponse]:
    from application.supplier_portal.evidence_service import list_evidence_requests

    rows = await list_evidence_requests(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        status=ev_status,
        session=session,
    )
    return [EvidenceRequestResponse.model_validate(r) for r in rows]


@router.post(
    "/evidence/submissions/{submission_id}/review",
    response_model=EvidenceSubmissionResponse,
    dependencies=[_ADMIN],
)
async def review_submission(
    submission_id: str,
    body: ReviewSubmissionRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EvidenceSubmissionResponse:
    from application.supplier_portal.evidence_service import review_submission

    try:
        sub = await review_submission(
            submission_id=submission_id,
            organization_id=current_user.organization_id,
            reviewed_by=current_user.id,
            new_status=body.new_status,
            reviewer_comments=body.reviewer_comments,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return EvidenceSubmissionResponse.model_validate(sub)


# ── Questionnaire Assignments listing ────────────────────────────────────────

@router.get(
    "/questionnaires/assignments",
    response_model=list[QuestionnaireAssignmentResponse],
    dependencies=[_ADMIN],
)
async def list_questionnaire_assignments(
    supplier_id: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[QuestionnaireAssignmentResponse]:
    from infrastructure.persistence.models.supplier_portal import QuestionnaireAssignmentModel
    from sqlalchemy import select

    stmt = select(QuestionnaireAssignmentModel).where(
        QuestionnaireAssignmentModel.organization_id == current_user.organization_id
    )
    if supplier_id:
        stmt = stmt.where(QuestionnaireAssignmentModel.supplier_id == supplier_id)
    stmt = stmt.order_by(QuestionnaireAssignmentModel.assigned_at.desc().nulls_last()).limit(50)
    rows = (await session.execute(stmt)).scalars().all()
    return [QuestionnaireAssignmentResponse.model_validate(r) for r in rows]


# ── Questionnaire Templates ───────────────────────────────────────────────────

@router.get(
    "/questionnaires/templates",
    response_model=list[QuestionnaireTemplateResponse],
    dependencies=[_ADMIN],
)
async def list_templates(
    session: AsyncSession = Depends(get_db),
) -> list[QuestionnaireTemplateResponse]:
    from infrastructure.persistence.models.supplier_portal import QuestionnaireTemplateModel
    from sqlalchemy import select

    stmt = (
        select(QuestionnaireTemplateModel)
        .where(QuestionnaireTemplateModel.is_active.is_(True))
        .order_by(QuestionnaireTemplateModel.name)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return [QuestionnaireTemplateResponse.model_validate(r) for r in rows]


@router.post(
    "/questionnaires/assign",
    response_model=QuestionnaireAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def assign_questionnaire(
    body: QuestionnaireAssignRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> QuestionnaireAssignmentResponse:
    from application.supplier_portal.questionnaire_service import assign_questionnaire

    try:
        assignment = await assign_questionnaire(
            template_id=body.template_id,
            supplier_id=body.supplier_id,
            organization_id=current_user.organization_id,
            assigned_by_user_id=current_user.id,
            due_date=body.due_date,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return QuestionnaireAssignmentResponse.model_validate(assignment)


@router.post(
    "/questionnaires/{assignment_id}/review",
    response_model=QuestionnaireAssignmentResponse,
    dependencies=[_ADMIN],
)
async def review_questionnaire(
    assignment_id: str,
    body: ReviewAssignmentRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> QuestionnaireAssignmentResponse:
    from application.supplier_portal.questionnaire_service import review_assignment

    try:
        assignment = await review_assignment(
            assignment_id=assignment_id,
            organization_id=current_user.organization_id,
            reviewed_by=current_user.id,
            new_status=body.new_status,
            reviewer_comments=body.reviewer_comments,
            score=body.score,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return QuestionnaireAssignmentResponse.model_validate(assignment)


# ── Remediation Plans ─────────────────────────────────────────────────────────

@router.post(
    "/suppliers/{supplier_id}/remediation",
    response_model=RemediationPlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_remediation_plan(
    supplier_id: str,
    body: RemediationPlanCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RemediationPlanResponse:
    from application.supplier_portal.remediation_service import create_remediation_plan

    plan = await create_remediation_plan(
        supplier_id=supplier_id,
        finding_id=body.finding_id,
        title=body.title,
        description=body.description,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        due_date=body.due_date,
        owner_supplier_user_id=body.owner_supplier_user_id,
        session=session,
    )
    await session.commit()
    return RemediationPlanResponse.model_validate(plan)


@router.get(
    "/suppliers/{supplier_id}/remediation",
    response_model=list[RemediationPlanResponse],
    dependencies=[_ADMIN],
)
async def list_remediation_plans(
    supplier_id: str,
    rem_status: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[RemediationPlanResponse]:
    from application.supplier_portal.remediation_service import list_plans_for_org

    rows = await list_plans_for_org(
        organization_id=current_user.organization_id,
        supplier_id=supplier_id,
        status=rem_status,
        session=session,
    )
    return [RemediationPlanResponse.model_validate(r) for r in rows]


@router.post(
    "/remediation/{plan_id}/verify",
    response_model=RemediationPlanResponse,
    dependencies=[_ADMIN],
)
async def verify_remediation_plan(
    plan_id: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RemediationPlanResponse:
    from application.supplier_portal.remediation_service import verify_plan

    try:
        plan = await verify_plan(
            plan_id=plan_id,
            organization_id=current_user.organization_id,
            verified_by=current_user.id,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RemediationPlanResponse.model_validate(plan)


# ── Messaging (Internal side) ─────────────────────────────────────────────────

@router.post(
    "/suppliers/{supplier_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def create_conversation(
    supplier_id: str,
    body: ConversationCreate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ConversationResponse:
    from application.supplier_portal.messaging_service import create_conversation

    conv = await create_conversation(
        title=body.title,
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        created_by_type="internal",
        session=session,
    )
    await session.commit()
    return ConversationResponse.model_validate(conv)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_ADMIN],
)
async def send_internal_message(
    conversation_id: str,
    body: SendMessageRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MessageResponse:
    from application.supplier_portal.messaging_service import (
        get_conversation,
        send_message,
    )
    from infrastructure.persistence.models.supplier_portal import ConversationModel
    from sqlalchemy import select

    # F1: scope by organization_id to block cross-tenant injection
    stmt = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.organization_id == current_user.organization_id,
    )
    conv = (await session.execute(stmt)).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        msg = await send_message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            sender_type="internal",
            content=body.content,
            supplier_id=conv.supplier_id,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return MessageResponse.model_validate(msg)
