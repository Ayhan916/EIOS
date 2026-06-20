"""M35 Supplier Portal — 15 new tables.

Creates all supplier portal tables:
  supplier_users, supplier_invitations,
  evidence_requests, evidence_submissions, evidence_submission_files,
  questionnaire_templates, questionnaire_questions,
  questionnaire_assignments, questionnaire_answers,
  remediation_plans,
  conversations, conversation_participants, messages, message_attachments,
  supplier_activity_events

Revision ID: 036
Revises: 035
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── supplier_users ─────────────────────────────────────────────────────────
    op.create_table(
        "supplier_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="supplier_user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("notification_preferences", sa.JSON, nullable=False,
                  server_default='{"email_evidence_requested": true, "email_questionnaire_assigned": true}'),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_supplier_users_email"),
    )
    op.create_index("ix_supplier_users_supplier_id", "supplier_users", ["supplier_id"])
    op.create_index("ix_supplier_users_email", "supplier_users", ["email"])

    # ── supplier_invitations ───────────────────────────────────────────────────
    op.create_table(
        "supplier_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("invited_by_user_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="supplier_user"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_invitations_token_hash", "supplier_invitations", ["token_hash"])
    op.create_index("ix_supplier_invitations_email", "supplier_invitations", ["email"])

    # ── evidence_requests ──────────────────────────────────────────────────────
    op.create_table(
        "evidence_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("assessment_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("assigned_to_supplier_user_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_requests_supplier_id", "evidence_requests", ["supplier_id"])
    op.create_index("ix_evidence_requests_status", "evidence_requests", ["evidence_status"])
    op.create_index("ix_evidence_requests_org", "evidence_requests", ["organization_id"])

    # ── evidence_submissions ───────────────────────────────────────────────────
    op.create_table(
        "evidence_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_request_id", sa.String(36), nullable=False),
        sa.Column("supplier_user_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("comments", sa.Text, nullable=False, server_default=""),
        sa.Column("submission_status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_comments", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_submissions_request_id", "evidence_submissions", ["evidence_request_id"])
    op.create_index("ix_evidence_submissions_supplier_user", "evidence_submissions", ["supplier_user_id"])

    # ── evidence_submission_files ──────────────────────────────────────────────
    op.create_table(
        "evidence_submission_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("submission_id", sa.String(36), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(200), nullable=False, server_default="application/octet-stream"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_submission_files_submission_id", "evidence_submission_files", ["submission_id"])

    # ── questionnaire_templates ────────────────────────────────────────────────
    op.create_table(
        "questionnaire_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("template_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by_user_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("question_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questionnaire_templates_name", "questionnaire_templates", ["name"])
    op.create_index("ix_questionnaire_templates_active", "questionnaire_templates", ["is_active"])

    # ── questionnaire_questions ────────────────────────────────────────────────
    op.create_table(
        "questionnaire_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_id", sa.String(36), nullable=False),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(30), nullable=False, server_default="text"),
        sa.Column("options_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questionnaire_questions_template_id", "questionnaire_questions", ["template_id"])

    # ── questionnaire_assignments ──────────────────────────────────────────────
    op.create_table(
        "questionnaire_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_id", sa.String(36), nullable=False),
        sa.Column("template_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("assigned_by_user_id", sa.String(36), nullable=False),
        sa.Column("questionnaire_status", sa.String(30), nullable=False, server_default="assigned"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewer_comments", sa.Text, nullable=False, server_default=""),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questionnaire_assignments_supplier_id", "questionnaire_assignments", ["supplier_id"])
    op.create_index("ix_questionnaire_assignments_status", "questionnaire_assignments", ["questionnaire_status"])
    op.create_index("ix_questionnaire_assignments_org", "questionnaire_assignments", ["organization_id"])

    # ── questionnaire_answers ──────────────────────────────────────────────────
    op.create_table(
        "questionnaire_answers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assignment_id", sa.String(36), nullable=False),
        sa.Column("question_id", sa.String(36), nullable=False),
        sa.Column("answer_text", sa.Text, nullable=False, server_default=""),
        sa.Column("answer_json", sa.Text, nullable=False, server_default="null"),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("answered_by_supplier_user_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("assignment_id", "question_id", name="uq_questionnaire_answers_assignment_question"),
    )
    op.create_index("ix_questionnaire_answers_assignment_id", "questionnaire_answers", ["assignment_id"])

    # ── remediation_plans ─────────────────────────────────────────────────────
    op.create_table(
        "remediation_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("owner_supplier_user_id", sa.String(36), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remediation_status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("completion_percentage", sa.Integer, nullable=False, server_default="0"),
        sa.Column("verified_by", sa.String(36), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_remediation_plans_supplier_id", "remediation_plans", ["supplier_id"])
    op.create_index("ix_remediation_plans_finding_id", "remediation_plans", ["finding_id"])
    op.create_index("ix_remediation_plans_status", "remediation_plans", ["remediation_status"])

    # ── conversations ──────────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("created_by_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("created_by_type", sa.String(20), nullable=False, server_default="internal"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_supplier_id", "conversations", ["supplier_id"])
    op.create_index("ix_conversations_org", "conversations", ["organization_id"])

    # ── conversation_participants ──────────────────────────────────────────────
    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("participant_id", sa.String(36), nullable=False),
        sa.Column("participant_type", sa.String(20), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("conversation_id", "participant_id", "participant_type",
                            name="uq_conv_participant"),
    )
    op.create_index("ix_conversation_participants_conv", "conversation_participants", ["conversation_id"])

    # ── messages ───────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("sender_id", sa.String(36), nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False, server_default="internal"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])

    # ── message_attachments ────────────────────────────────────────────────────
    op.create_table(
        "message_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_message_attachments_message_id", "message_attachments", ["message_id"])

    # ── supplier_activity_events ───────────────────────────────────────────────
    op.create_table(
        "supplier_activity_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("supplier_user_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_activity_supplier_id", "supplier_activity_events", ["supplier_id"])
    op.create_index("ix_supplier_activity_event_type", "supplier_activity_events", ["event_type"])
    op.create_index("ix_supplier_activity_supplier_user", "supplier_activity_events", ["supplier_user_id"])


def downgrade() -> None:
    op.drop_table("supplier_activity_events")
    op.drop_table("message_attachments")
    op.drop_table("messages")
    op.drop_table("conversation_participants")
    op.drop_table("conversations")
    op.drop_table("remediation_plans")
    op.drop_table("questionnaire_answers")
    op.drop_table("questionnaire_assignments")
    op.drop_table("questionnaire_questions")
    op.drop_table("questionnaire_templates")
    op.drop_table("evidence_submission_files")
    op.drop_table("evidence_submissions")
    op.drop_table("evidence_requests")
    op.drop_table("supplier_invitations")
    op.drop_table("supplier_users")
