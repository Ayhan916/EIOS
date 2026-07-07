"""M35 Supplier Portal — Pydantic schemas.

Covers:
  Auth:             InviteRequest, ActivateRequest, LoginRequest, LoginResponse,
                    PasswordResetRequest, PasswordResetConfirm
  SupplierUser:     SupplierUserResponse, SupplierUserUpdate
  Dashboard:        DashboardResponse, ActivityEventResponse
  Evidence:         EvidenceRequestResponse, EvidenceRequestCreate,
                    EvidenceSubmissionResponse, EvidenceSubmissionCreate,
                    AttachFileRequest, ReviewSubmissionRequest
  Questionnaire:    QuestionnaireTemplateResponse, QuestionnaireQuestionResponse,
                    QuestionnaireAssignmentResponse, QuestionnaireAssignRequest,
                    SaveAnswerRequest, SubmitQuestionnaireRequest, ReviewAssignmentRequest
  Remediation:      RemediationPlanResponse, RemediationPlanCreate,
                    UpdateProgressRequest, VerifyPlanRequest
  Messaging:        ConversationResponse, ConversationCreate,
                    MessageResponse, SendMessageRequest
  Internal:         InviteSupplierUserRequest

SECURITY: password_hash is NEVER included in any response schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

# ── Auth ──────────────────────────────────────────────────────────────────────


class InviteSupplierUserRequest(BaseModel):
    supplier_id: str
    email: EmailStr
    role: str = "supplier_user"


class ActivateRequest(BaseModel):
    invite_token: str
    display_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ── Supplier User ─────────────────────────────────────────────────────────────


class SupplierUserResponse(BaseModel):
    id: str
    supplier_id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None
    invited_at: datetime | None
    accepted_at: datetime | None
    notification_preferences: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierUserUpdate(BaseModel):
    display_name: str | None = None
    notification_preferences: dict[str, Any] | None = None


# ── Dashboard ─────────────────────────────────────────────────────────────────


class ActivityEventResponse(BaseModel):
    id: str
    supplier_id: str
    supplier_user_id: str | None
    event_type: str
    entity_type: str
    entity_id: str
    metadata_json: str = "{}"
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    supplier_id: str
    open_findings: int
    open_recommendations: int
    overdue_actions: int
    pending_questionnaires: int
    requested_evidence: int
    open_remediation_plans: int
    recent_activity: list[ActivityEventResponse] = []


# ── Evidence ──────────────────────────────────────────────────────────────────


class EvidenceRequestCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    due_date: datetime | None = None
    assessment_id: str | None = None
    assigned_to_supplier_user_id: str | None = None


class EvidenceRequestResponse(BaseModel):
    id: str
    supplier_id: str
    organization_id: str
    assessment_id: str | None
    title: str
    description: str
    due_date: datetime | None
    evidence_status: str
    created_by_user_id: str
    assigned_to_supplier_user_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceSubmissionCreate(BaseModel):
    comments: str = ""


class EvidenceSubmissionResponse(BaseModel):
    id: str
    evidence_request_id: str
    supplier_user_id: str
    supplier_id: str
    comments: str
    submission_status: str
    submitted_at: datetime | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    reviewer_comments: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceSubmissionFileResponse(BaseModel):
    id: str
    submission_id: str
    file_name: str
    file_path: str
    file_size: int
    content_type: str
    uploaded_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewSubmissionRequest(BaseModel):
    new_status: str = Field(..., pattern="^(accepted|rejected|revision_requested)$")
    reviewer_comments: str = ""


# ── Questionnaire ─────────────────────────────────────────────────────────────


class QuestionnaireQuestionResponse(BaseModel):
    id: str
    template_id: str
    order: int
    text: str
    question_type: str
    options_json: str
    required: bool
    weight: float

    model_config = {"from_attributes": True}


class QuestionnaireTemplateResponse(BaseModel):
    id: str
    name: str
    template_version: str
    description: str
    is_active: bool
    question_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionnaireAssignRequest(BaseModel):
    template_id: str
    supplier_id: str
    due_date: datetime | None = None


class QuestionnaireAssignmentResponse(BaseModel):
    id: str
    template_id: str
    template_version: str
    supplier_id: str
    organization_id: str
    assigned_by_user_id: str
    questionnaire_status: str
    due_date: datetime | None
    assigned_at: datetime | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by: str | None
    reviewer_comments: str
    score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SaveAnswerRequest(BaseModel):
    question_id: str
    answer_text: str = ""
    answer_json: str = "null"
    file_path: str | None = None


class ReviewAssignmentRequest(BaseModel):
    new_status: str = Field(..., pattern="^(approved|rejected)$")
    reviewer_comments: str = ""
    score: float | None = None


# ── Remediation ───────────────────────────────────────────────────────────────


class RemediationPlanCreate(BaseModel):
    finding_id: str
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    due_date: datetime | None = None
    owner_supplier_user_id: str | None = None


class RemediationPlanResponse(BaseModel):
    id: str
    supplier_id: str
    finding_id: str
    organization_id: str
    title: str
    description: str
    owner_supplier_user_id: str | None
    due_date: datetime | None
    remediation_status: str
    completion_percentage: int
    verified_by: str | None
    verified_at: datetime | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateProgressRequest(BaseModel):
    completion_percentage: int = Field(..., ge=0, le=100)
    new_status: str | None = None


class VerifyPlanRequest(BaseModel):
    plan_id: str


# ── Messaging ─────────────────────────────────────────────────────────────────


class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    supplier_id: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    supplier_id: str
    organization_id: str
    created_by_id: str
    created_by_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    sender_type: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
