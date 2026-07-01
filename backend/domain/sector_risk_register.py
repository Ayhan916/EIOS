"""
EIOS Domain — CSDDD Sector Risk Register (TASK-003)

Sector-level risk scores per CSDDD protected right (Annex I).
Scores are deterministic and human-approved (M43 compliant).

Architecture:
- SectorRightScore: single probability score for one NACE sector × CSDDD right pair
- ScenarioTemplate: fixed multiplier table for a scenario type (offline-curated)
- SimulationResult: output of deterministic scenario simulation
- CalibrationSuggestion: RAG-generated score suggestion awaiting Founder approval
- ScenarioSuggestion: news-triggered scenario suggestion awaiting Founder confirmation
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.enums import (
    CalibrationStatus,
    CSDDDRight,
    ConfidenceLevel,
    ScenarioSuggestionStatus,
    ScenarioType,
)


@dataclass
class SectorRightScore:
    """Approved probability score for one NACE 2-digit sector × CSDDD right pair.

    Stored in DB after Founder approval. Never updated by LLM at runtime.
    """
    nace_2digit: str            # e.g. "29" (Motor vehicles)
    csddd_right: CSDDDRight
    probability: int            # 1–10 (1 = very unlikely, 10 = near-certain)
    confidence: ConfidenceLevel
    sources: list[str]          # e.g. ["ILO 2024 Automotive Sector Report"]
    calibration_version: str    # e.g. "v1.0"
    approved_by: str | None = None   # user ID; None = static seed data
    id: str | None = None
    organization_id: str | None = None


@dataclass
class ScenarioTemplate:
    """Deterministic multiplier table for a scenario type.

    factors: CSDDDRight → float multiplier applied to base probability.
    Rights not listed default to factor 1.0 (no change).
    Result is always clamped to [1, 10].
    """
    scenario_type: ScenarioType
    name: str
    description: str
    factors: dict[CSDDDRight, float]
    affected_nace_sections: list[str]   # NACE letter sections most impacted
    sources: list[str]


@dataclass
class SimulationResult:
    """Output of a deterministic scenario simulation.

    No LLM involved at runtime — purely base_score × factor, clamped to [1, 10].
    Explanation texts are static strings generated from template metadata.
    """
    nace_2digit: str
    sector_name: str
    scenario_type: ScenarioType
    scenario_name: str
    baseline_scores: dict[CSDDDRight, int]
    scenario_scores: dict[CSDDDRight, int]
    delta: dict[CSDDDRight, int]
    explanation: dict[CSDDDRight, str]
    simulated_at: str                    # ISO 8601 UTC
    calibration_version: str


@dataclass
class CalibrationSuggestion:
    """RAG-generated score suggestion pending Founder review.

    Created by SectorRiskCalibrationPipeline. Never auto-applied.
    Becomes a SectorRightScore only after explicit approve() call.
    """
    id: str
    nace_2digit: str
    csddd_right: CSDDDRight
    suggested_probability: int           # 1–10 from LLM extraction
    confidence: ConfidenceLevel
    reasoning: str                       # max 200 chars from LLM
    sources: list[str]                   # chunk titles/URLs used as RAG context
    status: CalibrationStatus = CalibrationStatus.PENDING
    reviewed_by: str | None = None
    rejection_reason: str | None = None
    created_at: str = ""
    reviewed_at: str | None = None
    organization_id: str | None = None


@dataclass
class ScenarioSuggestion:
    """News-triggered scenario suggestion pending Founder confirmation.

    Created by NewsScenarioDetector when article volume exceeds threshold.
    Activating it enables the scenario in the simulation API.
    """
    id: str
    scenario_type: ScenarioType
    affected_nace_codes: list[str]
    trigger_article_count: int
    trigger_keywords_matched: list[str]
    sample_headlines: list[str]          # up to 3 representative headlines
    status: ScenarioSuggestionStatus = ScenarioSuggestionStatus.PENDING
    activated_by: str | None = None
    created_at: str = ""
    activated_at: str | None = None
    expires_at: str | None = None        # scenario auto-deactivates after N days
    organization_id: str | None = None


@dataclass
class SectorRiskSummary:
    """Aggregated risk summary for a NACE sector — used in API list responses."""
    nace_2digit: str
    sector_name: str
    nace_section: str
    highest_probability: int
    highest_right: CSDDDRight | None
    average_probability: float
    rights_above_7: int                  # count of rights with probability >= 7
    calibration_version: str
    score_count: int                     # how many rights have approved scores
