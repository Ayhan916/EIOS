from __future__ import annotations

from pydantic import BaseModel, Field

from interfaces.api.schemas.sustainability import SustainabilityExecutiveSummary  # noqa: F401 re-exported


# ── Dashboard ─────────────────────────────────────────────────────────────────


class PortfolioSummary(BaseModel):
    total_suppliers: int
    scored_suppliers: int
    critical_risk_suppliers: int
    high_risk_suppliers: int
    moderate_risk_suppliers: int
    low_risk_suppliers: int
    improving_suppliers: int
    deteriorating_suppliers: int
    avg_esg_score: float | None
    avg_risk_score: float | None
    risk_distribution: dict[str, int]


class ActionSummary(BaseModel):
    open_actions: int
    overdue_actions: int
    total_actions: int
    resolution_rate: float | None


class GovernanceSummary(BaseModel):
    assessments_awaiting_review: int
    assessments_approved: int
    critical_findings_total: int


class ESGOperatingSummary(BaseModel):
    """M39 ESG Operating System summary surfaced on the executive dashboard."""
    status: str = "ok"
    degraded_reason: str | None = None
    objectives_at_risk: int = 0
    initiatives_at_risk: int = 0
    strategic_risks_critical: int = 0
    strategic_risks_total: int = 0
    overdue_esg_actions: int = 0
    objectives_by_status: dict[str, int] = Field(default_factory=dict)
    initiatives_by_status: dict[str, int] = Field(default_factory=dict)
    compliance_readiness: dict[str, float] = Field(default_factory=dict)
    accountability_coverage: int = 0
    controls_failing: int = 0


class ExecutiveDashboard(BaseModel):
    portfolio_summary: PortfolioSummary
    action_summary: ActionSummary
    governance_summary: GovernanceSummary
    esg_summary: ESGOperatingSummary | None = None
    sustainability_summary: SustainabilityExecutiveSummary | None = None


# ── KPI Trends ────────────────────────────────────────────────────────────────


class MonthlyDataPoint(BaseModel):
    month: str
    avg_esg_score: float | None
    avg_risk_score: float | None
    supplier_count: int
    high_risk_count: int
    critical_risk_count: int
    risk_distribution: dict[str, int]


class KPITrendResponse(BaseModel):
    period_days: int
    data_points: list[MonthlyDataPoint]
    esg_delta: float | None
    risk_delta: float | None


# ── Risk Register ─────────────────────────────────────────────────────────────


class RiskRegisterEntry(BaseModel):
    rank: int
    supplier_id: str
    supplier_name: str
    country: str
    industry: str
    supplier_tier: str
    risk_score: float
    risk_band: str
    esg_score: float
    trend: str
    trend_delta: float
    critical_findings: int
    overdue_actions: int


# ── Executive Heatmaps ────────────────────────────────────────────────────────


class HeatmapBucket(BaseModel):
    label: str
    supplier_count: int
    avg_risk_score: float
    critical_count: int
    high_count: int


class ExecutiveHeatmapResponse(BaseModel):
    view: str
    buckets: list[HeatmapBucket]


# ── Action Effectiveness ──────────────────────────────────────────────────────


class ActionEffectivenessResponse(BaseModel):
    opened_this_period: int
    closed_this_period: int
    total_open: int
    total_overdue: int
    resolution_rate: float | None
    avg_resolution_days: float | None


# ── Governance Metrics ────────────────────────────────────────────────────────


class GovernanceMetricsResponse(BaseModel):
    total_review_decisions: int
    approved: int
    rejected: int
    changes_requested: int
    approval_rate: float | None
    rejection_rate: float | None
    changes_requested_rate: float | None
    avg_review_days: float | None


# ── Board Reports ─────────────────────────────────────────────────────────────


class BoardReportRequest(BaseModel):
    title: str = "Monthly Board Report"
    period_start: str = Field(..., description="ISO date YYYY-MM-DD")
    period_end: str = Field(..., description="ISO date YYYY-MM-DD")
    kpi_period_days: int = Field(default=30, ge=7, le=365)


class BoardReportSummary(BaseModel):
    id: str
    title: str
    report_version: str
    period_start: str
    period_end: str
    generated_at: str
    executive_summary: str


class BoardReportDetail(BaseModel):
    id: str
    title: str
    report_version: str
    period_start: str
    period_end: str
    generated_at: str
    executive_summary: str
    report_data: dict
    supplier_snapshot: dict


# ── Report Schedules ──────────────────────────────────────────────────────────


class ReportScheduleRequest(BaseModel):
    frequency: str = Field(default="monthly", pattern="^(monthly|quarterly)$")
    next_run_at: str = Field(..., description="ISO datetime for first run")
    report_config: dict = Field(default_factory=dict)


class ReportScheduleResponse(BaseModel):
    id: str
    frequency: str
    next_run_at: str
    last_run_at: str | None
    is_active: bool
    created_at: str
