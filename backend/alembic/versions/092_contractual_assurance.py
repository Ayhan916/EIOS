"""CSDDD-006 — Contractual Assurance Module (Art. 10)

Revision ID: 092
Revises: 091
Create Date: 2026-07-06

Creates:
  contract_clauses       — clause template library
  contract_assurances    — per-supplier clause acceptance records
  clause_audit_logs      — immutable audit trail for status changes
"""

from alembic import op
import sqlalchemy as sa

revision = "092"
down_revision = "091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_clauses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("clause_text", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("cascade_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_contract_clauses_org", "contract_clauses", ["organization_id"])
    op.create_index("ix_contract_clauses_org_category", "contract_clauses", ["organization_id", "category"])

    op.create_table(
        "contract_assurances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("clause_id", sa.String(36), sa.ForeignKey("contract_clauses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(255), nullable=True),
        sa.Column("document_ref", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("cascade_confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cascade_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_contract_assurances_org", "contract_assurances", ["organization_id"])
    op.create_index("ix_contract_assurances_supplier", "contract_assurances", ["supplier_id"])
    op.create_index("ix_contract_assurances_supplier_clause", "contract_assurances", ["supplier_id", "clause_id"])
    op.create_index("ix_contract_assurances_org_status", "contract_assurances", ["organization_id", "status"])

    op.create_table(
        "clause_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("assurance_id", sa.String(36), sa.ForeignKey("contract_assurances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("changed_by", sa.String(255), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_clause_audit_logs_org", "clause_audit_logs", ["organization_id"])
    op.create_index("ix_clause_audit_logs_assurance", "clause_audit_logs", ["assurance_id"])


def downgrade() -> None:
    op.drop_table("clause_audit_logs")
    op.drop_table("contract_assurances")
    op.drop_table("contract_clauses")
