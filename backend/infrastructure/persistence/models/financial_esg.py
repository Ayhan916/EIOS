"""M43 — Financial ESG, Value Creation & Capital Markets Platform ORM Models.

20 new tables:
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
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel

# ── Enum constants ─────────────────────────────────────────────────────────────

FINANCIAL_KPI_CATEGORIES = (
    "VALUE_CREATION",
    "COST_REDUCTION",
    "CARBON_ECONOMICS",
    "RISK_REDUCTION",
    "INVESTMENT",
    "TAXONOMY",
    "DISCLOSURE",
)
FINANCIAL_KPI_FREQUENCIES = ("MONTHLY", "QUARTERLY", "ANNUAL")

INSTRUMENT_TYPES = (
    "GREEN_BOND",
    "SUSTAINABILITY_LINKED_LOAN",
    "SUSTAINABILITY_LINKED_BOND",
    "TRANSITION_FINANCE",
    "ESG_FUND",
)
COVENANT_STATUSES = ("COMPLIANT", "AT_RISK", "BREACHED", "MONITORING")

TAXONOMY_FRAMEWORKS = ("EU_TAXONOMY",)
TAXONOMY_ASSESSMENT_STATUSES = ("DRAFT", "SUBMITTED", "VERIFIED")
ALIGNMENT_STATUSES = ("ALIGNED", "ELIGIBLE", "NOT_ALIGNED")

READINESS_STATUSES = ("NOT_READY", "PARTIAL", "READY")

INITIATIVE_STATUSES_FIN = ("PLANNED", "ACTIVE", "COMPLETED", "CANCELLED")
PLAN_STATUSES = ("DRAFT", "ACTIVE", "COMPLETED")

SCENARIO_TYPES_FIN = (
    "CARBON_PRICE_INCREASE",
    "SUPPLIER_DISRUPTION",
    "CLIMATE_REGULATION",
    "ACCELERATED_TRANSITION",
)
REPORT_STATUSES_FIN = ("DRAFT", "FINAL")

THRESHOLD_DIRECTIONS = ("ABOVE", "BELOW")


# ── Section 1: Financial ESG KPI Framework ────────────────────────────────────


class FinancialESGKPIModel(BaseModel):
    __tablename__ = "financial_esg_kpis"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="QUARTERLY")
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 2: Financial KPI Measurements ─────────────────────────────────────


class FinancialKPIMeasurementModel(BaseModel):
    __tablename__ = "financial_kpi_measurements"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kpi_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("financial_esg_kpis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "2024-Q1", "2024"
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 3: Cost of Carbon Framework ──────────────────────────────────────


class CarbonCostModelRecord(BaseModel):
    __tablename__ = "carbon_cost_models"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    internal_carbon_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    regulatory_carbon_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avoided_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avoided_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # total_carbon_cost = total_emissions × internal_carbon_price (deterministic)
    total_carbon_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # regulatory_exposure = total_emissions × regulatory_carbon_price
    regulatory_exposure: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    formula: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    inventory_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 4: Cost of Risk Engine ───────────────────────────────────────────


class CostOfRiskAssessmentModel(BaseModel):
    __tablename__ = "cost_of_risk_assessments"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Inputs (0–100 scores)
    supplier_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    climate_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    compliance_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    operational_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    exposure_base: Mapped[float] = mapped_column(Float, nullable=False)
    # Outputs (deterministic)
    composite_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_financial_exposure: Mapped[float] = mapped_column(Float, nullable=False)
    expected_loss: Mapped[float] = mapped_column(Float, nullable=False)
    risk_adjusted_exposure: Mapped[float] = mapped_column(Float, nullable=False)
    methodology: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 5: ESG Value Creation Model ──────────────────────────────────────


class ValueCreationInitiativeModel(BaseModel):
    __tablename__ = "value_creation_initiatives"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    investment_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    realized_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    roi_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    payback_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initiative_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)


# ── Section 6: Sustainable Finance Framework ──────────────────────────────────


class SustainableFinanceInstrumentModel(BaseModel):
    __tablename__ = "sustainable_finance_instruments"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    maturity_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    covenant_status: Mapped[str] = mapped_column(String(20), nullable=False, default="MONITORING")
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kpi_linkage: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ── Section 7: Taxonomy Alignment Engine ──────────────────────────────────────


class TaxonomyAlignmentAssessmentModel(BaseModel):
    __tablename__ = "taxonomy_alignment_assessments"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    taxonomy_framework: Mapped[str] = mapped_column(
        String(50), nullable=False, default="EU_TAXONOMY"
    )
    assessment_year: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_activities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    aligned_activities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    eligible_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    aligned_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    total_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_capex: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_opex: Mapped[float | None] = mapped_column(Float, nullable=True)


# ── Section 8: Green Revenue Tracking ────────────────────────────────────────


class GreenRevenueRecordModel(BaseModel):
    __tablename__ = "green_revenue_records"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    revenue_stream: Mapped[str] = mapped_column(String(255), nullable=False)
    taxonomy_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    alignment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ELIGIBLE")
    total_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    green_revenue_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 9: Green CapEx Tracking ──────────────────────────────────────────


class GreenCapexRecordModel(BaseModel):
    __tablename__ = "green_capex_records"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    taxonomy_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    alignment_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 10: Green OpEx Tracking ──────────────────────────────────────────


class GreenOpexRecordModel(BaseModel):
    __tablename__ = "green_opex_records"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    alignment_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 11: Transition Finance Planning ───────────────────────────────────


class TransitionPlanModel(BaseModel):
    __tablename__ = "transition_plans"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    baseline_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    target_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    financing_needs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    funding_sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    plan_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")


class TransitionPlanMilestoneModel(BaseModel):
    __tablename__ = "transition_plan_milestones"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transition_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    milestone_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")


# ── Section 12: Sustainability Linked KPI Management ─────────────────────────


class FinanceLinkedKPIModel(BaseModel):
    __tablename__ = "finance_linked_kpis"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sustainable_finance_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    esg_target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kpi_name: Mapped[str] = mapped_column(String(255), nullable=False)
    kpi_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_direction: Mapped[str] = mapped_column(String(10), nullable=False, default="BELOW")
    covenant_status: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLIANT")
    last_assessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)


# ── Section 13: Capital Markets Readiness ────────────────────────────────────


class CapitalMarketsAssessmentModel(BaseModel):
    __tablename__ = "capital_markets_assessments"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    disclosure_readiness: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NOT_READY"
    )
    assurance_readiness: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NOT_READY"
    )
    taxonomy_readiness: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_READY")
    kpi_readiness: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_READY")
    overall_readiness: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_READY")
    assessment_notes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── Section 14: Investor Disclosure Package ───────────────────────────────────


class InvestorDisclosurePackageModel(BaseModel):
    __tablename__ = "investor_disclosure_packages"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    esg_kpi_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    taxonomy_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    climate_metrics_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assurance_status_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sustainability_targets_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ── Section 15: Climate Finance Analytics ────────────────────────────────────


class ClimateFinanceAnalysisModel(BaseModel):
    __tablename__ = "climate_finance_analyses"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    analysis_name: Mapped[str] = mapped_column(String(255), nullable=False)
    analysis_year: Mapped[int] = mapped_column(Integer, nullable=False)
    transition_investment: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    emissions_reduction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # cost_per_ton_reduced = transition_investment / emissions_reduction (deterministic, if > 0)
    cost_per_ton_reduced: Mapped[float | None] = mapped_column(Float, nullable=True)
    roi_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    methodology: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 16: Sustainability Valuation Analytics ────────────────────────────


class SustainabilityValuationModelRecord(BaseModel):
    __tablename__ = "sustainability_valuation_models"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    valuation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    valuation_year: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_reduction_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbon_reduction_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    operational_efficiency_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # total = sum of above three (deterministic)
    total_sustainability_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    methodology: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 19: ESG + Financial Correlation Engine ────────────────────────────


class ESGFinancialCorrelationModel(BaseModel):
    __tablename__ = "esg_financial_correlations"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scorecard_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_period: Mapped[str] = mapped_column(String(20), nullable=False)
    esg_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_reduction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_reduction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    financial_performance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correlation_coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ── Section 22: Scenario & Sensitivity Analysis ───────────────────────────────


class FinancialScenarioAnalysisModel(BaseModel):
    __tablename__ = "financial_scenario_analyses"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)
    inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 23: Financial ESG Reporting ──────────────────────────────────────


class FinancialESGReportModel(BaseModel):
    __tablename__ = "financial_esg_reports"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_creation_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    carbon_economics_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    taxonomy_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    green_revenue_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sustainable_finance_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    readiness_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_status: Mapped[str] = mapped_column(String(10), nullable=False, default="DRAFT")
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
