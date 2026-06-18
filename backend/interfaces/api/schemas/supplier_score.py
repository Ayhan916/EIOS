from __future__ import annotations

from pydantic import BaseModel


class ScoreDriver(BaseModel):
    factor: str
    count: int
    impact: str  # high | medium | low
    description: str


class SupplierScoreResponse(BaseModel):
    supplier_id: str
    supplier_name: str
    calculated_at: str
    score_version: str

    esg_score: float
    environmental_score: float
    social_score: float
    governance_score: float

    risk_score: float
    risk_band: str

    trend: str
    trend_delta: float

    sector_percentile: float | None
    drivers: list[ScoreDriver]
    inputs: dict  # full raw inputs — always included for auditability


class SupplierScoreHistoryEntry(BaseModel):
    calculated_at: str
    esg_score: float
    risk_score: float
    risk_band: str
    trend: str


class SupplierBenchmark(BaseModel):
    supplier_id: str
    supplier_name: str
    risk_score: float
    risk_band: str
    sector_percentile: float | None
    peer_comparison: str  # "Better than peers" | "Average" | "Worse than peers"
    peers_evaluated: int
    industry: str


class WatchlistEntry(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str
    industry: str
    supplier_tier: str
    risk_score: float
    risk_band: str
    trend: str
    trend_delta: float
    critical_findings: int
    overdue_actions: int
    alert_reasons: list[str]


class PortfolioAnalytics(BaseModel):
    total_suppliers: int
    scored_suppliers: int
    critical_risk_suppliers: int
    high_risk_suppliers: int
    improving_suppliers: int
    deteriorating_suppliers: int
    avg_esg_score: float | None
    avg_risk_score: float | None
    risk_distribution: dict[str, int]


class ExecutiveRankingEntry(BaseModel):
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


class HeatmapCell(BaseModel):
    pillar: str    # Environmental | Social | Governance
    severity: str  # Critical | High | Medium | Low
    count: int


class RiskHeatmap(BaseModel):
    cells: list[HeatmapCell]
    total_findings: int
    supplier_id: str | None = None  # None = org-wide heatmap
