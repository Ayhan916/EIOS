"""add_regulatory_intelligence

M31 — Regulatory Intelligence & Compliance Mapping.

Tables:
  regulations              — persisted regulatory frameworks (CSRD, ISSB, TCFD, …)
  regulation_requirements  — specific obligations within each regulation
  requirement_mappings     — links Finding/Risk/Recommendation to a requirement
  compliance_gaps          — persisted gap records per org (computed by gap engine)

Revision ID: 025
Revises: 024
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None

_BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, default="Active"),
    sa.Column("version", sa.Integer, nullable=False, default=1),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    op.create_table(
        "regulations",
        *_BASE_COLS,
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False, server_default="Global"),
        sa.Column("reg_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("reg_status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
    )
    op.create_index("ix_regulations_code", "regulations", ["code"], unique=True)

    op.create_table(
        "regulation_requirements",
        *_BASE_COLS,
        sa.Column("regulation_id", sa.String(36), sa.ForeignKey("regulations.id"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("category", sa.String(50), nullable=False, server_default=""),
        sa.Column("pillar", sa.String(5), nullable=False, server_default=""),
        sa.Column("severity", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("obligation_type", sa.String(20), nullable=False, server_default="mandatory"),
        sa.Column("keywords", postgresql.JSON, nullable=False),
    )
    op.create_index(
        "ix_regulation_requirements_code", "regulation_requirements", ["code"], unique=True
    )
    op.create_index(
        "ix_regulation_requirements_regulation", "regulation_requirements", ["regulation_id"]
    )

    op.create_table(
        "requirement_mappings",
        *_BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "regulation_requirement_id",
            sa.String(36),
            sa.ForeignKey("regulation_requirements.id"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("mapping_method", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("mapping_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("mapped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("assessment_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_req_mappings_org", "requirement_mappings", ["organization_id"])
    op.create_index("ix_req_mappings_entity", "requirement_mappings", ["entity_type", "entity_id"])
    op.create_index(
        "ix_req_mappings_requirement", "requirement_mappings", ["regulation_requirement_id"]
    )

    op.create_table(
        "compliance_gaps",
        *_BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "regulation_requirement_id",
            sa.String(36),
            sa.ForeignKey("regulation_requirements.id"),
            nullable=False,
        ),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("gap_type", sa.String(50), nullable=False, server_default="missing_evidence"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("evidence_refs", postgresql.JSON, nullable=False),
        sa.Column("source_entity_type", sa.String(30), nullable=True),
        sa.Column("source_entity_id", sa.String(36), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculation_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(36), nullable=True),
    )
    op.create_index("ix_compliance_gaps_org", "compliance_gaps", ["organization_id"])
    op.create_index(
        "ix_compliance_gaps_requirement", "compliance_gaps", ["regulation_requirement_id"]
    )
    op.create_index("ix_compliance_gaps_supplier", "compliance_gaps", ["supplier_id"])


def downgrade() -> None:
    op.drop_table("compliance_gaps")
    op.drop_table("requirement_mappings")
    op.drop_table("regulation_requirements")
    op.drop_table("regulations")
