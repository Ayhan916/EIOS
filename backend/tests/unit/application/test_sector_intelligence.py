"""Unit tests for M19 Sector Intelligence & Benchmarking."""

from __future__ import annotations

from typing import Any

import pytest

from application.sector_intelligence.benchmarking import (
    SectorBenchmark,
    SeverityDistribution,
    _match_themes,
    _rate_coverage,
    _rate_finding_adequacy,
    _severity_distribution,
    compute_benchmark,
)
from application.sector_intelligence.profiles import (
    SectorESGProfile,
    all_profiles,
    get_profile,
    get_profile_by_section,
)
from domain.assessment import Assessment
from domain.enums import ConfidenceLevel, EntityStatus, RiskLevel
from domain.finding import Finding
from domain.risk import Risk
from domain.sector import Sector


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_sector(**kwargs: Any) -> Sector:
    defaults: dict[str, Any] = dict(
        id="sector-1",
        name="Mining and Quarrying",
        nace_code="B05",
        organization_id="org-1",
    )
    return Sector(**{**defaults, **kwargs})


def _make_assessment(**kwargs: Any) -> Assessment:
    defaults: dict[str, Any] = dict(
        id="assess-1",
        title="Acme Mining ESG Assessment",
        description="ESG due diligence for Acme Mining covering labour rights and environmental impact.",
        sector_id="sector-1",
        organization_id="org-1",
        assessment_type="ESG Due Diligence",
        scope="Tier-1 suppliers, 2024",
        quality_score=0.65,
    )
    return Assessment(**{**defaults, **kwargs})


def _make_finding(severity: str = "High", **kwargs: Any) -> Finding:
    defaults: dict[str, Any] = dict(
        id="find-1",
        title="Child Labour in Artisanal Mining",
        description="Evidence of child labour in artisanal mining operations.",
        assessment_id="assess-1",
        category="Human Rights",
        severity=RiskLevel(severity),
        confidence=ConfidenceLevel.HIGH,
    )
    return Finding(**{**defaults, **kwargs})


def _make_risk(level: str = "High", **kwargs: Any) -> Risk:
    defaults: dict[str, Any] = dict(
        id="risk-1",
        title="Regulatory Sanction Risk",
        description="LkSG sanction risk for non-disclosure of supply chain data.",
        assessment_id="assess-1",
        category="Regulatory",
        risk_level=RiskLevel(level),
        confidence=ConfidenceLevel.MEDIUM,
    )
    return Risk(**{**defaults, **kwargs})


# ── Profile registry ──────────────────────────────────────────────────────────

class TestSectorProfiles:
    def test_all_profiles_have_required_fields(self) -> None:
        for p in all_profiles():
            assert p.nace_section
            assert p.section_name
            assert p.environmental_risk in ("Low", "Medium", "High", "Critical")
            assert p.social_risk in ("Low", "Medium", "High", "Critical")
            assert p.governance_risk in ("Low", "Medium", "High", "Critical")
            assert p.overall_risk in ("Low", "Medium", "High", "Critical")
            assert len(p.key_risk_themes) >= 3
            assert len(p.applicable_frameworks) >= 1
            assert 0.0 <= p.baseline_mandatory_coverage <= 1.0
            assert p.expected_min_findings >= 1
            assert p.expected_min_risks >= 1

    def test_profiles_cover_key_nace_sections(self) -> None:
        sections = {p.nace_section for p in all_profiles()}
        for expected in ("A", "B", "C", "D", "F", "G", "H", "J", "K", "Q"):
            assert expected in sections, f"Missing NACE section {expected}"

    def test_get_profile_by_nace_code(self) -> None:
        profile = get_profile("B05")
        assert profile.nace_section == "B"
        assert profile.environmental_risk == "Critical"

    def test_get_profile_fallback_for_unknown(self) -> None:
        profile = get_profile("Z99")
        assert profile.nace_section == "*"
        assert profile.section_name == "General Industry"

    def test_get_profile_by_section(self) -> None:
        profile = get_profile_by_section("C")
        assert profile.nace_section == "C"
        assert profile.section_name == "Manufacturing"

    def test_get_profile_empty_code(self) -> None:
        profile = get_profile("")
        assert profile.nace_section == "*"

    def test_mining_is_critical_risk(self) -> None:
        profile = get_profile("B")
        assert profile.overall_risk == "Critical"
        assert "Mining" in profile.section_name

    def test_finance_has_critical_governance(self) -> None:
        profile = get_profile("K")
        assert profile.governance_risk == "Critical"

    def test_agriculture_has_critical_environmental(self) -> None:
        profile = get_profile("A")
        assert profile.environmental_risk == "Critical"

    def test_all_profiles_excludes_fallback(self) -> None:
        sections = [p.nace_section for p in all_profiles()]
        assert "*" not in sections

    def test_baseline_coverage_is_reasonable(self) -> None:
        for p in all_profiles():
            assert 0.30 <= p.baseline_mandatory_coverage <= 0.75, (
                f"Baseline coverage for {p.nace_section} is out of expected range: "
                f"{p.baseline_mandatory_coverage}"
            )


# ── Severity distribution ─────────────────────────────────────────────────────

class TestSeverityDistribution:
    def test_distribution_from_findings(self) -> None:
        findings = [
            _make_finding("Critical"),
            _make_finding("Critical"),
            _make_finding("High"),
            _make_finding("Medium"),
            _make_finding("Low"),
        ]
        dist = _severity_distribution(findings, "severity")
        assert dist.critical == 2
        assert dist.high == 1
        assert dist.medium == 1
        assert dist.low == 1
        assert dist.total == 5
        assert dist.high_or_critical_count == 3

    def test_empty_findings(self) -> None:
        dist = _severity_distribution([], "severity")
        assert dist.total == 0
        assert dist.high_or_critical_count == 0

    def test_distribution_from_risks(self) -> None:
        risks = [_make_risk("High"), _make_risk("Low")]
        dist = _severity_distribution(risks, "risk_level")
        assert dist.high == 1
        assert dist.low == 1
        assert dist.total == 2


# ── Coverage rating ───────────────────────────────────────────────────────────

class TestCoverageRating:
    def setup_method(self) -> None:
        self.profile = get_profile("B")
        self.assessment = _make_assessment()

    def test_above_baseline(self) -> None:
        rating, explanation = _rate_coverage(0.85, self.profile, self.assessment)
        assert rating == "above_baseline"
        assert "exceeds" in explanation.lower()

    def test_meets_baseline(self) -> None:
        # Mining baseline is 0.65; meets_baseline = delta in [-0.10, +0.15)
        rating, explanation = _rate_coverage(0.62, self.profile, self.assessment)
        assert rating == "meets_baseline"
        assert "within" in explanation.lower()

    def test_below_baseline(self) -> None:
        rating, explanation = _rate_coverage(0.30, self.profile, self.assessment)
        assert rating == "below_baseline"
        assert "below" in explanation.lower()

    def test_not_assessed_when_none(self) -> None:
        rating, explanation = _rate_coverage(None, self.profile, self.assessment)
        assert rating == "not_assessed"
        assert "not yet been computed" in explanation.lower()


# ── Finding adequacy ──────────────────────────────────────────────────────────

class TestFindingAdequacy:
    def setup_method(self) -> None:
        self.profile = get_profile("B")  # expects 4 min findings

    def test_zero_findings_is_below(self) -> None:
        rating, _ = _rate_finding_adequacy(0, self.profile)
        assert rating == "below_expected"

    def test_meets_minimum(self) -> None:
        rating, _ = _rate_finding_adequacy(self.profile.expected_min_findings, self.profile)
        assert rating == "meets_expected"

    def test_above_expected(self) -> None:
        rating, _ = _rate_finding_adequacy(self.profile.expected_min_findings + 3, self.profile)
        assert rating == "above_expected"

    def test_one_below_minimum_is_below(self) -> None:
        rating, _ = _rate_finding_adequacy(self.profile.expected_min_findings - 1, self.profile)
        assert rating == "below_expected"


# ── Theme matching ────────────────────────────────────────────────────────────

class TestThemeMatching:
    def test_matches_keyword_in_text(self) -> None:
        themes = ("Child and forced labour in supply chains",)
        text = "evidence of child labour was found in tier-2 suppliers"
        matched = _match_themes(themes, text)
        assert len(matched) == 1
        assert matched[0] == themes[0]

    def test_no_match_returns_empty(self) -> None:
        themes = ("Deforestation and biodiversity loss",)
        text = "tax compliance and board diversity are the main concerns"
        matched = _match_themes(themes, text)
        assert matched == []

    def test_multiple_themes(self) -> None:
        themes = (
            "Water stress and depletion",
            "Child and forced labour",
            "Greenhouse gas emissions",
        )
        text = "water stress is significant; child labour was identified in supply chains"
        matched = _match_themes(themes, text)
        assert len(matched) == 2

    def test_case_insensitive(self) -> None:
        themes = ("Pesticide and chemical use",)
        text = "PESTICIDE application was excessive"
        matched = _match_themes(themes, text)
        assert len(matched) == 1


# ── Full benchmark computation ────────────────────────────────────────────────

class TestComputeBenchmark:
    def test_benchmark_returns_correct_type(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector()
        findings = [_make_finding("Critical"), _make_finding("High", id="f2")]
        risks = [_make_risk("High")]
        result = compute_benchmark(assessment, sector, findings, risks, 0.70, [])
        assert isinstance(result, SectorBenchmark)

    def test_benchmark_sector_profile_used(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector(nace_code="B05")  # Mining
        result = compute_benchmark(assessment, sector, [], [], None, [])
        assert result.profile_nace_section == "B"
        assert result.overall_sector_risk == "Critical"

    def test_benchmark_without_sector(self) -> None:
        assessment = _make_assessment(sector_id=None)
        result = compute_benchmark(assessment, None, [], [], None, [])
        assert result.sector_id is None
        assert result.profile_nace_section == "*"

    def test_finding_distribution_counted(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector()
        findings = [
            _make_finding("Critical"),
            _make_finding("High", id="f2"),
            _make_finding("Medium", id="f3"),
        ]
        result = compute_benchmark(assessment, sector, findings, [], None, [])
        assert result.finding_distribution.critical == 1
        assert result.finding_distribution.high == 1
        assert result.finding_distribution.medium == 1
        assert result.finding_distribution.total == 3

    def test_risk_distribution_counted(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector()
        risks = [_make_risk("Critical"), _make_risk("Low", id="r2")]
        result = compute_benchmark(assessment, sector, [], risks, None, [])
        assert result.risk_distribution.critical == 1
        assert result.risk_distribution.low == 1

    def test_mandatory_coverage_stored(self) -> None:
        assessment = _make_assessment()
        result = compute_benchmark(assessment, None, [], [], 0.55, [])
        assert result.mandatory_coverage == pytest.approx(0.55)

    def test_coverage_vs_baseline_computed(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector(nace_code="C10")  # Manufacturing, baseline 0.55
        result = compute_benchmark(assessment, sector, [], [], 0.65, [])
        assert result.coverage_vs_baseline == pytest.approx(0.65 - 0.55, abs=0.01)

    def test_coverage_vs_baseline_none_when_no_coverage(self) -> None:
        assessment = _make_assessment()
        result = compute_benchmark(assessment, None, [], [], None, [])
        assert result.coverage_vs_baseline is None

    def test_themes_identified_from_finding_text(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector(nace_code="B")
        findings = [
            _make_finding(
                description="Child labour was identified in artisanal mining."
            )
        ]
        result = compute_benchmark(assessment, sector, findings, [], None, [])
        # "Child and forced labour in supply chains" should match via "Child" keyword
        assert len(result.key_themes_identified) >= 1

    def test_no_peers_gives_zero_peer_count(self) -> None:
        assessment = _make_assessment()
        result = compute_benchmark(assessment, None, [], [], None, [])
        assert result.peer_count == 0
        assert result.peers == []
        assert result.org_avg_quality_score is None

    def test_with_peers(self) -> None:
        assessment = _make_assessment()
        peer = _make_assessment(id="peer-1", title="Peer Assessment", quality_score=0.50)
        peer_findings = [_make_finding("High", id="pf1")]
        result = compute_benchmark(assessment, None, [], [], None, [(peer, peer_findings)])
        assert result.peer_count == 1
        assert result.org_avg_quality_score == pytest.approx(0.50)
        assert result.org_avg_finding_count == pytest.approx(1.0)

    def test_benchmark_rating_is_valid(self) -> None:
        assessment = _make_assessment()
        result = compute_benchmark(assessment, None, [], [], None, [])
        assert result.benchmark_rating in (
            "above_sector_baseline",
            "meets_sector_baseline",
            "below_sector_baseline",
        )

    def test_high_coverage_many_findings_rates_above_baseline(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector(nace_code="C")  # Manufacturing, min 3 findings
        findings = [
            _make_finding("Critical", id=f"f{i}") for i in range(6)
        ]
        # High coverage + many findings -> above or meets baseline
        result = compute_benchmark(assessment, sector, findings, [], 0.70, [])
        assert result.benchmark_rating in ("above_sector_baseline", "meets_sector_baseline")

    def test_no_findings_no_coverage_rates_below_baseline(self) -> None:
        assessment = _make_assessment(quality_score=0.10)
        sector = _make_sector(nace_code="B")  # Mining, min 4 findings, high baseline
        result = compute_benchmark(assessment, sector, [], [], 0.10, [])
        assert result.benchmark_rating == "below_sector_baseline"

    def test_benchmark_explanation_is_non_empty(self) -> None:
        assessment = _make_assessment()
        result = compute_benchmark(assessment, None, [], [], None, [])
        assert len(result.benchmark_explanation) > 20

    def test_key_themes_not_addressed_populated(self) -> None:
        assessment = _make_assessment(description="generic assessment", scope="")
        sector = _make_sector(nace_code="B")
        # No mention of any themes in the text -> all should be missed
        result = compute_benchmark(assessment, sector, [], [], None, [])
        assert len(result.key_themes_not_addressed) > 0

    def test_all_themes_addressable(self) -> None:
        assessment = _make_assessment()
        sector = _make_sector(nace_code="B")
        profile = get_profile("B")
        assert len(profile.key_risk_themes) > 0
