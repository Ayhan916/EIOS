"""M46.3 — Scheduling, Remediation Milestones, Certificates & AI Risk Drafts.

New tables:
  remediation_milestones  — milestones attached to remediation_plans (G-040)
  assessment_schedules    — auto re-assessment scheduling per supplier (G-041)
  supplier_certificates   — certificate expiry tracking with alert threshold (G-046)
  risk_drafts             — AI-generated risk descriptions awaiting human review (G-056)

Revision ID: 057
Revises: 056
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── remediation_milestones (G-040) ───────────────────────────────────────
    op.create_table(
        "remediation_milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("remediation_plans.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(36), nullable=True),
        sa.Column("milestone_status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rem_milestones_plan", "remediation_milestones", ["plan_id"])
    op.create_index("ix_rem_milestones_status", "remediation_milestones", ["milestone_status"])

    # ── assessment_schedules (G-041) ─────────────────────────────────────────
    op.create_table(
        "assessment_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("frequency_days", sa.Integer, nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("template_assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "supplier_id", name="uq_assessment_schedule_org_supplier"),
    )
    op.create_index("ix_assessment_schedules_org", "assessment_schedules", ["organization_id"])
    op.create_index("ix_assessment_schedules_supplier", "assessment_schedules", ["supplier_id"])
    op.create_index("ix_assessment_schedules_next_due", "assessment_schedules", ["next_due_at"])

    # ── supplier_certificates (G-046) ────────────────────────────────────────
    op.create_table(
        "supplier_certificates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("cert_type", sa.String(100), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("alert_days_before", sa.Integer, nullable=False, server_default="30"),
        sa.Column("last_alert_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issuer", sa.String(500), nullable=True),
        sa.Column("certificate_number", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_certs_supplier", "supplier_certificates", ["supplier_id"])
    op.create_index("ix_supplier_certs_org", "supplier_certificates", ["organization_id"])
    op.create_index("ix_supplier_certs_expires", "supplier_certificates", ["expires_at"])

    # ── risk_drafts (G-056) ──────────────────────────────────────────────────
    # AI-generated risk descriptions — human MUST review before promotion to Risk.
    # Agents may ONLY draft (recommend); they never create or approve risks.
    op.create_table(
        "risk_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("signal_id", sa.String(36), nullable=True),
        sa.Column("draft_title", sa.String(500), nullable=False),
        sa.Column("draft_description", sa.Text, nullable=False),
        sa.Column("draft_severity", sa.String(20), nullable=False),
        sa.Column("draft_category", sa.String(100), nullable=True),
        sa.Column("draft_likelihood", sa.String(20), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=False),
        sa.Column("llm_prompt_hash", sa.String(64), nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_risk_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_drafts_org", "risk_drafts", ["organization_id"])
    op.create_index("ix_risk_drafts_status", "risk_drafts", ["review_status"])
    op.create_index("ix_risk_drafts_supplier", "risk_drafts", ["supplier_id"])


def downgrade() -> None:
    op.drop_table("risk_drafts")
    op.drop_table("supplier_certificates")
    op.drop_table("assessment_schedules")
    op.drop_table("remediation_milestones")
