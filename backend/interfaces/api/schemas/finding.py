from pydantic import BaseModel, Field

from domain.enums import ConfidenceLevel, RiskLevel

from .base import EntityResponse


class FindingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    assessment_id: str
    category: str = ""
    severity: RiskLevel = RiskLevel.MEDIUM
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    reasoning: str | None = None
    uncertainty: str | None = None


class FindingResponse(EntityResponse):
    title: str
    description: str
    assessment_id: str
    category: str
    severity: str
    confidence: str
    reasoning: str | None = None
    uncertainty: str | None = None
    evidence_strength: str | None = None
    evidence_source_count: int = 0


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
