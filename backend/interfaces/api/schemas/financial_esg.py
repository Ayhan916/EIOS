"""M43 — Financial ESG Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ── KPI Framework ─────────────────────────────────────────────────────────────


class FinancialKPICreate(BaseModel):
    name: str
    category: str
    formula: str | None = None
    unit: str | None = None
    frequency: str = "QUARTERLY"
    owner_user_id: str | None = None
    description: str | None = None


class FinancialKPIResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    category: str
    formula: str | None = None
    unit: str | None = None
    frequency: str
    owner_user_id: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KPIMeasurementCreate(BaseModel):
    kpi_id: str
    period: str
    value: float
    source: str | None = None
    confidence: float | None = None
    notes: str | None = None


class KPIMeasurementResponse(BaseModel):
    id: str
    organization_id: str
    kpi_id: str
    period: str
    value: float
    source: str | None = None
    confidence: float | None = None
    calculated_at: datetime
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Carbon Cost Model ─────────────────────────────────────────────────────────


class CarbonCostModelCreate(BaseModel):
    name: str
    assessment_year: int
    total_emissions: float
    internal_carbon_price: float
    regulatory_carbon_price: float
    avoided_emissions: float = 0.0
    currency: str = "USD"
    inventory_id: str | None = None
    notes: str | None = None


class CarbonCostModelResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    assessment_year: int
    total_emissions: float
    internal_carbon_price: float
    regulatory_carbon_price: float
    avoided_emissions: float
    avoided_cost: float
    total_carbon_cost: float
    regulatory_exposure: float
    formula: dict | None = None
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Cost of Risk ──────────────────────────────────────────────────────────────


class CostOfRiskCreate(BaseModel):
    name: str
    supplier_risk_score: float = Field(..., ge=0, le=100)
    climate_risk_score: float = Field(..., ge=0, le=100)
    compliance_risk_score: float = Field(..., ge=0, le=100)
    operational_risk_score: float = Field(..., ge=0, le=100)
    exposure_base: float
    currency: str = "USD"
    notes: str | None = None


class CostOfRiskResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    assessment_date: datetime
    supplier_risk_score: float
    climate_risk_score: float
    compliance_risk_score: float
    operational_risk_score: float
    exposure_base: float
    composite_risk_score: float
    estimated_financial_exposure: float
    expected_loss: float
    risk_adjusted_exposure: float
    methodology: dict | None = None
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Value Creation ────────────────────────────────────────────────────────────


class ValueInitiativeCreate(BaseModel):
    name: str
    investment_amount: float
    expected_value: float
    description: str | None = None
    realized_value: float = 0.0
    payback_period_months: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    currency: str = "USD"
    category: str | None = None


class ValueInitiativeUpdate(BaseModel):
    realized_value: float
    new_status: str | None = None


class ValueInitiativeResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    investment_amount: float
    expected_value: float
    realized_value: float
    roi_percent: float | None = None
    payback_period_months: int | None = None
    initiative_status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    currency: str
    category: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Sustainable Finance ───────────────────────────────────────────────────────


class FinanceInstrumentCreate(BaseModel):
    name: str
    instrument_type: str
    amount: float
    currency: str = "USD"
    maturity_date: datetime | None = None
    issuer: str | None = None
    counterparty: str | None = None
    description: str | None = None
    kpi_linkage: dict | None = None


class FinanceInstrumentResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    instrument_type: str
    amount: float
    currency: str
    maturity_date: datetime | None = None
    covenant_status: str
    issuer: str | None = None
    counterparty: str | None = None
    description: str | None = None
    kpi_linkage: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LinkedKPICreate(BaseModel):
    instrument_id: str
    kpi_name: str
    esg_target_id: str | None = None
    kpi_description: str | None = None
    threshold_value: float | None = None
    threshold_direction: str = "BELOW"
    current_value: float | None = None


class LinkedKPIResponse(BaseModel):
    id: str
    organization_id: str
    instrument_id: str
    esg_target_id: str | None = None
    kpi_name: str
    kpi_description: str | None = None
    threshold_value: float | None = None
    threshold_direction: str
    covenant_status: str
    last_assessed_at: datetime | None = None
    current_value: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CovenantMonitorRequest(BaseModel):
    current_value: float


# ── Transition Plan ───────────────────────────────────────────────────────────


class TransitionPlanCreate(BaseModel):
    name: str
    description: str | None = None
    baseline_state: dict | None = None
    target_state: dict | None = None
    financing_needs: float = 0.0
    funding_sources: dict | None = None
    start_date: datetime | None = None
    target_date: datetime | None = None
    currency: str = "USD"


class TransitionPlanResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    baseline_state: dict | None = None
    target_state: dict | None = None
    financing_needs: float
    funding_sources: dict | None = None
    plan_status: str
    start_date: datetime | None = None
    target_date: datetime | None = None
    currency: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MilestoneCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime | None = None


class MilestoneResponse(BaseModel):
    id: str
    plan_id: str
    organization_id: str
    title: str
    description: str | None = None
    due_date: datetime | None = None
    milestone_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Taxonomy ──────────────────────────────────────────────────────────────────


class TaxonomyAssessmentCreate(BaseModel):
    assessment_year: int
    taxonomy_framework: str = "EU_TAXONOMY"
    eligible_activities: dict | None = None
    aligned_activities: dict | None = None
    total_revenue: float | None = None
    total_capex: float | None = None
    total_opex: float | None = None
    justification: str | None = None


class TaxonomyStatusUpdate(BaseModel):
    new_status: str


class TaxonomyAssessmentResponse(BaseModel):
    id: str
    organization_id: str
    taxonomy_framework: str
    assessment_year: int
    eligible_activities: dict | None = None
    aligned_activities: dict | None = None
    eligible_percent: float
    aligned_percent: float
    justification: str | None = None
    assessment_status: str
    total_revenue: float | None = None
    total_capex: float | None = None
    total_opex: float | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Green Revenue ─────────────────────────────────────────────────────────────


class GreenRevenueCreate(BaseModel):
    revenue_stream: str
    amount: float
    total_revenue: float
    period: str
    taxonomy_category: str | None = None
    alignment_status: str = "ELIGIBLE"
    currency: str = "USD"
    notes: str | None = None


class GreenRevenueResponse(BaseModel):
    id: str
    organization_id: str
    revenue_stream: str
    taxonomy_category: str | None = None
    amount: float
    currency: str
    period: str
    alignment_status: str
    total_revenue: float
    green_revenue_percent: float
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class GreenCapexCreate(BaseModel):
    project_name: str
    amount: float
    alignment_percent: float = Field(..., ge=0, le=100)
    period: str
    taxonomy_category: str | None = None
    currency: str = "USD"
    notes: str | None = None


class GreenCapexResponse(BaseModel):
    id: str
    organization_id: str
    project_name: str
    taxonomy_category: str | None = None
    amount: float
    currency: str
    alignment_percent: float
    period: str
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class GreenOpexCreate(BaseModel):
    description: str
    amount: float
    alignment_percent: float = Field(..., ge=0, le=100)
    period: str
    category: str | None = None
    currency: str = "USD"
    notes: str | None = None


class GreenOpexResponse(BaseModel):
    id: str
    organization_id: str
    description: str
    category: str | None = None
    amount: float
    currency: str
    alignment_percent: float
    period: str
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Capital Markets Readiness ─────────────────────────────────────────────────


class CapitalMarketsAssessmentCreate(BaseModel):
    disclosure_readiness: str = "NOT_READY"
    assurance_readiness: str = "NOT_READY"
    taxonomy_readiness: str = "NOT_READY"
    kpi_readiness: str = "NOT_READY"
    assessment_notes: dict | None = None


class CapitalMarketsAssessmentResponse(BaseModel):
    id: str
    organization_id: str
    disclosure_readiness: str
    assurance_readiness: str
    taxonomy_readiness: str
    kpi_readiness: str
    overall_readiness: str
    assessment_notes: dict | None = None
    assessed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ── Investor Disclosure Package ───────────────────────────────────────────────


class DisclosurePackageCreate(BaseModel):
    title: str
    period_start: datetime
    period_end: datetime
    description: str | None = None
    esg_kpi_snapshot: dict | None = None
    taxonomy_snapshot: dict | None = None
    climate_metrics_snapshot: dict | None = None
    assurance_status_snapshot: dict | None = None
    sustainability_targets_snapshot: dict | None = None


class DisclosurePackageResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str | None = None
    period_start: datetime
    period_end: datetime
    esg_kpi_snapshot: dict | None = None
    taxonomy_snapshot: dict | None = None
    climate_metrics_snapshot: dict | None = None
    assurance_status_snapshot: dict | None = None
    sustainability_targets_snapshot: dict | None = None
    is_final: bool
    finalized_at: datetime | None = None
    finalized_by: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Climate Finance Analytics ─────────────────────────────────────────────────


class ClimateFinanceCreate(BaseModel):
    analysis_name: str
    analysis_year: int
    transition_investment: float
    emissions_reduction: float
    carbon_price_proxy: float = 50.0
    currency: str = "USD"
    notes: str | None = None


class ClimateFinanceResponse(BaseModel):
    id: str
    organization_id: str
    analysis_name: str
    analysis_year: int
    transition_investment: float
    emissions_reduction: float
    cost_per_ton_reduced: float | None = None
    roi_percent: float | None = None
    methodology: dict | None = None
    currency: str
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Sustainability Valuation ──────────────────────────────────────────────────


class ValuationCreate(BaseModel):
    valuation_name: str
    valuation_year: int
    risk_reduction_value: float
    carbon_reduction_value: float
    operational_efficiency_value: float
    currency: str = "USD"
    notes: str | None = None


class ValuationResponse(BaseModel):
    id: str
    organization_id: str
    valuation_name: str
    valuation_year: int
    risk_reduction_value: float
    carbon_reduction_value: float
    operational_efficiency_value: float
    total_sustainability_value: float
    methodology: dict | None = None
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Scenario Analysis ─────────────────────────────────────────────────────────


class ScenarioCreate(BaseModel):
    scenario_name: str
    scenario_type: str
    inputs: dict
    assumptions: dict
    notes: str | None = None


class ScenarioResponse(BaseModel):
    id: str
    organization_id: str
    scenario_name: str
    scenario_type: str
    inputs: dict | None = None
    assumptions: dict | None = None
    outputs: dict | None = None
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── ESG Financial Correlation ─────────────────────────────────────────────────


class CorrelationCreate(BaseModel):
    esg_score: float
    risk_reduction: float
    cost_reduction: float
    financial_performance: float
    correlation_period: str
    scorecard_id: str | None = None
    methodology: str | None = None
    assumptions: dict | None = None


class CorrelationResponse(BaseModel):
    id: str
    organization_id: str
    scorecard_id: str | None = None
    correlation_period: str
    esg_score: float
    risk_reduction: float
    cost_reduction: float
    financial_performance: float
    correlation_coefficient: float | None = None
    methodology: str | None = None
    assumptions: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Financial ESG Report ──────────────────────────────────────────────────────


class FinancialReportCreate(BaseModel):
    title: str
    report_period_start: datetime
    report_period_end: datetime


class FinancialReportResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    report_period_start: datetime
    report_period_end: datetime
    value_creation_snapshot: dict | None = None
    carbon_economics_snapshot: dict | None = None
    taxonomy_snapshot: dict | None = None
    green_revenue_snapshot: dict | None = None
    sustainable_finance_snapshot: dict | None = None
    readiness_snapshot: dict | None = None
    overall_status: str
    is_final: bool
    finalized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Enterprise Rollup ─────────────────────────────────────────────────────────


class CarbonEconomicsRollupSchema(BaseModel):
    total_carbon_cost: float
    total_regulatory_exposure: float
    total_avoided_cost: float
    model_count: int


class GreenRevenueRollupSchema(BaseModel):
    total_green_amount: float
    avg_green_percent: float
    record_count: int


class TaxonomyRollupSchema(BaseModel):
    avg_aligned_percent: float | None = None
    avg_eligible_percent: float | None = None
    assessment_count: int


class FinanceRollupSchema(BaseModel):
    total_exposure: float
    instrument_count: int
    breached_count: int


class ValueCreationRollupSchema(BaseModel):
    total_investment: float
    total_realized_value: float
    initiative_count: int
    avg_roi_percent: float | None = None


class FinancialRollupResponse(BaseModel):
    entity_type: str
    entity_id: str
    organization_ids: list[str]
    computed_at: str
    carbon_economics: CarbonEconomicsRollupSchema
    green_revenue: GreenRevenueRollupSchema
    taxonomy: TaxonomyRollupSchema
    finance: FinanceRollupSchema
    value_creation: ValueCreationRollupSchema


# ── Executive Dashboard ───────────────────────────────────────────────────────


class FinancialSustainabilitySummary(BaseModel):
    status: str = "ok"
    degraded_reason: str | None = None
    green_revenue_percent: float | None = None
    taxonomy_alignment_percent: float | None = None
    carbon_cost_exposure: float | None = None
    sustainability_roi: float | None = None
    sustainable_finance_exposure: float | None = None
    capital_markets_readiness: str | None = None
