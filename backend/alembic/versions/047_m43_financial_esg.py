"""M43 — Financial ESG, Value Creation & Capital Markets Platform.

Creates 20 new tables:
  financial_esg_kpis, financial_kpi_measurements,
  carbon_cost_models, cost_of_risk_assessments,
  value_creation_initiatives, sustainable_finance_instruments,
  taxonomy_alignment_assessments, green_revenue_records,
  green_capex_records, green_opex_records,
  transition_plans, transition_plan_milestones,
  finance_linked_kpis, capital_markets_assessments,
  investor_disclosure_packages, climate_finance_analyses,
  sustainability_valuation_models, esg_financial_correlations,
  financial_scenario_analyses, financial_esg_reports

ORM table count: 168 → 188

Revision ID: 047
Revises: 046
Create Date: 2026-06-22

Migration integrity:
  - All PKs: String(36) UUID
  - FKs: financial_kpi_measurements → financial_esg_kpis (CASCADE)
         transition_plan_milestones → transition_plans (CASCADE)
         finance_linked_kpis → sustainable_finance_instruments (CASCADE)
  - Indexes: organization_id on every table (tenant lookup)
             kpi_id on financial_kpi_measurements (measurement lookup)
             plan_id on transition_plan_milestones (milestone lookup)
             instrument_id on finance_linked_kpis (covenant lookup)
  - Unique constraints: none (natural duplicates allowed — multiple
    assessments per year are valid)
  - Nullable: all optional fields nullable; computed fields default 0.0
  - BaseModel columns: id, status, version, owner,
    created_by, updated_by, created_at, updated_at on every table
"""

import sqlalchemy as sa

from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None

# Common BaseModel columns added to every table
_BASE = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def _base():
    """Return a fresh copy of BaseModel columns."""
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    # ── financial_esg_kpis ────────────────────────────────────────────────────
    op.create_table(
        "financial_esg_kpis",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("formula", sa.Text, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="QUARTERLY"),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
    )
    op.create_index("ix_financial_esg_kpis_org", "financial_esg_kpis", ["organization_id"])

    # ── financial_kpi_measurements ────────────────────────────────────────────
    op.create_table(
        "financial_kpi_measurements",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "kpi_id",
            sa.String(36),
            sa.ForeignKey("financial_esg_kpis.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_fin_kpi_measurements_org", "financial_kpi_measurements", ["organization_id"]
    )
    op.create_index("ix_fin_kpi_measurements_kpi", "financial_kpi_measurements", ["kpi_id"])

    # ── carbon_cost_models ────────────────────────────────────────────────────
    op.create_table(
        "carbon_cost_models",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("assessment_year", sa.Integer, nullable=False),
        sa.Column("total_emissions", sa.Float, nullable=False, server_default="0"),
        sa.Column("internal_carbon_price", sa.Float, nullable=False, server_default="0"),
        sa.Column("regulatory_carbon_price", sa.Float, nullable=False, server_default="0"),
        sa.Column("avoided_emissions", sa.Float, nullable=False, server_default="0"),
        sa.Column("avoided_cost", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_carbon_cost", sa.Float, nullable=False, server_default="0"),
        sa.Column("regulatory_exposure", sa.Float, nullable=False, server_default="0"),
        sa.Column("formula", sa.JSON, nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("inventory_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_carbon_cost_models_org", "carbon_cost_models", ["organization_id"])

    # ── cost_of_risk_assessments ──────────────────────────────────────────────
    op.create_table(
        "cost_of_risk_assessments",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("assessment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_risk_score", sa.Float, nullable=False),
        sa.Column("climate_risk_score", sa.Float, nullable=False),
        sa.Column("compliance_risk_score", sa.Float, nullable=False),
        sa.Column("operational_risk_score", sa.Float, nullable=False),
        sa.Column("exposure_base", sa.Float, nullable=False),
        sa.Column("composite_risk_score", sa.Float, nullable=False),
        sa.Column("estimated_financial_exposure", sa.Float, nullable=False),
        sa.Column("expected_loss", sa.Float, nullable=False),
        sa.Column("risk_adjusted_exposure", sa.Float, nullable=False),
        sa.Column("methodology", sa.JSON, nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_cost_of_risk_assessments_org", "cost_of_risk_assessments", ["organization_id"]
    )

    # ── value_creation_initiatives ────────────────────────────────────────────
    op.create_table(
        "value_creation_initiatives",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("investment_amount", sa.Float, nullable=False, server_default="0"),
        sa.Column("expected_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("realized_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("roi_percent", sa.Float, nullable=True),
        sa.Column("payback_period_months", sa.Integer, nullable=True),
        sa.Column("initiative_status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("category", sa.String(50), nullable=True),
    )
    op.create_index(
        "ix_value_creation_initiatives_org", "value_creation_initiatives", ["organization_id"]
    )

    # ── sustainable_finance_instruments ──────────────────────────────────────
    op.create_table(
        "sustainable_finance_instruments",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("instrument_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("maturity_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("covenant_status", sa.String(20), nullable=False, server_default="MONITORING"),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("counterparty", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("kpi_linkage", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_sustainable_finance_instruments_org",
        "sustainable_finance_instruments",
        ["organization_id"],
    )

    # ── taxonomy_alignment_assessments ────────────────────────────────────────
    op.create_table(
        "taxonomy_alignment_assessments",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "taxonomy_framework", sa.String(50), nullable=False, server_default="EU_TAXONOMY"
        ),
        sa.Column("assessment_year", sa.Integer, nullable=False),
        sa.Column("eligible_activities", sa.JSON, nullable=True),
        sa.Column("aligned_activities", sa.JSON, nullable=True),
        sa.Column("eligible_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("aligned_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("assessment_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("total_revenue", sa.Float, nullable=True),
        sa.Column("total_capex", sa.Float, nullable=True),
        sa.Column("total_opex", sa.Float, nullable=True),
    )
    op.create_index(
        "ix_taxonomy_alignment_assessments_org",
        "taxonomy_alignment_assessments",
        ["organization_id"],
    )

    # ── green_revenue_records ─────────────────────────────────────────────────
    op.create_table(
        "green_revenue_records",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("revenue_stream", sa.String(255), nullable=False),
        sa.Column("taxonomy_category", sa.String(100), nullable=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("alignment_status", sa.String(20), nullable=False, server_default="ELIGIBLE"),
        sa.Column("total_revenue", sa.Float, nullable=False, server_default="0"),
        sa.Column("green_revenue_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_green_revenue_records_org", "green_revenue_records", ["organization_id"])

    # ── green_capex_records ───────────────────────────────────────────────────
    op.create_table(
        "green_capex_records",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("taxonomy_category", sa.String(100), nullable=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("alignment_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_green_capex_records_org", "green_capex_records", ["organization_id"])

    # ── green_opex_records ────────────────────────────────────────────────────
    op.create_table(
        "green_opex_records",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("alignment_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_green_opex_records_org", "green_opex_records", ["organization_id"])

    # ── transition_plans ──────────────────────────────────────────────────────
    op.create_table(
        "transition_plans",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("baseline_state", sa.JSON, nullable=True),
        sa.Column("target_state", sa.JSON, nullable=True),
        sa.Column("financing_needs", sa.Float, nullable=False, server_default="0"),
        sa.Column("funding_sources", sa.JSON, nullable=True),
        sa.Column("plan_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
    )
    op.create_index("ix_transition_plans_org", "transition_plans", ["organization_id"])

    # ── transition_plan_milestones ────────────────────────────────────────────
    op.create_table(
        "transition_plan_milestones",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "plan_id",
            sa.String(36),
            sa.ForeignKey("transition_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("milestone_status", sa.String(20), nullable=False, server_default="PENDING"),
    )
    op.create_index(
        "ix_transition_plan_milestones_org", "transition_plan_milestones", ["organization_id"]
    )
    op.create_index("ix_transition_plan_milestones_plan", "transition_plan_milestones", ["plan_id"])

    # ── finance_linked_kpis ───────────────────────────────────────────────────
    op.create_table(
        "finance_linked_kpis",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "instrument_id",
            sa.String(36),
            sa.ForeignKey("sustainable_finance_instruments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("esg_target_id", sa.String(36), nullable=True),
        sa.Column("kpi_name", sa.String(255), nullable=False),
        sa.Column("kpi_description", sa.Text, nullable=True),
        sa.Column("threshold_value", sa.Float, nullable=True),
        sa.Column("threshold_direction", sa.String(10), nullable=False, server_default="BELOW"),
        sa.Column("covenant_status", sa.String(20), nullable=False, server_default="COMPLIANT"),
        sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
    )
    op.create_index("ix_finance_linked_kpis_org", "finance_linked_kpis", ["organization_id"])
    op.create_index("ix_finance_linked_kpis_instrument", "finance_linked_kpis", ["instrument_id"])

    # ── capital_markets_assessments ───────────────────────────────────────────
    op.create_table(
        "capital_markets_assessments",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "disclosure_readiness", sa.String(20), nullable=False, server_default="NOT_READY"
        ),
        sa.Column("assurance_readiness", sa.String(20), nullable=False, server_default="NOT_READY"),
        sa.Column("taxonomy_readiness", sa.String(20), nullable=False, server_default="NOT_READY"),
        sa.Column("kpi_readiness", sa.String(20), nullable=False, server_default="NOT_READY"),
        sa.Column("overall_readiness", sa.String(20), nullable=False, server_default="NOT_READY"),
        sa.Column("assessment_notes", sa.JSON, nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_capital_markets_assessments_org", "capital_markets_assessments", ["organization_id"]
    )

    # ── investor_disclosure_packages ──────────────────────────────────────────
    op.create_table(
        "investor_disclosure_packages",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("esg_kpi_snapshot", sa.JSON, nullable=True),
        sa.Column("taxonomy_snapshot", sa.JSON, nullable=True),
        sa.Column("climate_metrics_snapshot", sa.JSON, nullable=True),
        sa.Column("assurance_status_snapshot", sa.JSON, nullable=True),
        sa.Column("sustainability_targets_snapshot", sa.JSON, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_investor_disclosure_packages_org", "investor_disclosure_packages", ["organization_id"]
    )

    # ── climate_finance_analyses ──────────────────────────────────────────────
    op.create_table(
        "climate_finance_analyses",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("analysis_name", sa.String(255), nullable=False),
        sa.Column("analysis_year", sa.Integer, nullable=False),
        sa.Column("transition_investment", sa.Float, nullable=False, server_default="0"),
        sa.Column("emissions_reduction", sa.Float, nullable=False, server_default="0"),
        sa.Column("cost_per_ton_reduced", sa.Float, nullable=True),
        sa.Column("roi_percent", sa.Float, nullable=True),
        sa.Column("methodology", sa.JSON, nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_climate_finance_analyses_org", "climate_finance_analyses", ["organization_id"]
    )

    # ── sustainability_valuation_models ───────────────────────────────────────
    op.create_table(
        "sustainability_valuation_models",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("valuation_name", sa.String(255), nullable=False),
        sa.Column("valuation_year", sa.Integer, nullable=False),
        sa.Column("risk_reduction_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("carbon_reduction_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("operational_efficiency_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_sustainability_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("methodology", sa.JSON, nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_sustainability_valuation_models_org",
        "sustainability_valuation_models",
        ["organization_id"],
    )

    # ── esg_financial_correlations ────────────────────────────────────────────
    op.create_table(
        "esg_financial_correlations",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("scorecard_id", sa.String(36), nullable=True),
        sa.Column("correlation_period", sa.String(20), nullable=False),
        sa.Column("esg_score", sa.Float, nullable=False),
        sa.Column("risk_reduction", sa.Float, nullable=False, server_default="0"),
        sa.Column("cost_reduction", sa.Float, nullable=False, server_default="0"),
        sa.Column("financial_performance", sa.Float, nullable=False, server_default="0"),
        sa.Column("correlation_coefficient", sa.Float, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_esg_financial_correlations_org", "esg_financial_correlations", ["organization_id"]
    )

    # ── financial_scenario_analyses ───────────────────────────────────────────
    op.create_table(
        "financial_scenario_analyses",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("scenario_type", sa.String(50), nullable=False),
        sa.Column("inputs", sa.JSON, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
        sa.Column("outputs", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_financial_scenario_analyses_org", "financial_scenario_analyses", ["organization_id"]
    )

    # ── financial_esg_reports ─────────────────────────────────────────────────
    op.create_table(
        "financial_esg_reports",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("report_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value_creation_snapshot", sa.JSON, nullable=True),
        sa.Column("carbon_economics_snapshot", sa.JSON, nullable=True),
        sa.Column("taxonomy_snapshot", sa.JSON, nullable=True),
        sa.Column("green_revenue_snapshot", sa.JSON, nullable=True),
        sa.Column("sustainable_finance_snapshot", sa.JSON, nullable=True),
        sa.Column("readiness_snapshot", sa.JSON, nullable=True),
        sa.Column("overall_status", sa.String(10), nullable=False, server_default="DRAFT"),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_financial_esg_reports_org", "financial_esg_reports", ["organization_id"])


def downgrade() -> None:
    # Drop in reverse dependency order:
    # financial_esg_reports (no deps on M43 tables)
    op.drop_index("ix_financial_esg_reports_org", table_name="financial_esg_reports")
    op.drop_table("financial_esg_reports")

    op.drop_index("ix_financial_scenario_analyses_org", table_name="financial_scenario_analyses")
    op.drop_table("financial_scenario_analyses")

    op.drop_index("ix_esg_financial_correlations_org", table_name="esg_financial_correlations")
    op.drop_table("esg_financial_correlations")

    op.drop_index(
        "ix_sustainability_valuation_models_org", table_name="sustainability_valuation_models"
    )
    op.drop_table("sustainability_valuation_models")

    op.drop_index("ix_climate_finance_analyses_org", table_name="climate_finance_analyses")
    op.drop_table("climate_finance_analyses")

    op.drop_index("ix_investor_disclosure_packages_org", table_name="investor_disclosure_packages")
    op.drop_table("investor_disclosure_packages")

    op.drop_index("ix_capital_markets_assessments_org", table_name="capital_markets_assessments")
    op.drop_table("capital_markets_assessments")

    # finance_linked_kpis FK → sustainable_finance_instruments: drop child first
    op.drop_index("ix_finance_linked_kpis_instrument", table_name="finance_linked_kpis")
    op.drop_index("ix_finance_linked_kpis_org", table_name="finance_linked_kpis")
    op.drop_table("finance_linked_kpis")

    # transition_plan_milestones FK → transition_plans: drop child first
    op.drop_index("ix_transition_plan_milestones_plan", table_name="transition_plan_milestones")
    op.drop_index("ix_transition_plan_milestones_org", table_name="transition_plan_milestones")
    op.drop_table("transition_plan_milestones")

    op.drop_index("ix_transition_plans_org", table_name="transition_plans")
    op.drop_table("transition_plans")

    op.drop_index("ix_green_opex_records_org", table_name="green_opex_records")
    op.drop_table("green_opex_records")

    op.drop_index("ix_green_capex_records_org", table_name="green_capex_records")
    op.drop_table("green_capex_records")

    op.drop_index("ix_green_revenue_records_org", table_name="green_revenue_records")
    op.drop_table("green_revenue_records")

    op.drop_index(
        "ix_taxonomy_alignment_assessments_org", table_name="taxonomy_alignment_assessments"
    )
    op.drop_table("taxonomy_alignment_assessments")

    # sustainable_finance_instruments: child finance_linked_kpis already dropped
    op.drop_index(
        "ix_sustainable_finance_instruments_org", table_name="sustainable_finance_instruments"
    )
    op.drop_table("sustainable_finance_instruments")

    op.drop_index("ix_value_creation_initiatives_org", table_name="value_creation_initiatives")
    op.drop_table("value_creation_initiatives")

    op.drop_index("ix_cost_of_risk_assessments_org", table_name="cost_of_risk_assessments")
    op.drop_table("cost_of_risk_assessments")

    op.drop_index("ix_carbon_cost_models_org", table_name="carbon_cost_models")
    op.drop_table("carbon_cost_models")

    # financial_kpi_measurements FK → financial_esg_kpis: drop child first
    op.drop_index("ix_fin_kpi_measurements_kpi", table_name="financial_kpi_measurements")
    op.drop_index("ix_fin_kpi_measurements_org", table_name="financial_kpi_measurements")
    op.drop_table("financial_kpi_measurements")

    # financial_esg_kpis: child measurements already dropped
    op.drop_index("ix_financial_esg_kpis_org", table_name="financial_esg_kpis")
    op.drop_table("financial_esg_kpis")
