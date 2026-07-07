"""m34_external_intelligence

M34 — External Data & Benchmarking Intelligence.

New tables:
  external_datasets       — versioned, immutable external data sources
  country_risk_profiles   — per-country risk scores from external datasets
  sector_benchmarks       — sector-level ESG benchmarks
  external_risk_signals   — adverse signals (sanctions, corruption, etc.)
  supplier_enrichments    — tenant-scoped combined intelligence per supplier

Revision ID: 033
Revises: 032
Create Date: 2026-06-19
"""

import sqlalchemy as sa

from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None

_BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    # ── external_datasets ────────────────────────────────────────────────────
    op.create_table(
        "external_datasets",
        *_BASE_COLS,
        sa.Column("source_name", sa.String(50), nullable=False),
        sa.Column("source_version", sa.String(50), nullable=False),
        sa.Column("dataset_hash", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("dataset_status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.UniqueConstraint(
            "source_name", "source_version", name="uq_external_datasets_source_version"
        ),
    )
    op.create_index("ix_external_datasets_source", "external_datasets", ["source_name"])
    op.create_index("ix_external_datasets_status", "external_datasets", ["dataset_status"])

    # ── country_risk_profiles ────────────────────────────────────────────────
    op.create_table(
        "country_risk_profiles",
        *_BASE_COLS,
        sa.Column("country_code", sa.String(10), nullable=False),
        sa.Column("country_name", sa.String(200), nullable=False),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("governance_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("corruption_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("labour_rights_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("environmental_risk_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("human_rights_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("sanctions_status", sa.String(20), nullable=False, server_default="none"),
        sa.Column("overall_risk_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("source_name", sa.String(50), nullable=False, server_default=""),
        sa.Column("source_version", sa.String(50), nullable=False, server_default=""),
        sa.Column("data_date", sa.String(20), nullable=False, server_default=""),
    )
    op.create_index("ix_country_risk_code", "country_risk_profiles", ["country_code"])
    op.create_index("ix_country_risk_dataset", "country_risk_profiles", ["dataset_id"])
    op.create_index("ix_country_risk_level", "country_risk_profiles", ["risk_level"])

    # ── sector_benchmarks ────────────────────────────────────────────────────
    op.create_table(
        "sector_benchmarks",
        *_BASE_COLS,
        sa.Column("sector_id", sa.String(36), nullable=False),
        sa.Column("sector_name", sa.String(200), nullable=False),
        sa.Column("nace_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("average_esg_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("average_risk_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("average_compliance_coverage", sa.Float, nullable=False, server_default="0"),
        sa.Column("average_disclosure_readiness", sa.Float, nullable=False, server_default="0"),
        sa.Column("supplier_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("p10_esg_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("p25_esg_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("p50_esg_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("p75_esg_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("p90_esg_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("source_name", sa.String(50), nullable=False, server_default=""),
        sa.Column("source_version", sa.String(50), nullable=False, server_default=""),
        sa.Column("benchmark_date", sa.String(20), nullable=False, server_default=""),
    )
    op.create_index("ix_sector_benchmarks_sector", "sector_benchmarks", ["sector_id"])
    op.create_index("ix_sector_benchmarks_nace", "sector_benchmarks", ["nace_code"])
    op.create_index("ix_sector_benchmarks_dataset", "sector_benchmarks", ["dataset_id"])

    # ── external_risk_signals ─────────────────────────────────────────────────
    op.create_table(
        "external_risk_signals",
        *_BASE_COLS,
        sa.Column("signal_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("source_name", sa.String(50), nullable=False),
        sa.Column("source_version", sa.String(50), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_id", sa.String(36), nullable=True),
        sa.Column("country_code", sa.String(10), nullable=False, server_default=""),
        sa.Column("sector_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("supplier_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("organization_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_ext_signals_supplier", "external_risk_signals", ["supplier_id"])
    op.create_index("ix_ext_signals_country", "external_risk_signals", ["country_code"])
    op.create_index("ix_ext_signals_org", "external_risk_signals", ["organization_id"])
    op.create_index("ix_ext_signals_type", "external_risk_signals", ["signal_type"])

    # ── supplier_enrichments ──────────────────────────────────────────────────
    op.create_table(
        "supplier_enrichments",
        *_BASE_COLS,
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("country_code", sa.String(10), nullable=False, server_default=""),
        sa.Column("country_risk_id", sa.String(36), nullable=True),
        sa.Column("country_risk_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("country_risk_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("sanctions_exposure", sa.String(20), nullable=False, server_default="none"),
        sa.Column("sector_benchmark_id", sa.String(36), nullable=True),
        sa.Column("sector_percentile", sa.Float, nullable=False, server_default="0"),
        sa.Column("percentile_rank", sa.String(20), nullable=False, server_default="median"),
        sa.Column("benchmark_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("benchmark_explanation", sa.Text, nullable=False, server_default=""),
        sa.Column("external_risk_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("combined_risk_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False, server_default=""),
        sa.Column("active_signal_count", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "supplier_id", "organization_id", name="uq_supplier_enrichments_supplier_org"
        ),
    )
    op.create_index("ix_supplier_enrichments_supplier", "supplier_enrichments", ["supplier_id"])
    op.create_index("ix_supplier_enrichments_org", "supplier_enrichments", ["organization_id"])
    op.create_index("ix_supplier_enrichments_risk", "supplier_enrichments", ["combined_risk_score"])


def downgrade() -> None:
    op.drop_index("ix_supplier_enrichments_risk", "supplier_enrichments")
    op.drop_index("ix_supplier_enrichments_org", "supplier_enrichments")
    op.drop_index("ix_supplier_enrichments_supplier", "supplier_enrichments")
    op.drop_table("supplier_enrichments")

    op.drop_index("ix_ext_signals_type", "external_risk_signals")
    op.drop_index("ix_ext_signals_org", "external_risk_signals")
    op.drop_index("ix_ext_signals_country", "external_risk_signals")
    op.drop_index("ix_ext_signals_supplier", "external_risk_signals")
    op.drop_table("external_risk_signals")

    op.drop_index("ix_sector_benchmarks_dataset", "sector_benchmarks")
    op.drop_index("ix_sector_benchmarks_nace", "sector_benchmarks")
    op.drop_index("ix_sector_benchmarks_sector", "sector_benchmarks")
    op.drop_table("sector_benchmarks")

    op.drop_index("ix_country_risk_level", "country_risk_profiles")
    op.drop_index("ix_country_risk_dataset", "country_risk_profiles")
    op.drop_index("ix_country_risk_code", "country_risk_profiles")
    op.drop_table("country_risk_profiles")

    op.drop_index("ix_external_datasets_status", "external_datasets")
    op.drop_index("ix_external_datasets_source", "external_datasets")
    op.drop_table("external_datasets")
