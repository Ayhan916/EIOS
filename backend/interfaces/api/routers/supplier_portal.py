"""M35 Supplier Portal — Supplier-facing API router.

All endpoints here require a valid supplier JWT (aud=eios-supplier).
Internal tokens are rejected at the dependency layer.

Prefix: /api/v1/supplier-portal

Areas:
  /auth           — login, activate, password reset
  /dashboard      — widget aggregation
  /evidence       — view requests, create/submit submissions
  /questionnaires — view assignments, save answers, submit
  /remediation    — view plans, update progress
  /messages       — conversations and messages
  /activity       — activity timeline
  /profile        — view/update own profile
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from domain.supplier_portal import SupplierUser
from interfaces.api.deps import get_db
from interfaces.api.schemas.supplier_portal import (
    ActivateRequest,
    ActivityEventResponse,
    ConversationResponse,
    DashboardResponse,
    EvidenceRequestResponse,
    EvidenceSubmissionCreate,
    EvidenceSubmissionResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    QuestionnaireAssignmentResponse,
    RemediationPlanResponse,
    SaveAnswerRequest,
    SendMessageRequest,
    SupplierUserResponse,
    SupplierUserUpdate,
    UpdateProgressRequest,
)
from interfaces.api.supplier_deps import (
    get_current_supplier_user,
)

router = APIRouter(prefix="/supplier-portal", tags=["Supplier Portal"])

_SUPPLIER = Depends(get_current_supplier_user)


# ── Auth (no auth required) ───────────────────────────────────────────────────


@router.post("/auth/activate", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def activate_account(
    body: ActivateRequest,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    from application.supplier_portal.supplier_auth_service import activate_supplier_user

    try:
        access_token, refresh_token = await activate_supplier_user(
            invite_token=body.invite_token,
            display_name=body.display_name,
            password=body.password,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    from application.supplier_portal.supplier_auth_service import login_supplier_user

    try:
        access_token, refresh_token = await login_supplier_user(
            email=body.email,
            password=body.password,
            session=session,
        )
        await session.commit()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/password-reset/request", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(
    body: PasswordResetRequest,
    session: AsyncSession = Depends(get_db),
) -> None:
    from application.supplier_portal.supplier_auth_service import generate_password_reset_token

    # Fire-and-forget — never reveal whether user exists
    await generate_password_reset_token(body.email, session)
    await session.commit()


@router.post("/auth/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db),
) -> None:
    from application.supplier_portal.supplier_auth_service import reset_password

    try:
        await reset_password(body.token, body.new_password, session)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Profile ───────────────────────────────────────────────────────────────────


@router.get("/profile", response_model=SupplierUserResponse)
async def get_profile(
    supplier_user: SupplierUser = _SUPPLIER,
) -> SupplierUserResponse:
    return SupplierUserResponse(
        id=supplier_user.id,
        supplier_id=supplier_user.supplier_id,
        email=supplier_user.email,
        display_name=supplier_user.display_name,
        role=supplier_user.role,
        is_active=supplier_user.is_active,
        last_login_at=supplier_user.last_login_at,
        invited_at=supplier_user.invited_at,
        accepted_at=supplier_user.accepted_at,
        notification_preferences=supplier_user.notification_preferences,
        created_at=supplier_user.accepted_at or supplier_user.invited_at,
        updated_at=supplier_user.last_login_at
        or supplier_user.accepted_at
        or supplier_user.invited_at,
    )


@router.patch("/profile", response_model=SupplierUserResponse)
async def update_profile(
    body: SupplierUserUpdate,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> SupplierUserResponse:
    from datetime import UTC, datetime

    from sqlalchemy import select

    from infrastructure.persistence.models.supplier_portal import SupplierUserModel

    stmt = select(SupplierUserModel).where(SupplierUserModel.id == supplier_user.id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(UTC)
    if body.display_name is not None:
        row.display_name = body.display_name
    if body.notification_preferences is not None:
        row.notification_preferences = body.notification_preferences
    row.updated_at = now
    await session.commit()

    return SupplierUserResponse(
        id=row.id,
        supplier_id=row.supplier_id,
        email=row.email,
        display_name=row.display_name,
        role=row.role,
        is_active=row.is_active,
        last_login_at=row.last_login_at,
        invited_at=row.invited_at,
        accepted_at=row.accepted_at,
        notification_preferences=row.notification_preferences or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    from application.supplier_portal.dashboard_service import get_supplier_dashboard

    result = await get_supplier_dashboard(supplier_user.supplier_id, session)
    return DashboardResponse(
        supplier_id=result.supplier_id,
        open_findings=result.open_findings,
        open_recommendations=result.open_recommendations,
        overdue_actions=result.overdue_actions,
        pending_questionnaires=result.pending_questionnaires,
        requested_evidence=result.requested_evidence,
        open_remediation_plans=result.open_remediation_plans,
        recent_activity=[ActivityEventResponse.model_validate(ev) for ev in result.recent_activity],
    )


# ── Evidence ──────────────────────────────────────────────────────────────────


@router.get("/evidence/requests", response_model=list[EvidenceRequestResponse])
async def list_my_evidence_requests(
    status: str | None = None,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> list[EvidenceRequestResponse]:
    from application.supplier_portal.evidence_service import list_evidence_requests

    rows = await list_evidence_requests(
        supplier_id=supplier_user.supplier_id,
        organization_id="",
        status=status,
        limit=50,
        session=session,
    )
    return [EvidenceRequestResponse.model_validate(r) for r in rows]


@router.get("/evidence/requests/{request_id}", response_model=EvidenceRequestResponse)
async def get_my_evidence_request(
    request_id: str,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> EvidenceRequestResponse:
    from application.supplier_portal.evidence_service import get_supplier_evidence_request

    row = await get_supplier_evidence_request(request_id, supplier_user.supplier_id, session)
    if row is None:
        raise HTTPException(status_code=404, detail="Evidence request not found")
    return EvidenceRequestResponse.model_validate(row)


@router.post(
    "/evidence/requests/{request_id}/submissions",
    response_model=EvidenceSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    request_id: str,
    body: EvidenceSubmissionCreate,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> EvidenceSubmissionResponse:
    from application.supplier_portal.evidence_service import (
        create_submission,
        get_supplier_evidence_request,
    )

    req = await get_supplier_evidence_request(request_id, supplier_user.supplier_id, session)
    if req is None:
        raise HTTPException(status_code=404, detail="Evidence request not found")

    sub = await create_submission(
        evidence_request_id=request_id,
        supplier_user_id=supplier_user.id,
        supplier_id=supplier_user.supplier_id,
        comments=body.comments,
        session=session,
    )
    await session.commit()
    return EvidenceSubmissionResponse.model_validate(sub)


@router.post(
    "/evidence/submissions/{submission_id}/submit",
    response_model=EvidenceSubmissionResponse,
)
async def submit_evidence(
    submission_id: str,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> EvidenceSubmissionResponse:
    from application.supplier_portal.evidence_service import submit_evidence

    try:
        sub = await submit_evidence(submission_id, supplier_user.supplier_id, session)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return EvidenceSubmissionResponse.model_validate(sub)


# ── Questionnaires ────────────────────────────────────────────────────────────


@router.get("/questionnaires", response_model=list[QuestionnaireAssignmentResponse])
async def list_my_questionnaires(
    status: str | None = None,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> list[QuestionnaireAssignmentResponse]:
    from application.supplier_portal.questionnaire_service import get_my_assignments

    rows = await get_my_assignments(supplier_user.supplier_id, status, session=session)
    return [QuestionnaireAssignmentResponse.model_validate(r) for r in rows]


@router.post("/questionnaires/{assignment_id}/answers", response_model=dict)
async def save_answer(
    assignment_id: str,
    body: SaveAnswerRequest,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> dict:
    from application.supplier_portal.questionnaire_service import save_answer

    try:
        answer = await save_answer(
            assignment_id=assignment_id,
            question_id=body.question_id,
            supplier_user_id=supplier_user.id,
            supplier_id=supplier_user.supplier_id,
            answer_text=body.answer_text,
            answer_json=body.answer_json,
            file_path=body.file_path,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"id": answer.id, "question_id": answer.question_id, "saved": True}


@router.post(
    "/questionnaires/{assignment_id}/submit",
    response_model=QuestionnaireAssignmentResponse,
)
async def submit_questionnaire(
    assignment_id: str,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> QuestionnaireAssignmentResponse:
    from application.supplier_portal.questionnaire_service import submit_questionnaire

    try:
        assignment = await submit_questionnaire(assignment_id, supplier_user.supplier_id, session)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return QuestionnaireAssignmentResponse.model_validate(assignment)


# ── Remediation ───────────────────────────────────────────────────────────────


@router.get("/remediation", response_model=list[RemediationPlanResponse])
async def list_my_remediation_plans(
    status: str | None = None,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> list[RemediationPlanResponse]:
    from application.supplier_portal.remediation_service import get_my_plans

    rows = await get_my_plans(supplier_user.supplier_id, status, session=session)
    return [RemediationPlanResponse.model_validate(r) for r in rows]


@router.patch(
    "/remediation/{plan_id}/progress",
    response_model=RemediationPlanResponse,
)
async def update_remediation_progress(
    plan_id: str,
    body: UpdateProgressRequest,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> RemediationPlanResponse:
    from application.supplier_portal.remediation_service import update_progress

    try:
        plan = await update_progress(
            plan_id=plan_id,
            supplier_id=supplier_user.supplier_id,
            completion_percentage=body.completion_percentage,
            new_status=body.new_status,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return RemediationPlanResponse.model_validate(plan)


# ── Messaging ─────────────────────────────────────────────────────────────────


@router.get("/messages/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    from application.supplier_portal.messaging_service import list_conversations

    rows = await list_conversations(supplier_user.supplier_id, session=session)
    return [ConversationResponse.model_validate(r) for r in rows]


@router.get(
    "/messages/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    conversation_id: str,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    from application.supplier_portal.messaging_service import get_conversation_messages

    try:
        msgs = await get_conversation_messages(
            conversation_id, supplier_user.supplier_id, session=session
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [MessageResponse.model_validate(m) for m in msgs]


@router.post(
    "/messages/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    from application.supplier_portal.messaging_service import send_message

    try:
        msg = await send_message(
            conversation_id=conversation_id,
            sender_id=supplier_user.id,
            sender_type="supplier",
            content=body.content,
            supplier_id=supplier_user.supplier_id,
            session=session,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return MessageResponse.model_validate(msg)


# ── Activity ──────────────────────────────────────────────────────────────────


@router.get("/activity", response_model=list[ActivityEventResponse])
async def get_activity(
    event_type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = 0,
    supplier_user: SupplierUser = _SUPPLIER,
    session: AsyncSession = Depends(get_db),
) -> list[ActivityEventResponse]:
    from application.supplier_portal.activity_service import list_activity

    rows = await list_activity(
        supplier_user.supplier_id, event_type, limit=limit, offset=offset, session=session
    )
    return [ActivityEventResponse.model_validate(r) for r in rows]
