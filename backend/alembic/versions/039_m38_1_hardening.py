"""M38 + M38.1 Supplier Network Intelligence — tables and hardening.

Changes:
  CREATE (M38):
    supplier_relationships, suggested_relationships, network_exposure_signals,
    supplier_criticality, dependency_analyses, resilience_assessments,
    incident_clusters

  CREATE (M38.1):
    network_watchlist_entries

  INDEX (M38.1 P0):
    partial unique index on network_exposure_signals
    (organization_id, origin_supplier_id, impacted_supplier_id, exposure_type)
    WHERE exposure_status = 'ACTIVE'

Revision ID: 039
Revises: 038
Create Date: 2026-06-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None

# Shared base columns (mirrors BaseModel)
_BASE = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def _base():
    """Return fresh copies of base columns (Column objects are not reusable)."""
    return [
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
    # ── M38: supplier_relationships ──────────────────────────────────────────
    op.create_table(
        "supplier_relationships",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("related_supplier_id", sa.String(36), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("relationship_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by", sa.String(36), nullable=True),
        sa.Column("calculation_inputs", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_rel_org", "supplier_relationships", ["organization_id"])
    op.create_index("ix_rel_supplier", "supplier_relationships", ["supplier_id"])
    op.create_index("ix_rel_related", "supplier_relationships", ["related_supplier_id"])
    op.create_index("ix_rel_type", "supplier_relationships", ["relationship_type"])
    op.create_index("ix_rel_status", "supplier_relationships", ["relationship_status"])

    # ── M38: suggested_relationships ─────────────────────────────────────────
    op.create_table(
        "suggested_relationships",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("related_supplier_id", sa.String(36), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("suggestion_source", sa.String(50), nullable=False),
        sa.Column("suggestion_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("calculation_inputs", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_sugg_org", "suggested_relationships", ["organization_id"])
    op.create_index("ix_sugg_supplier", "suggested_relationships", ["supplier_id"])
    op.create_index("ix_sugg_status", "suggested_relationships", ["suggestion_status"])

    # ── M38: network_exposure_signals ────────────────────────────────────────
    op.create_table(
        "network_exposure_signals",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("origin_supplier_id", sa.String(36), nullable=False),
        sa.Column("impacted_supplier_id", sa.String(36), nullable=False),
        sa.Column("exposure_type", sa.String(50), nullable=False),
        sa.Column("propagation_path", JSONB, nullable=False, server_default="[]"),
        sa.Column("path_length", sa.Integer, nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("source_signal_id", sa.String(36), nullable=True),
        sa.Column("source_finding_id", sa.String(36), nullable=True),
        sa.Column("exposure_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculation_inputs", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_nexp_org", "network_exposure_signals", ["organization_id"])
    op.create_index("ix_nexp_origin", "network_exposure_signals", ["origin_supplier_id"])
    op.create_index("ix_nexp_impacted", "network_exposure_signals", ["impacted_supplier_id"])
    op.create_index("ix_nexp_status", "network_exposure_signals", ["exposure_status"])
    op.create_index("ix_nexp_type", "network_exposure_signals", ["exposure_type"])

    # ── M38: supplier_criticality ────────────────────────────────────────────
    op.create_table(
        "supplier_criticality",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("criticality", sa.String(20), nullable=False),
        sa.Column("criticality_score", sa.Float, nullable=False),
        sa.Column("degree_centrality", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("inbound_degree", sa.Integer, nullable=False, server_default="0"),
        sa.Column("outbound_degree", sa.Integer, nullable=False, server_default="0"),
        sa.Column("connected_component_size", sa.Integer, nullable=False, server_default="1"),
        sa.Column("dependency_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("assessment_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("finding_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("open_remediation_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("calculation_inputs", JSONB, nullable=False, server_default="{}"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_crit_org", "supplier_criticality", ["organization_id"])
    op.create_index("ix_crit_supplier", "supplier_criticality", ["supplier_id"])
    op.create_index("ix_crit_level", "supplier_criticality", ["criticality"])

    # ── M38: dependency_analyses ─────────────────────────────────────────────
    op.create_table(
        "dependency_analyses",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("dependency_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("concentration_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("diversification_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("critical_supplier_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("single_point_of_failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("calculation_inputs", JSONB, nullable=False, server_default="{}"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dep_org", "dependency_analyses", ["organization_id"])
    op.create_index("ix_dep_supplier", "dependency_analyses", ["supplier_id"])

    # ── M38: resilience_assessments ──────────────────────────────────────────
    op.create_table(
        "resilience_assessments",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("resilience_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("diversification_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("concentration_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("redundancy_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("calculation_inputs", JSONB, nullable=False, server_default="{}"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_res_org", "resilience_assessments", ["organization_id"])
    op.create_index("ix_res_supplier", "resilience_assessments", ["supplier_id"])

    # ── M38: incident_clusters ───────────────────────────────────────────────
    op.create_table(
        "incident_clusters",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("cluster_name", sa.String(500), nullable=False),
        sa.Column("root_cause", sa.Text, nullable=False, server_default=""),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("cluster_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("affected_supplier_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("finding_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("signal_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("risk_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("compliance_gap_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.Column("calculation_inputs", JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_cluster_org", "incident_clusters", ["organization_id"])
    op.create_index("ix_cluster_status", "incident_clusters", ["cluster_status"])
    op.create_index("ix_cluster_severity", "incident_clusters", ["severity"])

    # ── M38.1 P0: partial unique index on network_exposure_signals ───────────
    op.create_index(
        "uq_nexp_active_signal",
        "network_exposure_signals",
        ["organization_id", "origin_supplier_id", "impacted_supplier_id", "exposure_type"],
        unique=True,
        postgresql_where=sa.text("exposure_status = 'ACTIVE'"),
    )

    # ── M38.1: network_watchlist_entries ─────────────────────────────────────
    op.create_table(
        "network_watchlist_entries",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("watched_supplier_id", sa.String(36), nullable=False),
        sa.Column("related_supplier_id", sa.String(36), nullable=False),
        sa.Column("distance", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_nwl_org", "network_watchlist_entries", ["organization_id"])
    op.create_index("ix_nwl_watched", "network_watchlist_entries", ["watched_supplier_id"])
    op.create_index("ix_nwl_related", "network_watchlist_entries", ["related_supplier_id"])
    op.create_unique_constraint(
        "uq_nwl_pair",
        "network_watchlist_entries",
        ["organization_id", "watched_supplier_id", "related_supplier_id"],
    )


def downgrade() -> None:
    op.drop_table("network_watchlist_entries")
    op.drop_index("uq_nexp_active_signal", table_name="network_exposure_signals")
    op.drop_table("incident_clusters")
    op.drop_table("resilience_assessments")
    op.drop_table("dependency_analyses")
    op.drop_table("supplier_criticality")
    op.drop_table("network_exposure_signals")
    op.drop_table("suggested_relationships")
    op.drop_table("supplier_relationships")
