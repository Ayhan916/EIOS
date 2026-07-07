"""M42 — Sustainability Performance Management Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── ESG Objectives ─────────────────────────────────────────────────────────────


class ESGObjectiveCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    category: str = Field(..., pattern="^(ENVIRONMENTAL|SOCIAL|GOVERNANCE)$")
    description: str | None = None
    owner_user_id: str | None = None
    start_date: datetime | None = None
    target_date: datetime | None = None
    program_id: str | None = None


class ESGObjectiveStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(DRAFT|ACTIVE|COMPLETED|CANCELLED)$")


class ESGObjectiveResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    category: str
    description: str | None
    owner_user_id: str | None
    start_date: datetime | None
    target_date: datetime | None
    objective_status: str
    program_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── ESG Targets ───────────────────────────────────────────────────────────────


class ESGTargetCreate(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=255)
    baseline_value: float
    target_value: float
    target_unit: str | None = None
    measurement_frequency: str = Field("QUARTERLY", pattern="^(MONTHLY|QUARTERLY|ANNUAL)$")
    target_date: datetime | None = None
    notes: str | None = None


class ESGTargetValueUpdate(BaseModel):
    current_value: float


class ESGTargetResponse(BaseModel):
    id: str
    organization_id: str
    objective_id: str
    metric_name: str
    baseline_value: float
    target_value: float
    target_unit: str | None
    current_value: float | None
    progress_percent: float = 0.0
    measurement_frequency: str
    target_date: datetime | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── KPIs ──────────────────────────────────────────────────────────────────────


class ESGKPICreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(
        ...,
        pattern="^(EMISSIONS|SUPPLIER_COMPLIANCE|AUDIT_COMPLETION|TRAINING_COMPLETION|DIVERSITY|INCIDENT_RATE|CUSTOM)$",
    )
    description: str | None = None
    formula: str | None = None
    unit: str | None = None
    frequency: str = Field("QUARTERLY", pattern="^(MONTHLY|QUARTERLY|ANNUAL)$")
    target_value: float | None = None
    alert_threshold: float | None = None


class ESGKPIResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    category: str
    description: str | None
    formula: str | None
    unit: str | None
    frequency: str
    is_active: bool
    target_value: float | None
    alert_threshold: float | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── KPI Measurements ──────────────────────────────────────────────────────────


class KPIMeasurementCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    measured_value: float
    source: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    notes: str | None = None


class KPIMeasurementResponse(BaseModel):
    id: str
    kpi_id: str
    organization_id: str
    period_start: datetime
    period_end: datetime
    measured_value: float
    source: str | None
    confidence: float | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── KPI Alerts ────────────────────────────────────────────────────────────────


class KPIAlertCreate(BaseModel):
    alert_type: str = Field(..., pattern="^(THRESHOLD_BREACH|MISSED_TARGET|DETERIORATING_TREND)$")
    triggered_value: float
    threshold_value: float | None = None
    message: str | None = None


class KPIAlertResponse(BaseModel):
    id: str
    organization_id: str
    kpi_id: str
    alert_type: str
    threshold_value: float | None
    triggered_value: float
    message: str
    is_resolved: bool
    resolved_at: datetime | None
    resolved_by: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Scorecards ────────────────────────────────────────────────────────────────


class ScorecardComputeRequest(BaseModel):
    period_start: datetime
    period_end: datetime


class SustainabilityScorecardResponse(BaseModel):
    id: str
    organization_id: str
    period_start: datetime
    period_end: datetime
    environmental_score: float
    social_score: float
    governance_score: float
    overall_score: float
    calculation_method: str | None
    score_data: dict[str, Any]
    generated_by: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Emission Sources ──────────────────────────────────────────────────────────


class EmissionSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scope: str = Field(..., pattern="^(SCOPE1|SCOPE2|SCOPE3)$")
    activity_data: float = Field(..., ge=0)
    emission_factor: float = Field(..., ge=0)
    period_start: datetime
    period_end: datetime
    reporting_year: int = Field(..., ge=1990, le=2100)
    category: str | None = None
    activity_unit: str | None = None
    emission_factor_unit: str | None = None
    source_reference: str | None = None
    inventory_id: str | None = None


class EmissionSourceResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    scope: str
    category: str | None
    activity_data: float
    activity_unit: str | None
    emission_factor: float
    emission_factor_unit: str | None
    calculated_emissions: float
    period_start: datetime
    period_end: datetime
    reporting_year: int
    source_reference: str | None
    inventory_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Carbon Inventory ──────────────────────────────────────────────────────────


class CarbonInventoryCreate(BaseModel):
    reporting_year: int = Field(..., ge=1990, le=2100)
    period_start: datetime
    period_end: datetime


class CarbonInventoryResponse(BaseModel):
    id: str
    organization_id: str
    reporting_year: int
    period_start: datetime
    period_end: datetime
    total_emissions: float
    scope1_emissions: float
    scope2_emissions: float
    scope3_emissions: float
    unit: str
    inventory_status: str
    last_calculated_at: datetime | None
    recalculation_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Decarbonization Initiatives ───────────────────────────────────────────────


class DecarbonizationInitiativeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    initiative_type: str = Field(
        ...,
        pattern="^(RENEWABLE_ENERGY|LOGISTICS_OPTIMIZATION|SUPPLIER_TRANSITION|FACILITY_UPGRADE|OTHER)$",
    )
    expected_reduction: float = Field(..., ge=0)
    description: str | None = None
    roadmap_id: str | None = None
    cost_estimate: float | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    notes: str | None = None


class InitiativeProgressUpdate(BaseModel):
    actual_reduction: float = Field(..., ge=0)
    status: str = Field(..., pattern="^(PLANNED|IN_PROGRESS|COMPLETED|CANCELLED)$")


class DecarbonizationInitiativeResponse(BaseModel):
    id: str
    organization_id: str
    roadmap_id: str | None
    name: str
    initiative_type: str
    description: str | None
    expected_reduction: float
    actual_reduction: float | None
    cost_estimate: float | None
    initiative_status: str
    start_date: datetime | None
    end_date: datetime | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Net Zero Roadmap ──────────────────────────────────────────────────────────


class NetZeroRoadmapCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    baseline_year: int = Field(..., ge=1990, le=2100)
    target_year: int = Field(..., ge=1990, le=2100)
    baseline_emissions: float = Field(..., ge=0)
    target_reduction_percent: float = Field(..., ge=0, le=100)
    description: str | None = None


class NetZeroRoadmapResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    baseline_year: int
    target_year: int
    baseline_emissions: float
    target_reduction_percent: float
    target_emissions: float
    roadmap_status: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class MilestoneCreate(BaseModel):
    milestone_year: int = Field(..., ge=1990, le=2100)
    target_emissions: float = Field(..., ge=0)
    notes: str | None = None


class MilestoneUpdate(BaseModel):
    actual_emissions: float = Field(..., ge=0)
    status: str = Field(..., pattern="^(PENDING|ACHIEVED|MISSED)$")


class NetZeroMilestoneResponse(BaseModel):
    id: str
    roadmap_id: str
    milestone_year: int
    target_emissions: float
    actual_emissions: float | None
    milestone_status: str
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Science Based Targets ─────────────────────────────────────────────────────


class ScienceBasedTargetCreate(BaseModel):
    scope: str = Field(..., pattern="^(SCOPE1_2|SCOPE3|ALL)$")
    target_type: str = Field(..., pattern="^(ABSOLUTE|INTENSITY)$")
    baseline_year: int = Field(..., ge=1990, le=2100)
    baseline_emissions: float = Field(..., ge=0)
    target_reduction_percent: float = Field(..., ge=0, le=100)
    target_year: int = Field(..., ge=1990, le=2100)
    sbt_framework: str = Field("SBTi", pattern="^(SBTi|OTHER)$")
    description: str | None = None
    commitment_date: datetime | None = None


class SBTStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(DRAFT|SUBMITTED|APPROVED|ACTIVE|ACHIEVED)$")
    approval_date: datetime | None = None


class ScienceBasedTargetResponse(BaseModel):
    id: str
    organization_id: str
    scope: str
    target_type: str
    baseline_year: int
    baseline_emissions: float
    target_reduction_percent: float
    target_year: int
    sbt_status: str
    sbt_framework: str
    commitment_date: datetime | None
    approval_date: datetime | None
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Climate Risk ──────────────────────────────────────────────────────────────


class ClimateRiskAssessmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    assessment_year: int = Field(..., ge=1990, le=2100)
    transition_risk_score: float = Field(..., ge=0, le=100)
    physical_risk_score: float = Field(..., ge=0, le=100)
    regulatory_risk_score: float = Field(..., ge=0, le=100)
    scenario: str = Field("2C", pattern="^(1_5C|2C|BAU)$")
    transition_risk_details: dict[str, Any] = Field(default_factory=dict)
    physical_risk_details: dict[str, Any] = Field(default_factory=dict)
    regulatory_risk_details: dict[str, Any] = Field(default_factory=dict)
    network_entity_id: str | None = None
    regulation_id: str | None = None
    notes: str | None = None


class ClimateRiskAssessmentResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    assessment_year: int
    scenario: str
    transition_risk_score: float
    physical_risk_score: float
    regulatory_risk_score: float
    overall_risk_score: float
    transition_risk_details: dict[str, Any]
    physical_risk_details: dict[str, Any]
    regulatory_risk_details: dict[str, Any]
    network_entity_id: str | None
    regulation_id: str | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Assurance ─────────────────────────────────────────────────────────────────


class AssuranceRecordCreate(BaseModel):
    report_type: str = Field(..., pattern="^(EMISSIONS|KPI|FULL_ESG)$")
    reviewed_period_start: datetime
    reviewed_period_end: datetime
    reviewer_user_id: str
    assurance_level: str = Field(..., pattern="^(REASONABLE|LIMITED|NONE)$")
    findings: list[dict[str, Any]] = Field(default_factory=list)
    methodology: str | None = None


class AssuranceRecordResponse(BaseModel):
    id: str
    organization_id: str
    report_type: str
    reviewed_period_start: datetime
    reviewed_period_end: datetime
    reviewer_user_id: str
    assurance_level: str
    findings: list
    assurance_status: str
    methodology: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── CSRD Mapping ──────────────────────────────────────────────────────────────


class CSRDMappingCreate(BaseModel):
    esrs_standard: str = Field(..., pattern="^(E1|E2|E3|E4|E5|S1|S2|S3|S4|G1)$")
    kpi_id: str | None = None
    objective_id: str | None = None
    target_id: str | None = None
    disclosure_requirement: str | None = None
    data_point_reference: str | None = None
    compliance_status: str = Field(
        "NOT_ASSESSED",
        pattern="^(COMPLIANT|PARTIAL|NOT_ASSESSED|NOT_APPLICABLE)$",
    )
    notes: str | None = None


class CSRDMappingResponse(BaseModel):
    id: str
    organization_id: str
    esrs_standard: str
    kpi_id: str | None
    objective_id: str | None
    target_id: str | None
    disclosure_requirement: str | None
    data_point_reference: str | None
    mapping_compliance_status: str
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── ISSB Mapping ──────────────────────────────────────────────────────────────


class ISSBMappingCreate(BaseModel):
    issb_standard: str = Field(..., pattern="^(S1|S2)$")
    kpi_id: str | None = None
    objective_id: str | None = None
    disclosure_topic: str | None = None
    metric_reference: str | None = None
    compliance_status: str = Field(
        "NOT_ASSESSED",
        pattern="^(COMPLIANT|PARTIAL|NOT_ASSESSED|NOT_APPLICABLE)$",
    )
    notes: str | None = None


class ISSBMappingResponse(BaseModel):
    id: str
    organization_id: str
    issb_standard: str
    kpi_id: str | None
    objective_id: str | None
    disclosure_topic: str | None
    metric_reference: str | None
    mapping_compliance_status: str
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Forecasts ─────────────────────────────────────────────────────────────────


class ForecastCreate(BaseModel):
    forecast_type: str = Field(..., pattern="^(EMISSIONS|KPI_ATTAINMENT|TARGET_ACHIEVEMENT)$")
    method: str = Field(..., pattern="^(LINEAR_TREND|MOVING_AVERAGE)$")
    period_start: datetime
    period_end: datetime
    historical_data: list[float] = Field(..., min_length=1)
    forecast_horizon_months: int = Field(12, ge=1, le=120)
    kpi_id: str | None = None
    assumptions: dict[str, Any] = Field(default_factory=dict)


class ForecastResponse(BaseModel):
    id: str
    organization_id: str
    kpi_id: str | None
    forecast_type: str
    method: str
    period_start: datetime
    period_end: datetime
    forecast_horizon_months: int
    historical_data: list
    forecast_data: list
    confidence_interval: dict | None
    assumptions: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Scenarios ─────────────────────────────────────────────────────────────────


class ScenarioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scenario_type: str = Field(
        ...,
        pattern="^(SUPPLIER_IMPROVEMENT|RENEWABLE_TRANSITION|EMISSIONS_INTENSITY_REDUCTION|CUSTOM)$",
    )
    description: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    assumptions: dict[str, Any] = Field(default_factory=dict)


class ScenarioResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    scenario_type: str
    description: str | None
    inputs: dict[str, Any]
    assumptions: dict[str, Any]
    outputs: dict[str, Any]
    scenario_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Sustainability Reports ─────────────────────────────────────────────────────


class SustainabilityReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    period_start: datetime
    period_end: datetime
    report_type: str = Field(
        "FULL", pattern="^(KPI_SUMMARY|EMISSIONS_SUMMARY|TARGET_PROGRESS|FULL)$"
    )


class SustainabilityReportResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    period_start: datetime
    period_end: datetime
    report_type: str
    kpi_summary: dict[str, Any]
    emissions_summary: dict[str, Any]
    target_progress: dict[str, Any]
    objective_status: dict[str, Any]
    overall_status: str
    generated_by: str | None
    is_final: bool
    finalized_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────


class SustainabilityDashboard(BaseModel):
    organization_id: str
    total_objectives: int
    active_objectives: int
    completed_objectives: int
    total_kpis: int
    active_kpis: int
    total_emissions_tco2e: float | None
    latest_inventory_year: int | None
    open_alerts: int
    active_initiatives: int
    latest_overall_score: float | None
    active_sbts: int


# ── Rollups ───────────────────────────────────────────────────────────────────


class EmissionsRollupSchema(BaseModel):
    total_emissions: float
    scope1: float
    scope2: float
    scope3: float
    inventories_count: int


class ObjectivesRollupSchema(BaseModel):
    total: int
    active: int
    completed: int
    completion_percent: float


class TargetsRollupSchema(BaseModel):
    total: int
    with_measurements: int
    attainment_percent: float


class KPIsRollupSchema(BaseModel):
    total: int
    active: int


class ScoreRollupSchema(BaseModel):
    avg_overall_score: float | None
    avg_environmental_score: float | None
    avg_social_score: float | None
    avg_governance_score: float | None
    scorecard_count: int


class ClimateRiskRollupSchema(BaseModel):
    avg_overall_risk: float | None
    avg_transition_risk: float | None
    avg_physical_risk: float | None
    avg_regulatory_risk: float | None
    assessment_count: int


class RollupSummaryResponse(BaseModel):
    entity_type: str
    entity_id: str
    organization_ids: list[str]
    emissions: EmissionsRollupSchema
    objectives: ObjectivesRollupSchema
    targets: TargetsRollupSchema
    kpis: KPIsRollupSchema
    scores: ScoreRollupSchema
    climate_risks: ClimateRiskRollupSchema
    computed_at: str


# ── Executive Sustainability Summary ──────────────────────────────────────────


class SustainabilityExecutiveSummary(BaseModel):
    status: str = "ok"
    degraded_reason: str | None = None
    total_emissions: float | None = None
    emissions_change_percent: float | None = None
    objective_completion_percent: float | None = None
    target_attainment_percent: float | None = None
    sustainability_score: float | None = None
    climate_risk_score: float | None = None
    active_net_zero_roadmaps: int = 0
    active_science_based_targets: int = 0
    open_kpi_alerts: int = 0
