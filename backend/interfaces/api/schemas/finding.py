from pydantic import BaseModel, Field, model_validator

from domain.enums import ConfidenceLevel, RiskLevel

from .base import EntityResponse


class ConfidenceCardOut(BaseModel):
    """Standardised confidence output (ADR-015 / E4-F1).

    `overall_level` is a backward-compat alias for `level` — consumers that
    already read `overall_level` continue to work without code changes.
    `limitations` surfaces as UI warnings for missing information.
    """

    level: str
    overall_level: str = ""     # set by validator from level if not provided
    score: float
    basis: str
    limitations: list[str] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _set_overall_level(self) -> "ConfidenceCardOut":
        if not self.overall_level:
            self.overall_level = self.level
        return self

    @classmethod
    def from_card(cls, card) -> "ConfidenceCardOut":
        level_str = card.level.value if hasattr(card.level, "value") else str(card.level)
        return cls(
            level=level_str,
            overall_level=level_str,
            score=card.score,
            basis=card.basis,
            limitations=list(card.limitations),
        )


class FindingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    assessment_id: str
    category: str = ""
    severity: RiskLevel = RiskLevel.MEDIUM
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    reasoning: str | None = None
    uncertainty: str | None = None
    severity_score: int | None = Field(default=None, ge=1, le=10)
    probability_score: int | None = Field(default=None, ge=1, le=10)
    # E3-F1: ADR-003 — at least one evidence reference required (POST /findings → 422 if empty)
    evidence_ids: list[str] = Field(default_factory=list)


class FindingResponse(EntityResponse):
    title: str
    description: str
    assessment_id: str
    category: str
    severity: str
    confidence: str
    # ADR-015 E4-F1: structured confidence card (includes limitations as UI warnings)
    confidence_card: ConfidenceCardOut | None = None
    reasoning: str | None = None
    uncertainty: str | None = None
    evidence_strength: str | None = None
    evidence_source_count: int = 0
    severity_score: int | None = None
    probability_score: int | None = None
    evidence_quality_status: str = "Hypothetical"


class FindingEvidenceLinkResponse(EntityResponse):
    finding_id: str
    evidence_id: str
    evidence_chunk_id: str | None = None
    page_number: int | None = None
    confidence_score: float | None = None
    supporting_excerpt: str | None = None
    link_method: str


class FindingWithLinksResponse(BaseModel):
    finding: FindingResponse
    evidence_links: list[FindingEvidenceLinkResponse]


class EvidenceInsightsResponse(BaseModel):
    """Summary of evidence intelligence for all findings in an assessment."""

    assessment_id: str
    total_findings: int
    linked_findings: int
    total_evidence_links: int
    strength_distribution: dict[str, int]
    findings: list[FindingWithLinksResponse]
