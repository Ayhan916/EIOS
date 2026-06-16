from __future__ import annotations

from pydantic import BaseModel


class ArticleCoverageResponse(BaseModel):
    code: str
    framework: str
    article: str
    title: str
    obligation_type: str
    esg_categories: list[str]
    covered: bool


class FrameworkCoverageResponse(BaseModel):
    framework: str
    total_articles: int
    covered_count: int
    coverage_ratio: float
    articles: list[ArticleCoverageResponse]


class GapResponse(BaseModel):
    article_code: str
    framework: str
    article: str
    title: str
    obligation_type: str
    esg_categories: list[str]
    regulatory_exposure: float
    gap_severity: str
    explanation: str
    remediation_hint: str


class ComplianceVerdictResponse(BaseModel):
    status: str
    mandatory_coverage_ratio: float
    total_mandatory_articles: int
    covered_mandatory_count: int
    mandatory_gap_count: int
    critical_gap_count: int
    high_gap_count: int
    weighted_gap_score: float
    explanation: str
    top_gap_codes: list[str]


class ComplianceCoverageResponse(BaseModel):
    assessment_id: str
    covered_article_codes: list[str]
    framework_coverage: list[FrameworkCoverageResponse]
    overall_coverage_ratio: float
    mandatory_coverage_ratio: float
    quality_score: float | None
    gaps: list[GapResponse]
    verdict: ComplianceVerdictResponse


class FrameworkInfo(BaseModel):
    framework: str
    article_count: int
    mandatory_count: int
    recommended_count: int
    articles: list[ArticleCoverageResponse]
