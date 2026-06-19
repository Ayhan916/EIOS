"""Unit tests for compliance gap analysis and verdict engine (M10)."""

from __future__ import annotations

from application.compliance.coverage import compute_coverage
from application.compliance.gaps import compute_gaps
from application.compliance.verdict import compute_verdict
from application.compliance.weights import exposure

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EMPTY_TEXTS = [""]

RICH_TEXT = """
This assessment covers identification of adverse impacts (CSDDD Art. 6),
prevention and mitigation measures (CSDDD Art. 7, LkSG § 5),
grievance mechanisms (CSDDD Art. 10, LkSG § 7),
climate change risks (ESRS E1, GHG emissions Scope 3),
forced labour screening (GRI 409, ESRS S2),
child labour due diligence (GRI 408, CSDDD Art. 6).
"""

# Comprehensive text covering >50% of mandatory articles (required for "partial" verdict).
# Updated for M31: includes CSRD, ESRS, EU Taxonomy, and ISSB coverage.
COMPREHENSIVE_TEXT = """
Due diligence policy (CSDDD Art. 5) integrated into corporate governance.
Identification of adverse impacts (CSDDD Art. 6) across Tier 1 and Tier 2 supply chain.
Prevention and mitigation (CSDDD Art. 7) with contractual supplier commitments.
Bringing actual adverse impacts to an end (CSDDD Art. 8) via corrective action plans.
Remediation for affected stakeholders (CSDDD Art. 9) — compensation funds established.
Grievance mechanism (CSDDD Art. 10, LkSG § 7) with multilingual hotline.
Monitoring effectiveness of due diligence (CSDDD Art. 11) — annual KPI review.
Communication and public reporting (CSDDD Art. 12) on company website.
Directors duty of care for sustainability (CSDDD Art. 22) — board sustainability committee.
Due diligence obligations (LkSG § 3) — Human Rights Officer appointed.
Risk analysis (LkSG § 4) conducted for all direct suppliers — Risikoanalyse completed.
Preventive measures (LkSG § 5) implemented — Präventionsmaßnahmen documented.
Remediation measures (LkSG § 6) — Abhilfemaßnahmen for confirmed violations.
Documentation and reporting obligations (LkSG § 8) — BAFA report submitted.
ESRS E1 climate change — GHG emissions Scope 3 disclosed; net zero target set.
ESRS E2 pollution — hazardous substances inventory completed.
Own workforce (ESRS S1) — working conditions and labour rights assessed.
Value chain workers (ESRS S2) — supply chain workers screening completed.
Business conduct and anti-corruption (ESRS G1) — whistleblower channel active.
CSRD sustainability reporting — CSRD Art. 19a disclosures prepared; double materiality assessment completed.
EU Taxonomy alignment — climate change mitigation activities screened; DNSH assessment performed; minimum social safeguards verified.
IFRS S1 general sustainability disclosures — sustainability KPIs and sustainability strategy disclosed.
IFRS S2 climate-related financial disclosures — climate transition plan prepared; Scope 1 2 3 ISSB emissions measured.
EU taxonomy adaptation — climate resilience assessed and physical risk addressed.
"""

# Covers nothing — all articles should be gaps
BLANK_COVERAGE = compute_coverage(EMPTY_TEXTS)

# Covers several key articles
RICH_COVERAGE = compute_coverage([RICH_TEXT])

# Covers >50% mandatory articles (partial or compliant verdict)
COMPREHENSIVE_COVERAGE = compute_coverage([COMPREHENSIVE_TEXT])


# ---------------------------------------------------------------------------
# Weights tests
# ---------------------------------------------------------------------------


class TestRegulatorExposureWeights:
    def test_all_articles_have_weight(self) -> None:
        from application.compliance.frameworks import ALL_ARTICLES

        for article in ALL_ARTICLES:
            w = exposure(article.code)
            assert 0.0 <= w <= 1.0, f"{article.code} weight out of bounds"

    def test_csddd_core_obligations_are_highest_weight(self) -> None:
        assert exposure("CSDDD-Art-6") == 1.0
        assert exposure("CSDDD-Art-7") == 1.0
        assert exposure("LkSG-4") == 1.0

    def test_gri_recommended_articles_lower_than_mandatory(self) -> None:
        gri_308 = exposure("GRI-305")
        csddd_6 = exposure("CSDDD-Art-6")
        assert csddd_6 > gri_308

    def test_child_labour_articles_have_elevated_weight(self) -> None:
        assert exposure("GRI-408") >= 0.75
        assert exposure("GRI-409") >= 0.75

    def test_unknown_code_returns_default(self) -> None:
        w = exposure("UNKNOWN-XYZ")
        assert 0.0 <= w <= 1.0


# ---------------------------------------------------------------------------
# Gap computation tests
# ---------------------------------------------------------------------------


class TestComputeGaps:
    def test_blank_coverage_yields_mandatory_gaps(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        assert len(gaps) > 0
        assert all(g.obligation_type == "mandatory" for g in gaps)

    def test_gaps_are_sorted_by_exposure_descending(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        exposures = [g.regulatory_exposure for g in gaps]
        assert exposures == sorted(exposures, reverse=True)

    def test_gaps_have_severity_classification(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        for g in gaps:
            assert g.gap_severity in ("critical", "high", "medium")

    def test_critical_severity_requires_high_exposure(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        for g in gaps:
            if g.gap_severity == "critical":
                assert g.regulatory_exposure >= 0.90

    def test_gaps_have_non_empty_explanation(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        for g in gaps:
            assert g.explanation and len(g.explanation) > 20

    def test_gaps_have_non_empty_remediation_hint(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        for g in gaps:
            assert g.remediation_hint and len(g.remediation_hint) > 20

    def test_covered_articles_are_not_in_gaps(self) -> None:
        gaps = compute_gaps(RICH_COVERAGE)
        gap_codes = {g.article_code for g in gaps}
        covered_codes = set(RICH_COVERAGE.covered_article_codes)
        assert gap_codes.isdisjoint(covered_codes), "Covered articles should not appear as gaps"

    def test_rich_coverage_has_fewer_gaps_than_blank(self) -> None:
        blank_gaps = compute_gaps(BLANK_COVERAGE)
        rich_gaps = compute_gaps(RICH_COVERAGE)
        assert len(rich_gaps) < len(blank_gaps)

    def test_include_recommended_adds_high_exposure_gri(self) -> None:
        gaps_mandatory_only = compute_gaps(BLANK_COVERAGE, include_recommended=False)
        gaps_with_recommended = compute_gaps(BLANK_COVERAGE, include_recommended=True)
        assert len(gaps_with_recommended) > len(gaps_mandatory_only)

    def test_csddd_art6_is_critical_gap_in_blank(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        art6 = next((g for g in gaps if g.article_code == "CSDDD-Art-6"), None)
        assert art6 is not None
        assert art6.gap_severity == "critical"
        assert art6.regulatory_exposure == 1.0

    def test_lksg_4_is_critical_gap_in_blank(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        lksg4 = next((g for g in gaps if g.article_code == "LkSG-4"), None)
        assert lksg4 is not None
        assert lksg4.gap_severity == "critical"

    def test_gap_esg_categories_are_populated(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        for g in gaps:
            assert len(g.esg_categories) > 0


# ---------------------------------------------------------------------------
# Verdict computation tests
# ---------------------------------------------------------------------------


class TestComputeVerdict:
    def test_blank_coverage_yields_non_compliant(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert verdict.status == "non_compliant"

    def test_comprehensive_coverage_yields_partial_or_compliant(self) -> None:
        gaps = compute_gaps(COMPREHENSIVE_COVERAGE)
        verdict = compute_verdict(COMPREHENSIVE_COVERAGE, gaps)
        assert verdict.status in ("partial", "compliant")

    def test_verdict_has_explanation(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert verdict.explanation and len(verdict.explanation) > 10

    def test_verdict_explanation_mentions_status(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert any(
            kw in verdict.explanation.lower() for kw in ("non-compliant", "compliant", "partial")
        )

    def test_mandatory_coverage_ratio_matches_coverage_report(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert verdict.mandatory_coverage_ratio == BLANK_COVERAGE.mandatory_coverage_ratio

    def test_critical_gap_count_matches_gap_list(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        expected_critical = sum(
            1 for g in gaps if g.gap_severity == "critical" and g.obligation_type == "mandatory"
        )
        assert verdict.critical_gap_count == expected_critical

    def test_weighted_gap_score_bounded(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert 0.0 <= verdict.weighted_gap_score <= 1.0

    def test_top_gap_codes_are_subset_of_gap_codes(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        all_gap_codes = {g.article_code for g in gaps}
        for code in verdict.top_gap_codes:
            assert code in all_gap_codes

    def test_top_gap_codes_max_three(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert len(verdict.top_gap_codes) <= 3

    def test_covered_mandatory_count_is_zero_for_blank(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert verdict.covered_mandatory_count == 0

    def test_compliant_status_requires_no_critical_gaps(self) -> None:
        # A compliant verdict must have 0 critical gaps
        gaps = compute_gaps(RICH_COVERAGE)
        verdict = compute_verdict(RICH_COVERAGE, gaps)
        if verdict.status == "compliant":
            assert verdict.critical_gap_count == 0

    def test_total_mandatory_articles_is_positive(self) -> None:
        gaps = compute_gaps(BLANK_COVERAGE)
        verdict = compute_verdict(BLANK_COVERAGE, gaps)
        assert verdict.total_mandatory_articles > 0
