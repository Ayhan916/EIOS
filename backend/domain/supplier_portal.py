"""
EIOS Domain Model — Supplier Portal (M35)

Canonical domain objects for all supplier-facing collaboration entities.
These are pure domain types with no persistence or HTTP concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity
from .enums import (
    EvidenceRequestStatus,
    EvidenceSubmissionStatus,
    QuestionnaireStatus,
    QuestionType,
    RemediationStatus,
    SupplierActivityEventType,
    SupplierUserRole,
)


@dataclass(slots=True, kw_only=True)
class SupplierUser(BaseEntity):
    """External user account belonging to a supplier organisation."""

    supplier_id: str
    email: str
    display_name: str
    role: str = SupplierUserRole.SUPPLIER_USER.value
    is_active: bool = True
    last_login_at: datetime | None = None
    invited_at: datetime | None = None
    accepted_at: datetime | None = None
    password_hash: str | None = None
    notification_preferences: dict = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class SupplierInvitation(BaseEntity):
    """One-time-use invitation token sent to a supplier contact."""

    supplier_id: str
    email: str
    invited_by_user_id: str
    token_hash: str
    expires_at: datetime
    accepted_at: datetime | None = None
    role: str = SupplierUserRole.SUPPLIER_USER.value


@dataclass(slots=True, kw_only=True)
class EvidenceRequest(BaseEntity):
    """Internal request for a supplier to submit evidence."""

    supplier_id: str
    organization_id: str
    title: str
    description: str
    due_date: datetime | None = None
    evidence_status: str = EvidenceRequestStatus.OPEN.value
    created_by_user_id: str = ""
    assigned_to_supplier_user_id: str | None = None
    assessment_id: str | None = None


@dataclass(slots=True, kw_only=True)
class EvidenceSubmission(BaseEntity):
    """Supplier's response to an EvidenceRequest."""

    evidence_request_id: str
    supplier_user_id: str
    supplier_id: str
    comments: str = ""
    submission_status: str = EvidenceSubmissionStatus.DRAFT.value
    submitted_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    reviewer_comments: str = ""


@dataclass(slots=True, kw_only=True)
class EvidenceSubmissionFile(BaseEntity):
    """File attached to an EvidenceSubmission."""

    submission_id: str
    file_name: str
    file_path: str
    file_size: int = 0
    content_type: str = "application/octet-stream"
    uploaded_at: datetime | None = None


@dataclass(slots=True, kw_only=True)
class QuestionnaireTemplate(BaseEntity):
    """Versioned questionnaire blueprint reusable across suppliers."""

    name: str
    template_version: str = "1.0"
    description: str = ""
    is_active: bool = True
    created_by_user_id: str = ""
    question_count: int = 0


@dataclass(slots=True, kw_only=True)
class QuestionnaireQuestion(BaseEntity):
    """A single question within a QuestionnaireTemplate."""

    template_id: str
    order: int = 0
    text: str = ""
    question_type: str = QuestionType.TEXT.value
    options_json: str = "[]"
    required: bool = True
    weight: float = 1.0


@dataclass(slots=True, kw_only=True)
class QuestionnaireAssignment(BaseEntity):
    """An instance of a QuestionnaireTemplate assigned to a supplier."""

    template_id: str
    template_version: str
    supplier_id: str
    organization_id: str
    assigned_by_user_id: str
    questionnaire_status: str = QuestionnaireStatus.ASSIGNED.value
    due_date: datetime | None = None
    assigned_at: datetime | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    reviewer_comments: str = ""
    score: float | None = None


@dataclass(slots=True, kw_only=True)
class QuestionnaireAnswer(BaseEntity):
    """Supplier's answer to one question in an assignment."""

    assignment_id: str
    question_id: str
    answer_text: str = ""
    answer_json: str = "null"
    file_path: str | None = None
    answered_by_supplier_user_id: str = ""
    answered_at: datetime | None = None


@dataclass(slots=True, kw_only=True)
class RemediationPlan(BaseEntity):
    """Supplier-owned plan to remediate a specific finding."""

    supplier_id: str
    finding_id: str
    title: str
    description: str = ""
    owner_supplier_user_id: str | None = None
    due_date: datetime | None = None
    remediation_status: str = RemediationStatus.OPEN.value
    completion_percentage: int = 0
    verified_by: str | None = None
    verified_at: datetime | None = None
    organization_id: str = ""


@dataclass(slots=True, kw_only=True)
class Conversation(BaseEntity):
    """Threaded message thread between internal and supplier users."""

    title: str
    supplier_id: str
    organization_id: str
    created_by_id: str = ""
    created_by_type: str = "internal"


@dataclass(slots=True, kw_only=True)
class Message(BaseEntity):
    """Single message within a Conversation."""

    conversation_id: str
    sender_id: str
    sender_type: str = "internal"
    content: str = ""


@dataclass(slots=True, kw_only=True)
class MessageAttachment(BaseEntity):
    """File attached to a Message."""

    message_id: str
    file_name: str
    file_path: str
    file_size: int = 0


@dataclass(slots=True, kw_only=True)
class SupplierActivityEvent:
    """Immutable audit event for all supplier portal actions."""

    id: str
    supplier_id: str
    supplier_user_id: str | None
    event_type: str
    entity_type: str = ""
    entity_id: str = ""
    metadata_json: str = "{}"
    created_at: datetime | None = None
