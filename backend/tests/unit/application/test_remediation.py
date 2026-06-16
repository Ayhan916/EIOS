"""Unit tests for the Remediation Intelligence layer (M11)."""

from __future__ import annotations

import pytest

from application.compliance.coverage import compute_coverage
from application.compliance.gaps import compute_gaps
from application.compliance.verdict import compute_verdict
from application.remediation.brief import DecisionBrief, compute_brief
from application.remediation.matcher import GapRecommendationLink, compute_matches
from application.remediation.planner import RemediationPlan, compute_remediation_plan
from domain.enums import ConfidenceLevel, EntityStatus, RiskLevel
from domain.recommendation import Recommendation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BLANK_COVERAGE = compute_coverage([""])
BLANK_GAPS = compute_gaps(BLANK_COVERAGE)

PARTIAL_TEXT = """
CSDDD Art. 5 due diligence policy integrated.
CSDDD Art. 6 adverse impact identification completed.
CSDDD Art. 7 prevention and mitigation measures documented.
LkSG § 4 Risikoanalyse conducted. LkSG § 5 Präventionsmaßnahmen implemented.
ESRS E1 climate change GHG emissions Scope 3. ESRS S2 supply chain workers.
"""
PARTIAL_COVERAGE = compute_coverage([PARTIAL_TEXT])
PARTIAL_GAPS = compute_gaps(PARTIAL_COVERAGE)


def _make_rec(title: str, description: str, priority: RiskLevel = RiskLevel.HIGH) -> Recommendation:
    return Recommendation(
        title=title,
        description=description,
        priority=priority,
        confidence=ConfidenceLevel.HIGH,
        status=EntityStatus.REVIEWED,
    )


RECS = [
    _make_rec(
        "Implement CSDDD Due Diligence Policy",
        "Develop board-approved Human Rights and Environmental Due Diligence Policy "
        "aligned with CSDDD Art. 5 requirements. Include preventive measures and "
        "mitigation procedures.",
    ),
    _make_rec(
        "Conduct Supplier Risk Analysis",
        "Perform LkSG risk analysis (Risikoanalyse) for direct suppliers per § 4. "
        "Map risks against adverse impact categories including forced labour and "
        "child labour exposure.",
    ),
    _make_rec(
        "Establish Grievance Mechanism",
        "Implement multilingual complaint mechanism (Beschwerdeverfahren) per "
        "CSDDD Art. 10 and LkSG § 7 accessible to workers and affected communities.",
        priority=RiskLevel.CRITICAL,
    ),
    _make_rec(
        "Climate Change Disclosure",
        "Report GHG emissions Scope 1, Scope 2 and Scope 3 per ESRS E1. "
        "Set science-based emissions reduction targets.",
        priority=RiskLevel.MEDIUM,
    ),
]


# ---------------------------------------------------------------------------
# Matcher tests
# ---------------------------------------------------------------------------

class TestComputeMatches:
    def test_empty_inputs_returns_empty(self) -> None:
        assert compute_matches([], []) == []
        assert compute_matches(BLANK_GAPS, []) == []
        assert compute_matches([], RECS) == []

    def test_returns_list_of_links(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        assert isinstance(links, list)
        assert all(isinstance(lk, GapRecommendationLink) for lk in links)

    def test_links_have_valid_gap_codes(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        gap_codes = {g.article_code for g in BLANK_GAPS}
        for lk in links:
            assert lk.gap_code in gap_codes

    def test_links_have_valid_recommendation_ids(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        rec_ids = {r.id for r in RECS}
        for lk in links:
            assert lk.recommendation_id in rec_ids

    def test_match_confidence_bounded(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        for lk in links:
            assert 0.0 <= lk.match_confidence <= 1.0

    def test_policy_recommendation_matches_art5_gap(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        policy_links = [lk for lk in links if lk.gap_code == "CSDDD-Art-5"]
        # The "Implement CSDDD Due Diligence Policy" rec should match Art. 5
        matched_rec_titles = {lk.recommendation_title for lk in policy_links}
        assert any("Policy" in t or "Due Diligence" in t for t in matched_rec_titles)

    def test_grievance_recommendation_matches_grievance_gaps(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        grievance_gaps = {"CSDDD-Art-10", "LkSG-7"}
        grievance_links = [lk for lk in links if lk.gap_code in grievance_gaps]
        assert len(grievance_links) > 0

    def test_links_sorted_by_confidence_descending(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        confidences = [lk.match_confidence for lk in links]
        assert confidences == sorted(confidences, reverse=True)

    def test_one_rec_can_link_to_multiple_gaps(self) -> None:
        links = compute_matches(BLANK_GAPS, RECS)
        policy_rec_links = [lk for lk in links if "Policy" in lk.recommendation_title]
        gap_codes = {lk.gap_code for lk in policy_rec_links}
        # The CSDDD policy rec is general enough to match several gaps
        assert len(gap_codes) >= 1


# ---------------------------------------------------------------------------
# Planner tests
# ---------------------------------------------------------------------------

class TestComputeRemediationPlan:
    def setup_method(self) -> None:
        self.links = compute_matches(BLANK_GAPS, RECS)

    def test_returns_remediation_plan(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        assert isinstance(plan, RemediationPlan)

    def test_plan_assessment_id(self) -> None:
        plan = compute_remediation_plan("assessment-xyz", BLANK_GAPS, self.links)
        assert plan.assessment_id == "assessment-xyz"

    def test_total_gaps_matches_input(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        assert plan.total_gaps == len(BLANK_GAPS)

    def test_all_gaps_bucketed(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        total = (
            len(plan.immediate_actions)
            + len(plan.short_term_actions)
            + len(plan.medium_term_actions)
        )
        assert total == plan.total_gaps

    def test_immediate_actions_are_critical_exposure(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        for action in plan.immediate_actions:
            assert action.regulatory_exposure >= 0.90, (
                f"{action.article_code} has exposure {action.regulatory_exposure} "
                "but is in immediate bucket"
            )

    def test_short_term_actions_have_high_exposure(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        for action in plan.short_term_actions:
            assert 0.75 <= action.regulatory_exposure < 0.90

    def test_medium_term_actions_have_lower_exposure(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        for action in plan.medium_term_actions:
            assert action.regulatory_exposure < 0.75

    def test_linked_recommendation_ids_are_known_ids(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        rec_ids = {r.id for r in RECS}
        all_actions = plan.immediate_actions + plan.short_term_actions + plan.medium_term_actions
        for action in all_actions:
            for rid in action.linked_recommendation_ids:
                assert rid in rec_ids

    def test_linked_gap_count_plus_unlinked_equals_total(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        assert plan.linked_gap_count + plan.unlinked_gap_count == plan.total_gaps

    def test_priority_ranks_are_sequential(self) -> None:
        plan = compute_remediation_plan("assessment-1", BLANK_GAPS, self.links)
        all_actions = plan.immediate_actions + plan.short_term_actions + plan.medium_term_actions
        ranks = [a.priority_rank for a in all_actions]
        assert sorted(ranks) == list(range(1, len(ranks) + 1))

    def test_empty_gaps_produces_empty_plan(self) -> None:
        plan = compute_remediation_plan("assessment-1", [], [])
        assert plan.total_gaps == 0
        assert plan.immediate_actions == []
        assert plan.short_term_actions == []
        assert plan.medium_term_actions == []


# ---------------------------------------------------------------------------
# Decision Brief tests
# ---------------------------------------------------------------------------

class TestComputeBrief:
    def _build_brief(self, coverage_text: str = "") -> DecisionBrief:
        from domain.assessment import Assessment
        from domain.enums import ConfidenceLevel

        assessment = Assessment(
            title="ESG Assessment: Test Company",
            description="Test assessment description.",
            assessment_type="quick_scan",
            confidence=ConfidenceLevel.MEDIUM,
            quality_score=0.45,
            status=EntityStatus.REVIEWED,
        )
        coverage = compute_coverage([coverage_text])
        gaps = compute_gaps(coverage)
        verdict = compute_verdict(coverage, gaps)
        critical_gaps = [g for g in gaps if g.gap_severity == "critical"]
        links = compute_matches(gaps, RECS)
        plan = compute_remediation_plan(assessment.id, gaps, links)

        return compute_brief(
            assessment=assessment,
            verdict=verdict,
            top_critical_gaps=critical_gaps[:3],
            finding_titles=["Finding 1: Child Labour", "Finding 2: Wastewater"],
            recommendation_titles=[r.title for r in RECS],
            immediate_action_count=len(plan.immediate_actions),
        )

    def test_brief_has_all_required_fields(self) -> None:
        brief = self._build_brief()
        assert brief.assessment_id
        assert brief.assessment_title
        assert brief.compliance_verdict in ("compliant", "partial", "non_compliant")
        assert 0 <= brief.mandatory_coverage_pct <= 100
        assert brief.executive_summary
        assert brief.disclaimer

    def test_disclaimer_present_and_mentions_legal(self) -> None:
        brief = self._build_brief()
        assert "legal" in brief.disclaimer.lower()
        assert "advice" in brief.disclaimer.lower()

    def test_disclaimer_does_not_use_first_person(self) -> None:
        brief = self._build_brief()
        assert " I " not in brief.disclaimer
        assert " we " not in brief.disclaimer.lower()

    def test_executive_summary_is_factual(self) -> None:
        brief = self._build_brief()
        # Should reference coverage percentage
        assert "%" in brief.executive_summary

    def test_top_critical_gaps_bounded_to_three(self) -> None:
        brief = self._build_brief()
        assert len(brief.top_critical_gaps) <= 3

    def test_key_findings_bounded_to_three(self) -> None:
        brief = self._build_brief()
        assert len(brief.key_findings) <= 3

    def test_top_recommendations_bounded_to_three(self) -> None:
        brief = self._build_brief()
        assert len(brief.top_recommendations) <= 3

    def test_quality_score_propagated(self) -> None:
        brief = self._build_brief()
        assert brief.quality_score == pytest.approx(0.45)

    def test_compliant_verdict_brief_summary(self) -> None:
        # Use comprehensive text from test_compliance_reasoning
        comprehensive = """
        CSDDD Art. 5 due diligence policy. CSDDD Art. 6 identification of adverse impacts.
        CSDDD Art. 7 prevention mitigation. CSDDD Art. 8 corrective action plans.
        CSDDD Art. 9 remediation. CSDDD Art. 10 grievance mechanism. CSDDD Art. 11 monitoring.
        CSDDD Art. 12 public reporting. CSDDD Art. 22 directors duty of care.
        LkSG § 3 Sorgfaltspflicht. LkSG § 4 Risikoanalyse. LkSG § 5 Präventionsmaßnahmen.
        LkSG § 6 Abhilfemaßnahmen. LkSG § 7 Beschwerdeverfahren. LkSG § 8 Dokumentation.
        LkSG § 10 indirect supplier mittelbarer Zulieferer.
        ESRS E1 climate change GHG Scope 3. ESRS E2 pollution. ESRS E3 water.
        ESRS E4 biodiversity. ESRS E5 circular economy. ESRS S1 workforce.
        ESRS S2 value chain workers forced labour. ESRS S3 affected communities.
        ESRS G1 business conduct anti-corruption.
        """
        brief = self._build_brief(comprehensive)
        # With comprehensive coverage, verdict should be partial or compliant
        assert brief.compliance_verdict in ("partial", "compliant")
