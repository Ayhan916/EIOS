"""
EIOS Domain Model — Evaluation Engine (GAP-02 / FR-014)

Tracks platform-level AI quality metrics: accuracy, confidence calibration,
hallucination rate, cost, and benchmark pass/fail status.

All snapshots are system-wide (no organization_id) — they reflect the
health of the EIOS AI engine, not a specific tenant's data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class EvaluationRun(BaseEntity):
    """A periodic or manual snapshot of platform AI quality metrics.

    Computed from AgentRunModel records for the evaluation window.
    """

    run_type: str = "manual"            # "scheduled" | "manual"
    window_days: int = 30               # days of agent_runs evaluated
    agent_run_count: int = 0            # number of agent runs in window

    # Quality metrics (0.0 – 1.0)
    accuracy_score: float = 0.0         # benchmark pass rate
    precision_score: float = 0.0        # true positives / (true + false positives)
    recall_score: float = 0.0           # true positives / (true + false negatives)
    confidence_score: float = 0.0       # mean confidence across agent runs

    # Reliability
    hallucination_rate: float = 0.0     # proxy: error rate on high-confidence runs
    error_rate: float = 0.0             # runs with error / total runs

    # Cost (USD)
    cost_usd_total: float = 0.0
    cost_usd_last_7d: float = 0.0
    cost_usd_last_30d: float = 0.0

    # Benchmark
    benchmark_status: str = "unknown"   # "green" | "yellow" | "red" | "unknown"
    benchmark_passed: int = 0
    benchmark_total: int = 0

    # Platform health (0–100)
    platform_health_score: float = 0.0

    raw_metrics: dict = field(default_factory=dict)
    computed_at: datetime | None = None


@dataclass(slots=True, kw_only=True)
class BenchmarkResult(BaseEntity):
    """Result of a single benchmark test case within an EvaluationRun."""

    evaluation_run_id: str = ""
    benchmark_name: str = ""            # e.g. "CREDIBILITY_HIGH_SOURCE"
    module: str = ""                    # e.g. "source_credibility" | "prioritization"
    dimension: str = ""                 # accuracy | precision | recall | hallucination | cost
    passed: bool = False
    score: float = 0.0                  # 0.0 – 1.0
    expected_output: str = ""
    actual_output: str = ""
    failure_reason: str = ""
    duration_ms: float = 0.0


@dataclass(slots=True, kw_only=True)
class CalibrationEvent(BaseEntity):
    """Records whether a predicted confidence level was accurate after audit.

    An analyst observes: entity X was predicted with confidence level Y,
    and the real audit outcome was Z (confirmed / refuted / unknown).
    Aggregated over time this produces a calibration curve per confidence band.
    """

    organization_id: str = ""
    entity_type: str = ""        # "finding" | "risk" | "recommendation"
    entity_id: str = ""
    predicted_confidence: str = ""  # "high" | "medium" | "low"
    actual_outcome: str = "unknown"  # "confirmed" | "refuted" | "unknown"
    recorded_by: str | None = None
    recorded_at: datetime | None = None
