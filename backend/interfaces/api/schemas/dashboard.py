from pydantic import BaseModel


class RecentAssessmentItem(BaseModel):
    id: str
    title: str
    status: str
    assessment_type: str | None = None
    quality_score: float | None = None
    finding_count: int
    risk_count: int
    created_at: str


class MonthlyCount(BaseModel):
    month: str  # "2026-01"
    count: int


class DashboardResponse(BaseModel):
    total_assessments: int
    avg_quality_score: float | None
    action_status_breakdown: dict[str, int]
    open_actions: int
    overdue_actions: int
    closed_actions_pct: float
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]
    high_risk_finding_count: int
    critical_finding_count: int
    recent_assessments: list[RecentAssessmentItem]
    assessments_over_time: list[MonthlyCount]
