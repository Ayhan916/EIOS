"""Unit tests for the Compliance Intelligence Engine (M9)."""

from __future__ import annotations

import pytest

from application.compliance.coverage import ArticleCoverage, FrameworkCoverage, compute_coverage
from application.compliance.frameworks import (
    ALL_ARTICLES,
    all_frameworks,
    get_article,
    get_by_framework,
)
from application.compliance.scoring import compute_quality_score


# ---------------------------------------------------------------------------
# Framework catalog tests
# ---------------------------------------------------------------------------

class TestFrameworkCatalog:
    def test_all_articles_have_required_fields(self) -> None:
        for article in ALL_ARTICLES:
            assert article.code
            assert article.framework
            assert article.title
            assert article.obligation_type in ("mandatory", "recommended")
            assert len(article.keywords) > 0

    def test_all_frameworks_present(self) -> None:
        frameworks = all_frameworks()
        assert "CSDDD" in frameworks
        assert "LkSG" in frameworks
        assert "ESRS" in frameworks
        assert "GRI" in frameworks

    def test_get_article_by_code(self) -> None:
        article = get_article("CSDDD-Art-6")
        assert article is not None
        assert article.title == "Identification of actual and potential adverse impacts"

    def test_get_article_unknown_code_returns_none(self) -> None:
        assert get_article("DOES-NOT-EXIST") is None

    def test_get_by_framework_csddd(self) -> None:
        articles = get_by_framework("CSDDD")
        assert len(articles) >= 9
        assert all(a.framework == "CSDDD" for a in articles)

    def test_get_by_framework_case_insensitive(self) -> None:
        assert get_by_framework("csddd") == get_by_framework("CSDDD")

    def test_mandatory_articles_exist_in_csddd_lksg_esrs(self) -> None:
        for fw in ("CSDDD", "LkSG", "ESRS"):
            mandatory = [a for a in get_by_framework(fw) if a.obligation_type == "mandatory"]
            assert len(mandatory) > 0, f"{fw} should have mandatory articles"

    def test_gri_articles_are_recommended(self) -> None:
        gri = get_by_framework("GRI")
        assert all(a.obligation_type == "recommended" for a in gri)

    def test_unique_codes_across_all_articles(self) -> None:
        codes = [a.code for a in ALL_ARTICLES]
        assert len(codes) == len(set(codes)), "Duplicate article codes found"


# ---------------------------------------------------------------------------
# Coverage computation tests
# ---------------------------------------------------------------------------

RICH_TEXT = """
This assessment covers climate change impacts (ESRS E1), GHG emissions including Scope 3,
and water-related risks per CSRD E3 (ESRS E3). Supply chain workers face forced labour
risks assessed against ESRS S2 and GRI 409. The company has implemented grievance
mechanisms as required by CSDDD Art. 10 and LkSG § 7.
Child labour screening covers GRI 408 and CSDDD Art. 6 obligations.
Preventive measures per CSDDD Art. 7 and LkSG § 5 are in place.
The board's duty of care (CSDDD Art. 22) was reviewed. Due diligence policy (CSDDD Art. 5).
"""

EMPTY_TEXT = ""
IRRELEVANT_TEXT = "This is a report about financial performance and quarterly earnings."


class TestCoverageComputation:
    def test_empty_texts_returns_zero_coverage(self) -> None:
        report = compute_coverage([EMPTY_TEXT])
        assert report.overall_coverage_ratio == 0.0
        assert report.mandatory_coverage_ratio == 0.0
        assert len(report.covered_article_codes) == 0

    def test_irrelevant_text_has_low_coverage(self) -> None:
        report = compute_coverage([IRRELEVANT_TEXT])
        assert report.overall_coverage_ratio < 0.1

    def test_rich_text_covers_multiple_frameworks(self) -> None:
        report = compute_coverage([RICH_TEXT])
        covered_frameworks = {fc.framework for fc in report.framework_coverage if fc.covered_count > 0}
        assert "CSDDD" in covered_frameworks
        assert "ESRS" in covered_frameworks
        assert "GRI" in covered_frameworks

    def test_rich_text_covered_codes_include_expected_articles(self) -> None:
        report = compute_coverage([RICH_TEXT])
        codes = set(report.covered_article_codes)
        assert "CSDDD-Art-5" in codes
        assert "CSDDD-Art-6" in codes
        assert "ESRS-E1" in codes
        assert "GRI-408" in codes

    def test_coverage_ratios_are_bounded(self) -> None:
        report = compute_coverage([RICH_TEXT])
        assert 0.0 <= report.overall_coverage_ratio <= 1.0
        assert 0.0 <= report.mandatory_coverage_ratio <= 1.0

    def test_framework_coverage_items_match_all_frameworks(self) -> None:
        report = compute_coverage([RICH_TEXT])
        fw_names = {fc.framework for fc in report.framework_coverage}
        assert fw_names == set(all_frameworks())

    def test_multiple_texts_are_combined(self) -> None:
        text_a = "ESRS E1 climate change and GHG emissions Scope 3 coverage."
        text_b = "CSDDD Art. 6 identification of adverse impacts."
        report_combined = compute_coverage([text_a, text_b])
        report_single_a = compute_coverage([text_a])
        assert report_combined.overall_coverage_ratio >= report_single_a.overall_coverage_ratio

    def test_framework_coverage_ratio_per_framework(self) -> None:
        report = compute_coverage([RICH_TEXT])
        csddd = next(fc for fc in report.framework_coverage if fc.framework == "CSDDD")
        assert csddd.covered_count > 0
        assert csddd.coverage_ratio == csddd.covered_count / csddd.total_articles

    def test_article_level_covered_flag(self) -> None:
        report = compute_coverage(["CSDDD Art. 6 adverse impact identification"])
        csddd = next(fc for fc in report.framework_coverage if fc.framework == "CSDDD")
        art6 = next(ac for ac in csddd.articles if ac.code == "CSDDD-Art-6")
        assert art6.covered is True


# ---------------------------------------------------------------------------
# Quality scoring tests
# ---------------------------------------------------------------------------

class TestQualityScoring:
    def _zero_coverage(self):
        from application.compliance.coverage import ComplianceCoverageReport, FrameworkCoverage
        return ComplianceCoverageReport(
            covered_article_codes=[],
            framework_coverage=[],
            overall_coverage_ratio=0.0,
            mandatory_coverage_ratio=0.0,
        )

    def _full_coverage(self):
        return compute_coverage([RICH_TEXT])

    def test_no_entities_no_coverage_is_zero(self) -> None:
        score = compute_quality_score(0, 0, 0, self._zero_coverage())
        assert score == 0.0

    def test_full_entities_full_coverage_approaches_one(self) -> None:
        coverage = self._full_coverage()
        score = compute_quality_score(5, 4, 5, coverage)
        assert score > 0.4

    def test_insufficient_evidence_verdict_caps_score(self) -> None:
        coverage = self._full_coverage()
        score = compute_quality_score(5, 4, 5, coverage, verdict="insufficient_evidence")
        assert score <= 0.30

    def test_score_increases_with_more_findings(self) -> None:
        cov = self._zero_coverage()
        score_low = compute_quality_score(1, 0, 0, cov)
        score_high = compute_quality_score(5, 0, 0, cov)
        assert score_high > score_low

    def test_score_is_bounded_0_to_1(self) -> None:
        cov = self._full_coverage()
        score = compute_quality_score(100, 100, 100, cov)
        assert 0.0 <= score <= 1.0

    def test_score_has_4_decimal_precision(self) -> None:
        cov = self._zero_coverage()
        score = compute_quality_score(2, 1, 1, cov)
        assert score == round(score, 4)

    def test_pass_verdict_does_not_cap_score(self) -> None:
        coverage = self._full_coverage()
        score_pass = compute_quality_score(5, 4, 5, coverage, verdict="pass")
        score_no_verdict = compute_quality_score(5, 4, 5, coverage, verdict=None)
        assert score_pass == score_no_verdict
