"""M47 — Regulatory Calendar: regulatory_deadlines table + seeds.

Revision ID: 059
Revises: 058
Create Date: 2026-06-23
"""

from __future__ import annotations

import uuid
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None

# (framework_code, deadline_name, deadline_date, description, jurisdiction, entity_size, is_mandatory, reporting_year)
_DEADLINES = [
    # ── CSRD ────────────────────────────────────────────────────────────────────
    (
        "CSRD", "CSRD First-Wave Filing Deadline",
        "2025-03-31", "Large public-interest entities (>500 employees) must publish ESRS-compliant sustainability statements for FY2024.",
        "EU", "Large", True, "2024",
    ),
    (
        "CSRD", "CSRD Second-Wave Filing Deadline",
        "2026-03-31", "Large companies not already covered by wave 1 must file for FY2025.",
        "EU", "Large", True, "2025",
    ),
    (
        "CSRD", "CSRD SME Filing Deadline (voluntary)",
        "2027-03-31", "Listed SMEs may voluntarily adopt CSRD reporting for FY2026.",
        "EU", "SME", False, "2026",
    ),
    # ── SFDR ────────────────────────────────────────────────────────────────────
    (
        "SFDR", "SFDR PAI Annual Report 2024",
        "2024-06-30", "Financial market participants must publish annual PAI (Principal Adverse Impact) statements for reference period 2023.",
        "EU", "All", True, "2023",
    ),
    (
        "SFDR", "SFDR PAI Annual Report 2025",
        "2025-06-30", "PAI statement for reference period 2024.",
        "EU", "All", True, "2024",
    ),
    (
        "SFDR", "SFDR PAI Annual Report 2026",
        "2026-06-30", "PAI statement for reference period 2025.",
        "EU", "All", True, "2025",
    ),
    # ── EU Taxonomy ─────────────────────────────────────────────────────────────
    (
        "EU_TAXONOMY", "EU Taxonomy KPI Disclosure FY2024",
        "2025-04-30", "Non-financial reporting entities must disclose EU Taxonomy alignment KPIs (turnover, capex, opex) for FY2024.",
        "EU", "Large", True, "2024",
    ),
    (
        "EU_TAXONOMY", "EU Taxonomy KPI Disclosure FY2025",
        "2026-04-30", "Taxonomy KPI disclosure for FY2025.",
        "EU", "Large", True, "2025",
    ),
    # ── TCFD ────────────────────────────────────────────────────────────────────
    (
        "TCFD", "UK TCFD Mandatory Reporting FY2024",
        "2025-04-30", "UK-listed companies and large asset managers must include TCFD-aligned disclosures in annual reports for FY2024.",
        "UK", "Large", True, "2024",
    ),
    (
        "TCFD", "UK TCFD Mandatory Reporting FY2025",
        "2026-04-30", "UK mandatory TCFD for FY2025.",
        "UK", "Large", True, "2025",
    ),
    # ── GRI ─────────────────────────────────────────────────────────────────────
    (
        "GRI", "GRI Annual Report (voluntary)",
        "2025-06-30", "Voluntary GRI Standards sustainability report recommended publication date for calendar-year companies.",
        "Global", "All", False, "2024",
    ),
    # ── SEC ─────────────────────────────────────────────────────────────────────
    (
        "SEC_ESG", "SEC Climate Disclosure Rule — Large Accelerated Filers",
        "2026-02-28", "SEC-registered large accelerated filers must begin climate-related disclosure in 10-K filings for FY2025.",
        "US", "Large", True, "2025",
    ),
]


def upgrade() -> None:
    op.create_table(
        "regulatory_deadlines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("framework_code", sa.String(30), nullable=False),
        sa.Column("deadline_name", sa.String(500), nullable=False),
        sa.Column("deadline_date", sa.Date, nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("jurisdiction", sa.String(10), nullable=False, server_default="EU"),
        sa.Column("entity_size", sa.String(20), nullable=False, server_default="All"),
        sa.Column("is_mandatory", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("reporting_year", sa.String(4), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_reg_deadline_jurisdiction", "regulatory_deadlines", ["jurisdiction"])
    op.create_index("ix_reg_deadline_framework", "regulatory_deadlines", ["framework_code"])
    op.create_index("ix_reg_deadline_date", "regulatory_deadlines", ["deadline_date"])

    # Seed deadlines
    table = sa.table(
        "regulatory_deadlines",
        sa.column("id", sa.String),
        sa.column("framework_code", sa.String),
        sa.column("deadline_name", sa.String),
        sa.column("deadline_date", sa.Date),
        sa.column("description", sa.Text),
        sa.column("jurisdiction", sa.String),
        sa.column("entity_size", sa.String),
        sa.column("is_mandatory", sa.Boolean),
        sa.column("reporting_year", sa.String),
        sa.column("organization_id", sa.String),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": str(uuid.uuid4()),
                "framework_code": fw,
                "deadline_name": name,
                "deadline_date": date.fromisoformat(date_str),
                "description": desc,
                "jurisdiction": jur,
                "entity_size": size,
                "is_mandatory": mandatory,
                "reporting_year": year,
                "organization_id": None,
            }
            for fw, name, date_str, desc, jur, size, mandatory, year in _DEADLINES
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_reg_deadline_date", table_name="regulatory_deadlines")
    op.drop_index("ix_reg_deadline_framework", table_name="regulatory_deadlines")
    op.drop_index("ix_reg_deadline_jurisdiction", table_name="regulatory_deadlines")
    op.drop_table("regulatory_deadlines")
