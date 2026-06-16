from typing import Optional

from pydantic import BaseModel


class SectorESGProfileResponse(BaseModel):
    nace_section: str
    section_name: str
    environmental_risk: str
    social_risk: str
    governance_risk: str
    overall_risk: str
    key_risk_themes: list[str]
    applicable_frameworks: list[str]
    baseline_mandatory_coverage: float
    expected_min_findings: int
    expected_min_risks: int
    regulatory_exposure_notes: str
    esg_priority_categories: list[str]


class SeverityDistributionResponse(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    total: int
    high_or_critical_count: int


class PeerSummaryResponse(BaseModel):
    assessment_id: str
    title: str
    quality_score: Optional[float] = None
    finding_count: int
    risk_count: int
    high_critical_finding_count: int


class SectorBenchmarkResponse(BaseModel):
    assessment_id: str
    assessment_title: str

    # Sector context
    sector_id: Optional[str] = None
    sector_nace_code: str
    sector_name: str
    profile_nace_section: str

    # Assessment metrics
    finding_distribution: SeverityDistributionResponse
    risk_distribution: SeverityDistributionResponse
    quality_score: Optional[float] = None

    # Sector baseline
    baseline_mandatory_coverage: float
    expected_min_findings: int
    expected_min_risks: int
    environmental_risk: str
    social_risk: str
    governance_risk: str
    overall_sector_risk: str
    key_risk_themes: list[str]
    applicable_frameworks: list[str]
    esg_priority_categories: list[str]
    regulatory_exposure_notes: str

    # Compliance comparison
    mandatory_coverage: Optional[float] = None
    coverage_vs_baseline: Optional[float] = None
    coverage_rating: str
    coverage_explanation: str

    # Finding adequacy
    finding_adequacy: str
    finding_explanation: str

    # Theme coverage
    key_themes_identified: list[str]
    key_themes_not_addressed: list[str]

    # Peers
    peer_count: int
    peers: list[PeerSummaryResponse]
    org_avg_quality_score: Optional[float] = None
    org_avg_finding_count: Optional[float] = None

    # Overall
    benchmark_rating: str
    benchmark_explanation: str
