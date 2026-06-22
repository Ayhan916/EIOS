"""M42 — Sustainability Performance Management & Decarbonization Platform.

Creates 19 new tables:
  sustainability_objectives, esg_targets, esg_kpis, kpi_measurements,
  sustainability_scorecards, emission_sources, carbon_inventories,
  decarbonization_initiatives, net_zero_roadmaps, net_zero_milestones,
  science_based_targets, climate_risk_assessments,
  sustainability_assurance_records, csrd_performance_mappings,
  issb_sustainability_mappings, kpi_alerts, performance_forecasts,
  scenario_analyses, sustainability_performance_reports

ORM table count: 149 → 168

Revision ID: 046
Revises: 045
Create Date: 2026-06-22
"""

import sqlalchemy as sa
from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sustainability_objectives ──────────────────────────────────────────────
    op.create_table(
        "sustainability_objectives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("objective_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("program_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── esg_targets ───────────────────────────────────────────────────────────
    op.create_table(
        "esg_targets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("objective_id", sa.String(36), sa.ForeignKey("sustainability_objectives.id"), nullable=False),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("baseline_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("target_value", sa.Float, nullable=False),
        sa.Column("target_unit", sa.String(50), nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
        sa.Column("measurement_frequency", sa.String(20), nullable=False, server_default="QUARTERLY"),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── esg_kpis ──────────────────────────────────────────────────────────────
    op.create_table(
        "esg_kpis",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("formula", sa.Text, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="QUARTERLY"),
        sa.Column("target_value", sa.Float, nullable=True),
        sa.Column("alert_threshold", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── kpi_measurements ──────────────────────────────────────────────────────
    op.create_table(
        "kpi_measurements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kpi_id", sa.String(36), sa.ForeignKey("esg_kpis.id"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measured_value", sa.Float, nullable=False),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("recorded_by", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── kpi_alerts ────────────────────────────────────────────────────────────
    op.create_table(
        "kpi_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kpi_id", sa.String(36), sa.ForeignKey("esg_kpis.id"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("alert_type", sa.String(30), nullable=False),
        sa.Column("triggered_value", sa.Float, nullable=False),
        sa.Column("threshold_value", sa.Float, nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── sustainability_scorecards ──────────────────────────────────────────────
    op.create_table(
        "sustainability_scorecards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("environmental_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("social_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("governance_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("calculation_method", sa.Text, nullable=True),
        sa.Column("score_data", sa.JSON, nullable=True),
        sa.Column("generated_by", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── emission_sources ──────────────────────────────────────────────────────
    op.create_table(
        "emission_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("inventory_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scope", sa.String(10), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("activity_data", sa.Float, nullable=False),
        sa.Column("activity_unit", sa.String(50), nullable=True),
        sa.Column("emission_factor", sa.Float, nullable=False),
        sa.Column("emission_factor_unit", sa.String(50), nullable=True),
        sa.Column("calculated_emissions", sa.Float, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reporting_year", sa.Integer, nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── carbon_inventories ────────────────────────────────────────────────────
    op.create_table(
        "carbon_inventories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("reporting_year", sa.Integer, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope1_emissions", sa.Float, nullable=False, server_default="0"),
        sa.Column("scope2_emissions", sa.Float, nullable=False, server_default="0"),
        sa.Column("scope3_emissions", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_emissions", sa.Float, nullable=False, server_default="0"),
        sa.Column("unit", sa.String(20), nullable=False, server_default="tCO2e"),
        sa.Column("inventory_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "reporting_year", name="uq_carbon_inventory_org_year"),
    )

    # ── decarbonization_initiatives ───────────────────────────────────────────
    op.create_table(
        "decarbonization_initiatives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("roadmap_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("initiative_type", sa.String(40), nullable=False),
        sa.Column("expected_reduction", sa.Float, nullable=False, server_default="0"),
        sa.Column("actual_reduction", sa.Float, nullable=True),
        sa.Column("cost_estimate", sa.Float, nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("initiative_status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── net_zero_roadmaps ─────────────────────────────────────────────────────
    op.create_table(
        "net_zero_roadmaps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("baseline_year", sa.Integer, nullable=False),
        sa.Column("target_year", sa.Integer, nullable=False),
        sa.Column("baseline_emissions", sa.Float, nullable=False),
        sa.Column("target_reduction_percent", sa.Float, nullable=False),
        sa.Column("target_emissions", sa.Float, nullable=False),
        sa.Column("roadmap_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── net_zero_milestones ───────────────────────────────────────────────────
    op.create_table(
        "net_zero_milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("roadmap_id", sa.String(36), sa.ForeignKey("net_zero_roadmaps.id"), nullable=False),
        sa.Column("milestone_year", sa.Integer, nullable=False),
        sa.Column("target_emissions", sa.Float, nullable=False),
        sa.Column("actual_emissions", sa.Float, nullable=True),
        sa.Column("milestone_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── science_based_targets ─────────────────────────────────────────────────
    op.create_table(
        "science_based_targets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("baseline_year", sa.Integer, nullable=False),
        sa.Column("baseline_emissions", sa.Float, nullable=False),
        sa.Column("target_reduction_percent", sa.Float, nullable=False),
        sa.Column("target_year", sa.Integer, nullable=False),
        sa.Column("sbt_framework", sa.String(20), nullable=False, server_default="SBTi"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("commitment_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sbt_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── climate_risk_assessments ──────────────────────────────────────────────
    op.create_table(
        "climate_risk_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("assessment_year", sa.Integer, nullable=False),
        sa.Column("scenario", sa.String(10), nullable=False, server_default="2C"),
        sa.Column("transition_risk_score", sa.Float, nullable=False),
        sa.Column("physical_risk_score", sa.Float, nullable=False),
        sa.Column("regulatory_risk_score", sa.Float, nullable=False),
        sa.Column("overall_risk_score", sa.Float, nullable=False),
        sa.Column("transition_risk_details", sa.JSON, nullable=True),
        sa.Column("physical_risk_details", sa.JSON, nullable=True),
        sa.Column("regulatory_risk_details", sa.JSON, nullable=True),
        sa.Column("network_entity_id", sa.String(36), nullable=True),
        sa.Column("regulation_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── sustainability_assurance_records ──────────────────────────────────────
    op.create_table(
        "sustainability_assurance_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("reviewed_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer_user_id", sa.String(36), nullable=False),
        sa.Column("assurance_level", sa.String(20), nullable=False),
        sa.Column("findings", sa.JSON, nullable=True),
        sa.Column("assurance_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── csrd_performance_mappings ─────────────────────────────────────────────
    op.create_table(
        "csrd_performance_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("kpi_id", sa.String(36), nullable=True),
        sa.Column("objective_id", sa.String(36), nullable=True),
        sa.Column("target_id", sa.String(36), nullable=True),
        sa.Column("esrs_standard", sa.String(10), nullable=False),
        sa.Column("disclosure_requirement", sa.String(255), nullable=True),
        sa.Column("data_point_reference", sa.String(255), nullable=True),
        sa.Column("mapping_compliance_status", sa.String(20), nullable=False, server_default="NOT_ASSESSED"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── issb_sustainability_mappings ──────────────────────────────────────────
    op.create_table(
        "issb_sustainability_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("kpi_id", sa.String(36), nullable=True),
        sa.Column("objective_id", sa.String(36), nullable=True),
        sa.Column("issb_standard", sa.String(10), nullable=False),
        sa.Column("disclosure_topic", sa.String(255), nullable=True),
        sa.Column("metric_reference", sa.String(255), nullable=True),
        sa.Column("mapping_compliance_status", sa.String(20), nullable=False, server_default="NOT_ASSESSED"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── performance_forecasts ─────────────────────────────────────────────────
    op.create_table(
        "performance_forecasts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("kpi_id", sa.String(36), nullable=True),
        sa.Column("forecast_type", sa.String(30), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_horizon_months", sa.Integer, nullable=False),
        sa.Column("historical_data", sa.JSON, nullable=False),
        sa.Column("forecast_data", sa.JSON, nullable=False),
        sa.Column("confidence_interval", sa.JSON, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── scenario_analyses ─────────────────────────────────────────────────────
    op.create_table(
        "scenario_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scenario_type", sa.String(40), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("inputs", sa.JSON, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
        sa.Column("outputs", sa.JSON, nullable=True),
        sa.Column("scenario_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── sustainability_performance_reports ────────────────────────────────────
    op.create_table(
        "sustainability_performance_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("kpi_summary", sa.JSON, nullable=True),
        sa.Column("emissions_summary", sa.JSON, nullable=True),
        sa.Column("target_progress", sa.JSON, nullable=True),
        sa.Column("objective_status", sa.JSON, nullable=True),
        sa.Column("overall_status", sa.String(10), nullable=False, server_default="RED"),
        sa.Column("generated_by", sa.String(36), nullable=False),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("updated_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sustainability_performance_reports")
    op.drop_table("scenario_analyses")
    op.drop_table("performance_forecasts")
    op.drop_table("issb_sustainability_mappings")
    op.drop_table("csrd_performance_mappings")
    op.drop_table("sustainability_assurance_records")
    op.drop_table("climate_risk_assessments")
    op.drop_table("science_based_targets")
    op.drop_table("net_zero_milestones")
    op.drop_table("net_zero_roadmaps")
    op.drop_table("decarbonization_initiatives")
    op.drop_table("carbon_inventories")
    op.drop_table("emission_sources")
    op.drop_table("sustainability_scorecards")
    op.drop_table("kpi_alerts")
    op.drop_table("kpi_measurements")
    op.drop_table("esg_kpis")
    op.drop_table("esg_targets")
    op.drop_table("sustainability_objectives")
