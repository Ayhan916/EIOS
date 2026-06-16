"""
EIOS Sector Benchmarking Engine (M19)

Computes how an assessment compares to:
  1. The static ESG risk profile for its sector (baseline expectations)
  2. Peer assessments from the same organisation in the same sector

All logic is deterministic and explainable — no LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.assessment import Assessment
from domain.finding import Finding
from domain.risk import Risk
from domain.sector import Sector

from .profiles import SectorESGProfile, _FALLBACK, get_profile


# ── Output data structures ─────────────────────────────────────────────────────

@dataclass
class SeverityDistribution:
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    @property
    def total(self) -> int:
        return self.critical + self.high + self.medium + self.low

    @property
    def high_or_critical_count(self) -> int:
        return self.critical + self.high


@dataclass
class PeerSummary:
    assessment_id: str
    title: str
    quality_score: float | None
    finding_count: int
    risk_count: int
    high_critical_finding_count: int


@dataclass
class SectorBenchmark:
    """Full benchmark of an assessment against its sector profile and org peers."""

    assessment_id: str
    assessment_title: str

    # Sector context
    sector_id: str | None
    sector_nace_code: str
    sector_name: str
    profile_nace_section: str

    # Assessment metrics
    finding_distribution: SeverityDistribution
    risk_distribution: SeverityDistribution
    quality_score: float | None

    # Sector baseline expectations
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
    mandatory_coverage: float | None      # Actual coverage (None = not computed yet)
    coverage_vs_baseline: float | None    # actual - baseline (negative = below)

    # Coverage rating
    coverage_rating: str     # "above_baseline" | "meets_baseline" | "below_baseline" | "not_assessed"
    coverage_explanation: str

    # Finding adequacy
    finding_adequacy: str    # "above_expected" | "meets_expected" | "below_expected"
    finding_explanation: str

    # Key sector themes found vs missed
    key_themes_identified: list[str]   # Themes whose keywords appeared in findings/risks
    key_themes_not_addressed: list[str]

    # Peer comparison (org-scoped, same sector)
    peer_count: int
    peers: list[PeerSummary]
    org_avg_quality_score: float | None
    org_avg_finding_count: float | None

    # Overall benchmark rating
    benchmark_rating: str        # "above_sector_baseline" | "meets_sector_baseline" | "below_sector_baseline"
    benchmark_explanation: str


# ── Public API ─────────────────────────────────────────────────────────────────

def compute_benchmark(
    assessment: Assessment,
    sector: Sector | None,
    findings: list[Finding],
    risks: list[Risk],
    mandatory_coverage: float | None,
    peers: list[tuple[Assessment, list[Finding]]],
) -> SectorBenchmark:
    """
    Compute a full sector benchmark for the given assessment.

    Parameters
    ----------
    assessment        The target assessment.
    sector            The sector entity linked to the assessment (or None).
    findings          Findings for this assessment.
    risks             Risks for this assessment.
    mandatory_coverage  Pre-computed mandatory compliance coverage (0-1), or None.
    peers             List of (peer_assessment, peer_findings) for same-sector org assessments.
                      The target assessment itself must NOT be in this list.
    """
    nace_code = sector.nace_code if sector else ""
    profile = get_profile(nace_code)

    finding_dist = _severity_distribution(findings, "severity")
    risk_dist = _severity_distribution(risks, "risk_level")

    # Compliance coverage vs baseline
    coverage_vs_baseline: float | None = None
    if mandatory_coverage is not None:
        coverage_vs_baseline = round(mandatory_coverage - profile.baseline_mandatory_coverage, 4)

    coverage_rating, coverage_explanation = _rate_coverage(
        mandatory_coverage, profile, assessment
    )

    finding_adequacy, finding_explanation = _rate_finding_adequacy(
        finding_dist.total, profile
    )

    # Which key sector risk themes appear in the assessment content?
    assessment_text = _build_assessment_text(assessment, findings, risks)
    themes_found = _match_themes(profile.key_risk_themes, assessment_text)
    themes_missed = [t for t in profile.key_risk_themes if t not in themes_found]

    # Peer metrics
    peer_summaries, org_avg_quality, org_avg_findings = _compute_peer_metrics(peers)

    benchmark_rating, benchmark_explanation = _overall_rating(
        coverage_rating=coverage_rating,
        finding_adequacy=finding_adequacy,
        themes_missed_count=len(themes_missed),
        total_themes=len(profile.key_risk_themes),
        quality_score=assessment.quality_score,
        profile=profile,
    )

    return SectorBenchmark(
        assessment_id=assessment.id,
        assessment_title=assessment.title,
        sector_id=sector.id if sector else None,
        sector_nace_code=nace_code or "—",
        sector_name=sector.name if sector else profile.section_name,
        profile_nace_section=profile.nace_section,
        finding_distribution=finding_dist,
        risk_distribution=risk_dist,
        quality_score=assessment.quality_score,
        baseline_mandatory_coverage=profile.baseline_mandatory_coverage,
        expected_min_findings=profile.expected_min_findings,
        expected_min_risks=profile.expected_min_risks,
        environmental_risk=profile.environmental_risk,
        social_risk=profile.social_risk,
        governance_risk=profile.governance_risk,
        overall_sector_risk=profile.overall_risk,
        key_risk_themes=list(profile.key_risk_themes),
        applicable_frameworks=list(profile.applicable_frameworks),
        esg_priority_categories=list(profile.esg_priority_categories),
        regulatory_exposure_notes=profile.regulatory_exposure_notes,
        mandatory_coverage=mandatory_coverage,
        coverage_vs_baseline=coverage_vs_baseline,
        coverage_rating=coverage_rating,
        coverage_explanation=coverage_explanation,
        finding_adequacy=finding_adequacy,
        finding_explanation=finding_explanation,
        key_themes_identified=themes_found,
        key_themes_not_addressed=themes_missed,
        peer_count=len(peers),
        peers=peer_summaries,
        org_avg_quality_score=org_avg_quality,
        org_avg_finding_count=org_avg_findings,
        benchmark_rating=benchmark_rating,
        benchmark_explanation=benchmark_explanation,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _severity_distribution(
    items: list,
    level_attr: str,
) -> SeverityDistribution:
    dist = SeverityDistribution()
    for item in items:
        level_val = getattr(item, level_attr, None)
        level = level_val.value if hasattr(level_val, "value") else str(level_val or "")
        if level == "Critical":
            dist.critical += 1
        elif level == "High":
            dist.high += 1
        elif level == "Medium":
            dist.medium += 1
        elif level == "Low":
            dist.low += 1
    return dist


def _rate_coverage(
    mandatory_coverage: float | None,
    profile: SectorESGProfile,
    assessment: Assessment,
) -> tuple[str, str]:
    if mandatory_coverage is None:
        return (
            "not_assessed",
            "Compliance coverage has not yet been computed for this assessment. "
            "Run a compliance analysis to obtain a coverage rating.",
        )

    delta = mandatory_coverage - profile.baseline_mandatory_coverage
    pct = round(mandatory_coverage * 100)
    baseline_pct = round(profile.baseline_mandatory_coverage * 100)

    if delta >= 0.15:
        return (
            "above_baseline",
            f"Mandatory compliance coverage ({pct}%) exceeds the sector baseline "
            f"of {baseline_pct}% by {round(delta*100)}pp. This assessment demonstrates "
            "strong regulatory framework alignment for its sector.",
        )
    elif delta >= -0.10:
        return (
            "meets_baseline",
            f"Mandatory compliance coverage ({pct}%) is within acceptable range "
            f"of the sector baseline ({baseline_pct}%). Minor gaps may exist but "
            "overall regulatory framework alignment is adequate.",
        )
    else:
        return (
            "below_baseline",
            f"Mandatory compliance coverage ({pct}%) falls {abs(round(delta*100))}pp "
            f"below the sector baseline of {baseline_pct}%. This sector typically "
            "requires stronger regulatory framework coverage. A gap remediation plan "
            "is recommended.",
        )


def _rate_finding_adequacy(
    finding_count: int,
    profile: SectorESGProfile,
) -> tuple[str, str]:
    min_expected = profile.expected_min_findings
    sector = profile.section_name

    if finding_count == 0:
        return (
            "below_expected",
            f"No material findings were extracted. The {sector} sector typically "
            f"surfaces at least {min_expected} material ESG findings in a credible "
            "assessment. Consider whether the evidence base is sufficient.",
        )
    elif finding_count >= min_expected + 2:
        return (
            "above_expected",
            f"{finding_count} material findings were identified, exceeding the "
            f"minimum expectation of {min_expected} for the {sector} sector. "
            "The assessment demonstrates thorough ESG investigation.",
        )
    elif finding_count >= min_expected:
        return (
            "meets_expected",
            f"{finding_count} material findings were identified, meeting the "
            f"minimum expectation of {min_expected} for the {sector} sector.",
        )
    else:
        return (
            "below_expected",
            f"Only {finding_count} material finding(s) were identified. The "
            f"{sector} sector typically requires at least {min_expected} findings "
            "for a credible due diligence assessment. The evidence base may be limited.",
        )


def _build_assessment_text(
    assessment: Assessment,
    findings: list[Finding],
    risks: list[Risk],
) -> str:
    parts = [
        assessment.description or "",
        assessment.scope or "",
        assessment.methodology or "",
    ]
    for f in findings:
        parts += [f.title, f.description, f.reasoning or "", f.category or ""]
    for r in risks:
        parts += [r.title, r.description, r.reasoning or "", r.category or ""]
    return " ".join(parts).lower()


def _match_themes(
    themes: tuple[str, ...],
    text: str,
) -> list[str]:
    """Return themes whose keywords appear (case-insensitive) in the text."""
    text_lower = text.lower()
    matched = []
    for theme in themes:
        key_words = [w.lower() for w in theme.split() if len(w) > 4]
        if any(kw in text_lower for kw in key_words):
            matched.append(theme)
    return matched


def _compute_peer_metrics(
    peers: list[tuple[Assessment, list[Finding]]],
) -> tuple[list[PeerSummary], float | None, float | None]:
    summaries = []
    quality_scores = []
    finding_counts = []

    for peer_assessment, peer_findings in peers:
        finding_dist = _severity_distribution(peer_findings, "severity")
        summaries.append(PeerSummary(
            assessment_id=peer_assessment.id,
            title=peer_assessment.title,
            quality_score=peer_assessment.quality_score,
            finding_count=finding_dist.total,
            risk_count=0,  # Simplified — risks not loaded for peers in this pass
            high_critical_finding_count=finding_dist.high_or_critical_count,
        ))
        if peer_assessment.quality_score is not None:
            quality_scores.append(peer_assessment.quality_score)
        finding_counts.append(finding_dist.total)

    org_avg_quality = (
        round(sum(quality_scores) / len(quality_scores), 4)
        if quality_scores else None
    )
    org_avg_findings = (
        round(sum(finding_counts) / len(finding_counts), 1)
        if finding_counts else None
    )

    return summaries, org_avg_quality, org_avg_findings


def _overall_rating(
    coverage_rating: str,
    finding_adequacy: str,
    themes_missed_count: int,
    total_themes: int,
    quality_score: float | None,
    profile: SectorESGProfile,
) -> tuple[str, str]:
    """Derive an overall benchmark rating from the individual component ratings."""

    # Score each dimension
    coverage_ok = coverage_rating in ("above_baseline", "meets_baseline")
    findings_ok = finding_adequacy in ("above_expected", "meets_expected")
    themes_coverage = (total_themes - themes_missed_count) / total_themes if total_themes else 1.0
    quality_ok = quality_score is not None and quality_score >= 0.40

    strong_count = sum([
        coverage_rating == "above_baseline",
        finding_adequacy == "above_expected",
        themes_coverage >= 0.60,
        quality_score is not None and quality_score >= 0.65,
    ])

    weak_count = sum([
        not coverage_ok,
        not findings_ok,
        themes_coverage < 0.30,
        quality_score is not None and quality_score < 0.30,
    ])

    sector_risk = profile.overall_risk

    if weak_count >= 2 or (not coverage_ok and not findings_ok):
        rating = "below_sector_baseline"
        explanation = (
            f"This assessment falls below the baseline expectation for the "
            f"{profile.section_name} sector ({sector_risk} overall ESG risk). "
            f"Key gaps: {_describe_gaps(coverage_rating, finding_adequacy, themes_missed_count, total_themes)}. "
            "Strengthening the evidence base and expanding compliance framework coverage "
            "is recommended before this assessment can be considered credible for "
            "enterprise due diligence purposes."
        )
    elif strong_count >= 2 and weak_count == 0:
        rating = "above_sector_baseline"
        explanation = (
            f"This assessment exceeds the baseline expectation for the "
            f"{profile.section_name} sector ({sector_risk} overall ESG risk). "
            "The depth of findings, risk identification, and regulatory coverage "
            "demonstrates thorough due diligence. This assessment can serve as a "
            "strong basis for executive reporting and regulatory disclosure."
        )
    else:
        rating = "meets_sector_baseline"
        explanation = (
            f"This assessment meets the baseline expectation for the "
            f"{profile.section_name} sector ({sector_risk} overall ESG risk). "
            "Core ESG dimensions are covered, though additional depth may be needed "
            "for specific regulatory frameworks or high-exposure risk themes."
        )

    return rating, explanation


def _describe_gaps(
    coverage_rating: str,
    finding_adequacy: str,
    themes_missed: int,
    total_themes: int,
) -> str:
    gaps = []
    if coverage_rating == "below_baseline":
        gaps.append("compliance coverage below sector baseline")
    if finding_adequacy == "below_expected":
        gaps.append("insufficient material findings")
    if themes_missed > 0 and total_themes > 0:
        gaps.append(f"{themes_missed}/{total_themes} key sector risk themes not addressed")
    return "; ".join(gaps) if gaps else "no specific gaps identified"
