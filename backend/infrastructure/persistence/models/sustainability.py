"""M42 — Sustainability Performance Management & Decarbonization Platform ORM Models.

19 new tables (149 → 168):
  sustainability_objectives, esg_targets, esg_kpis, kpi_measurements,
  sustainability_scorecards, emission_sources, carbon_inventories,
  decarbonization_initiatives, net_zero_roadmaps, net_zero_milestones,
  science_based_targets, climate_risk_assessments,
  sustainability_assurance_records, csrd_performance_mappings,
  issb_sustainability_mappings, kpi_alerts, performance_forecasts,
  scenario_analyses, sustainability_performance_reports
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel

# ── Enum constants ─────────────────────────────────────────────────────────────

ESG_CATEGORIES = ("ENVIRONMENTAL", "SOCIAL", "GOVERNANCE")
OBJECTIVE_STATUSES = ("DRAFT", "ACTIVE", "COMPLETED", "CANCELLED")
KPI_CATEGORIES = (
    "EMISSIONS", "SUPPLIER_COMPLIANCE", "AUDIT_COMPLETION",
    "TRAINING_COMPLETION", "DIVERSITY", "INCIDENT_RATE", "CUSTOM",
)
MEASUREMENT_FREQUENCIES = ("MONTHLY", "QUARTERLY", "ANNUAL")
EMISSION_SCOPES = ("SCOPE1", "SCOPE2", "SCOPE3")
INVENTORY_STATUSES = ("DRAFT", "FINALIZED")
INITIATIVE_TYPES = (
    "RENEWABLE_ENERGY", "LOGISTICS_OPTIMIZATION",
    "SUPPLIER_TRANSITION", "FACILITY_UPGRADE", "OTHER",
)
INITIATIVE_STATUSES = ("PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED")
ROADMAP_STATUSES = ("DRAFT", "ACTIVE", "COMPLETED")
MILESTONE_STATUSES = ("PENDING", "ACHIEVED", "MISSED")
SBT_SCOPES = ("SCOPE1_2", "SCOPE3", "ALL")
SBT_TYPES = ("ABSOLUTE", "INTENSITY")
SBT_STATUSES = ("DRAFT", "SUBMITTED", "APPROVED", "ACTIVE", "ACHIEVED")
SBT_FRAMEWORKS = ("SBTi", "OTHER")
CLIMATE_SCENARIOS = ("1_5C", "2C", "BAU")
ASSURANCE_LEVELS = ("REASONABLE", "LIMITED", "NONE")
ASSURANCE_REPORT_TYPES = ("EMISSIONS", "KPI", "FULL_ESG")
ASSURANCE_STATUSES = ("DRAFT", "COMPLETE")
CSRD_ESRS_STANDARDS = ("E1", "E2", "E3", "E4", "E5", "S1", "S2", "S3", "S4", "G1")
ISSB_STANDARDS = ("S1", "S2")
MAPPING_COMPLIANCE_STATUSES = ("COMPLIANT", "PARTIAL", "NOT_ASSESSED", "NOT_APPLICABLE")
ALERT_TYPES = ("THRESHOLD_BREACH", "MISSED_TARGET", "DETERIORATING_TREND")
FORECAST_TYPES = ("EMISSIONS", "KPI_ATTAINMENT", "TARGET_ACHIEVEMENT")
FORECAST_METHODS = ("LINEAR_TREND", "MOVING_AVERAGE")
SCENARIO_TYPES = (
    "SUPPLIER_IMPROVEMENT", "RENEWABLE_TRANSITION",
    "EMISSIONS_INTENSITY_REDUCTION", "CUSTOM",
)
SCENARIO_STATUSES = ("DRAFT", "COMPLETE")
REPORT_TYPES = ("KPI_SUMMARY", "EMISSIONS_SUMMARY", "TARGET_PROGRESS", "FULL")
REPORT_RAG_STATUSES = ("GREEN", "AMBER", "RED")


# ── ESG Objectives ─────────────────────────────────────────────────────────────

class SustainabilityObjectiveModel(BaseModel):
    __tablename__ = "sustainability_objectives"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    objective_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    program_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ESGTargetModel(BaseModel):
    __tablename__ = "esg_targets"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    objective_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sustainability_objectives.id"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="QUARTERLY")
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── KPI Management ─────────────────────────────────────────────────────────────

class ESGKPIModel(BaseModel):
    __tablename__ = "esg_kpis"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="CUSTOM")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="QUARTERLY")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)


class KPIMeasurementModel(BaseModel):
    __tablename__ = "kpi_measurements"

    kpi_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("esg_kpis.id"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    measured_value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Sustainability Scorecards ──────────────────────────────────────────────────

class SustainabilityScorecardModel(BaseModel):
    __tablename__ = "sustainability_scorecards"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    environmental_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    social_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    governance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calculation_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ── Carbon Accounting ─────────────────────────────────────────────────────────

class EmissionSourceModel(BaseModel):
    __tablename__ = "emission_sources"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activity_data: Mapped[float] = mapped_column(Float, nullable=False)
    activity_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emission_factor: Mapped[float] = mapped_column(Float, nullable=False)
    emission_factor_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    calculated_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inventory_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("carbon_inventories.id"), nullable=True
    )


class CarbonInventoryModel(BaseModel):
    __tablename__ = "carbon_inventories"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scope1_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scope2_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scope3_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="tCO2e")
    inventory_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    last_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recalculation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("organization_id", "reporting_year", name="uq_carbon_inventory_org_year"),
    )


# ── Decarbonization ───────────────────────────────────────────────────────────

class DecarbonizationInitiativeModel(BaseModel):
    __tablename__ = "decarbonization_initiatives"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    roadmap_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("net_zero_roadmaps.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    initiative_type: Mapped[str] = mapped_column(String(50), nullable=False, default="OTHER")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_reduction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_reduction: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    initiative_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class NetZeroRoadmapModel(BaseModel):
    __tablename__ = "net_zero_roadmaps"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    baseline_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_emissions: Mapped[float] = mapped_column(Float, nullable=False)
    target_reduction_percent: Mapped[float] = mapped_column(Float, nullable=False)
    target_emissions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    roadmap_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class NetZeroMilestoneModel(BaseModel):
    __tablename__ = "net_zero_milestones"

    roadmap_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("net_zero_roadmaps.id"), nullable=False
    )
    milestone_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_emissions: Mapped[float] = mapped_column(Float, nullable=False)
    actual_emissions: Mapped[float | None] = mapped_column(Float, nullable=True)
    milestone_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScienceBasedTargetModel(BaseModel):
    __tablename__ = "science_based_targets"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="SCOPE1_2")
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ABSOLUTE")
    baseline_year: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_emissions: Mapped[float] = mapped_column(Float, nullable=False)
    target_reduction_percent: Mapped[float] = mapped_column(Float, nullable=False)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    sbt_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    sbt_framework: Mapped[str] = mapped_column(String(20), nullable=False, default="SBTi")
    commitment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Climate Risk ──────────────────────────────────────────────────────────────

class ClimateRiskAssessmentModel(BaseModel):
    __tablename__ = "climate_risk_assessments"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    assessment_year: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario: Mapped[str] = mapped_column(String(20), nullable=False, default="2C")
    transition_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    physical_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    regulatory_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    transition_risk_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    physical_risk_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    regulatory_risk_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Cross-module integration (nullable — not required)
    network_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    regulation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Sustainability Assurance ──────────────────────────────────────────────────

class SustainabilityAssuranceRecordModel(BaseModel):
    __tablename__ = "sustainability_assurance_records"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, default="FULL_ESG")
    reviewed_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assurance_level: Mapped[str] = mapped_column(String(20), nullable=False, default="LIMITED")
    findings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    assurance_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Regulatory Mappings ───────────────────────────────────────────────────────

class CSRDPerformanceMappingModel(BaseModel):
    __tablename__ = "csrd_performance_mappings"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    kpi_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("esg_kpis.id"), nullable=True
    )
    objective_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("esg_objectives.id"), nullable=True
    )
    target_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("esg_targets.id"), nullable=True
    )
    esrs_standard: Mapped[str] = mapped_column(String(10), nullable=False)
    disclosure_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_point_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapping_compliance_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_ASSESSED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ISSBSustainabilityMappingModel(BaseModel):
    __tablename__ = "issb_sustainability_mappings"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    kpi_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("esg_kpis.id"), nullable=True
    )
    objective_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("esg_objectives.id"), nullable=True
    )
    issb_standard: Mapped[str] = mapped_column(String(10), nullable=False)
    disclosure_topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metric_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapping_compliance_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_ASSESSED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── KPI Alerts ────────────────────────────────────────────────────────────────

class KPIAlertModel(BaseModel):
    __tablename__ = "kpi_alerts"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    kpi_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("esg_kpis.id"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    triggered_value: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ── Forecasting & Scenarios ───────────────────────────────────────────────────

class PerformanceForecastModel(BaseModel):
    __tablename__ = "performance_forecasts"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    kpi_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("esg_kpis.id"), nullable=True
    )
    forecast_type: Mapped[str] = mapped_column(String(30), nullable=False, default="KPI_ATTAINMENT")
    method: Mapped[str] = mapped_column(String(30), nullable=False, default="LINEAR_TREND")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_horizon_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    historical_data: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    forecast_data: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence_interval: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assumptions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ScenarioAnalysisModel(BaseModel):
    __tablename__ = "scenario_analyses"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False, default="CUSTOM")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    assumptions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    outputs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scenario_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")


# ── Sustainability Reports ─────────────────────────────────────────────────────

class SustainabilityPerformanceReportModel(BaseModel):
    __tablename__ = "sustainability_performance_reports"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False, default="FULL")
    kpi_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    emissions_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    target_progress: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    objective_status: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    overall_status: Mapped[str] = mapped_column(String(10), nullable=False, default="AMBER")
    generated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
