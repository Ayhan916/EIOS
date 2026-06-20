"""M35 Supplier Portal ORM Models.

15 new tables for the supplier-facing collaboration layer:
  supplier_users                — external user accounts
  supplier_invitations          — one-time invite tokens
  evidence_requests             — internal requests for supplier evidence
  evidence_submissions          — supplier responses
  evidence_submission_files     — files attached to submissions
  questionnaire_templates       — reusable questionnaire blueprints
  questionnaire_questions       — questions within a template
  questionnaire_assignments     — template assigned to a supplier
  questionnaire_answers         — supplier answers per question
  remediation_plans             — supplier-owned finding remediation
  conversations                 — threaded message threads
  conversation_participants     — participants (internal + supplier)
  messages                      — individual messages
  message_attachments           — files attached to messages
  supplier_activity_events      — immutable audit log
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SupplierUserModel(Base):
    __tablename__ = "supplier_users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_supplier_users_email"),
        Index("ix_supplier_users_supplier_id", "supplier_id"),
        Index("ix_supplier_users_email", "email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="supplier_user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notification_preferences: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "email_evidence_requested": True,
            "email_questionnaire_assigned": True,
            "email_remediation_due": True,
            "email_comment_received": True,
        },
    )
    # M35.1 F7: brute-force lockout
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplierInvitationModel(Base):
    __tablename__ = "supplier_invitations"
    __table_args__ = (
        Index("ix_supplier_invitations_token_hash", "token_hash"),
        Index("ix_supplier_invitations_email", "email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    invited_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="supplier_user")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceRequestModel(Base):
    __tablename__ = "evidence_requests"
    __table_args__ = (
        Index("ix_evidence_requests_supplier_id", "supplier_id"),
        Index("ix_evidence_requests_status", "evidence_status"),
        Index("ix_evidence_requests_org", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assessment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assigned_to_supplier_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceSubmissionModel(Base):
    __tablename__ = "evidence_submissions"
    __table_args__ = (
        # M35.1 F8: one active submission per (request, supplier)
        UniqueConstraint("evidence_request_id", "supplier_id", name="uq_evidence_submission_per_supplier"),
        Index("ix_evidence_submissions_request_id", "evidence_request_id"),
        Index("ix_evidence_submissions_supplier_user", "supplier_user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evidence_request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    supplier_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    submission_status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceSubmissionFileModel(Base):
    __tablename__ = "evidence_submission_files"
    __table_args__ = (
        Index("ix_evidence_submission_files_submission_id", "submission_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False, default="application/octet-stream")
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuestionnaireTemplateModel(Base):
    __tablename__ = "questionnaire_templates"
    __table_args__ = (
        Index("ix_questionnaire_templates_name", "name"),
        Index("ix_questionnaire_templates_active", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    template_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuestionnaireQuestionModel(Base):
    __tablename__ = "questionnaire_questions"
    __table_args__ = (
        Index("ix_questionnaire_questions_template_id", "template_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(36), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False, default="text")
    options_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuestionnaireAssignmentModel(Base):
    __tablename__ = "questionnaire_assignments"
    __table_args__ = (
        Index("ix_questionnaire_assignments_supplier_id", "supplier_id"),
        Index("ix_questionnaire_assignments_status", "questionnaire_status"),
        Index("ix_questionnaire_assignments_org", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(36), nullable=False)
    template_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assigned_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    questionnaire_status: Mapped[str] = mapped_column(String(30), nullable=False, default="assigned")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewer_comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuestionnaireAnswerModel(Base):
    __tablename__ = "questionnaire_answers"
    __table_args__ = (
        Index("ix_questionnaire_answers_assignment_id", "assignment_id"),
        UniqueConstraint("assignment_id", "question_id", name="uq_questionnaire_answers_assignment_question"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(String(36), nullable=False)
    question_id: Mapped[str] = mapped_column(String(36), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer_json: Mapped[str] = mapped_column(Text, nullable=False, default="null")
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    answered_by_supplier_user_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RemediationPlanModel(Base):
    __tablename__ = "remediation_plans"
    __table_args__ = (
        Index("ix_remediation_plans_supplier_id", "supplier_id"),
        Index("ix_remediation_plans_finding_id", "finding_id"),
        Index("ix_remediation_plans_status", "remediation_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    finding_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_supplier_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remediation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    completion_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verified_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationModel(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_supplier_id", "supplier_id"),
        Index("ix_conversations_org", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    created_by_type: Mapped[str] = mapped_column(String(20), nullable=False, default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationParticipantModel(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint("conversation_id", "participant_id", "participant_type",
                         name="uq_conv_participant"),
        Index("ix_conversation_participants_conv", "conversation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    participant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    participant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_sender_id", "sender_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False, default="internal")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MessageAttachmentModel(Base):
    __tablename__ = "message_attachments"
    __table_args__ = (
        Index("ix_message_attachments_message_id", "message_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplierActivityEventModel(Base):
    __tablename__ = "supplier_activity_events"
    __table_args__ = (
        Index("ix_supplier_activity_supplier_id", "supplier_id"),
        Index("ix_supplier_activity_event_type", "event_type"),
        Index("ix_supplier_activity_supplier_user", "supplier_user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    supplier_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplierPasswordResetTokenModel(Base):
    """M35.1 F2: DB-backed password reset tokens — single-use, expire-aware."""

    __tablename__ = "supplier_password_reset_tokens"
    __table_args__ = (
        Index("ix_supplier_pwd_reset_token_hash", "token_hash"),
        Index("ix_supplier_pwd_reset_email", "email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
