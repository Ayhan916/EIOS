from __future__ import annotations

from dataclasses import dataclass, field

from domain.base_entity import BaseEntity
from domain.enums import RiskBand, TrendDirection


@dataclass(slots=True, kw_only=True)
class SupplierScore(BaseEntity):
    """
    Immutable snapshot of a supplier's computed ESG and Risk scores.

    A new record is created on every (re)calculation so the full audit trail
    is preserved.  The latest record per supplier is the authoritative score.
    """

    supplier_id: str
    organization_id: str
    score_version: str = "1.0"

    # ESG scores — higher is better (0-100)
    esg_score: float = 100.0
    environmental_score: float = 100.0
    social_score: float = 100.0
    governance_score: float = 100.0

    # Risk score — higher is worse (0-100)
    risk_score: float = 0.0
    risk_band: RiskBand = field(default=RiskBand.LOW)

    # Trend vs previous snapshot
    trend: TrendDirection = field(default=TrendDirection.STABLE)
    trend_delta: float = 0.0  # ESG score delta (positive = improving)

    # Peer benchmark
    sector_percentile: float | None = None  # 0-100; lower risk_score = higher percentile

    # Auditability
    inputs: dict = field(default_factory=dict)   # raw counts used for calculation
    drivers: list = field(default_factory=list)  # human-readable score explanation
