from datetime import datetime

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
    review_status: str = "Draft"


class ReviewQueueItem(BaseModel):
    id: str
    title: str
    review_status: str
    assigned_reviewer_id: str | None = None
    review_due_date: datetime | None = None
    created_at: str
    is_overdue: bool = False


class MonthlyCount(BaseModel):
    month: str  # "2026-01"
    count: int


class SupplierWatchlistItem(BaseModel):
    id: str
    name: str
    country: str
    supplier_tier: str
    critical_findings: int
    high_findings: int
    open_actions: int
    overdue_actions: int
    last_assessment_date: str | None


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
    # Review queue KPIs (M26)
    awaiting_review: int = 0
    reviews_overdue: int = 0
    recently_approved: int = 0
    recently_rejected: int = 0
    review_queue: list[ReviewQueueItem] = []
    # Supplier KPIs (M27)
    total_suppliers: int = 0
    active_suppliers: int = 0
    suppliers_with_critical_risks: int = 0
    suppliers_without_assessments: int = 0
    supplier_watchlist: list[SupplierWatchlistItem] = []
