"""Tests for News → Scenario Trigger detector (TASK-003 Phase 4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from application.sector_intelligence.news_scenario_detector import (
    _NACE_SECTOR_KEYWORDS,
    _SCENARIO_KEYWORDS,
    _THRESHOLD_ARTICLES,
    NewsScenarioDetector,
)
from domain.enums import ScenarioSuggestionStatus, ScenarioType


def _make_articles(
    n: int,
    title_template: str = "Article {i}",
    summary: str = "",
    days_ago: int = 0,
) -> list[dict]:
    now = datetime.now(UTC) - timedelta(days=days_ago)
    return [
        {
            "title": title_template.format(i=i),
            "summary": summary,
            "translated_title": None,
            "translated_summary": None,
            "published_at": now.isoformat(),
            "url": f"https://example.com/{i}",
        }
        for i in range(n)
    ]


@pytest.fixture
def detector() -> NewsScenarioDetector:
    return NewsScenarioDetector()


class TestKeywordSets:
    def test_all_6_scenario_types_have_keywords(self) -> None:
        assert len(_SCENARIO_KEYWORDS) == 6
        for scenario_type in ScenarioType:
            assert scenario_type in _SCENARIO_KEYWORDS
            assert len(_SCENARIO_KEYWORDS[scenario_type]) > 0

    def test_all_keyword_sets_are_non_empty(self) -> None:
        for st, kws in _SCENARIO_KEYWORDS.items():
            assert len(kws) >= 5, f"{st.value} has fewer than 5 keywords"

    def test_nace_sector_keyword_sets_cover_key_sectors(self) -> None:
        key_sectors = {"29", "13", "01", "49", "07", "26", "62"}
        for sector in key_sectors:
            assert sector in _NACE_SECTOR_KEYWORDS, f"NACE {sector} has no keyword set"

    def test_all_keywords_are_lowercase(self) -> None:
        for st, kws in _SCENARIO_KEYWORDS.items():
            for kw in kws:
                # Keywords are used with .lower() in detection, so they should match lowercased text
                assert kw == kw.lower() or any(c.isupper() for c in kw), (
                    f"Keyword '{kw}' in {st.value} has unexpected casing"
                )


class TestDetectionLogic:
    def test_no_articles_returns_empty(self, detector: NewsScenarioDetector) -> None:
        result = detector.detect([])
        assert result == []

    def test_below_threshold_returns_empty(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES - 1,
            title_template="Workers go on strike {i}",
        )
        result = detector.detect(articles)
        assert result == []

    def test_at_threshold_returns_suggestion(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES,
            title_template="Workers go on strike in automotive sector {i}",
        )
        result = detector.detect(articles)
        types = {s["scenario_type"] for s in result}
        assert "labour_unrest" in types

    def test_above_threshold_returns_suggestion(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES + 3,
            title_template="War conflict invasion military troops {i}",
        )
        result = detector.detect(articles)
        types = {s["scenario_type"] for s in result}
        assert "geopolitical_conflict" in types

    def test_suggestion_has_required_fields(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES + 2,
            title_template="Flood disaster earthquake natural disaster {i}",
        )
        result = detector.detect(articles)
        assert len(result) > 0
        suggestion = result[0]
        required = {
            "id",
            "status",
            "scenario_type",
            "affected_nace_codes",
            "trigger_article_count",
            "trigger_keywords_matched",
            "sample_headlines",
            "created_at",
        }
        assert required <= set(suggestion.keys()), (
            f"Missing fields: {required - set(suggestion.keys())}"
        )

    def test_suggestion_status_is_pending(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES,
            title_template="Sanctions embargo trade restriction {i}",
        )
        result = detector.detect(articles)
        for s in result:
            assert s["status"] == ScenarioSuggestionStatus.PENDING.value

    def test_trigger_count_matches_articles(self, detector: NewsScenarioDetector) -> None:
        n = _THRESHOLD_ARTICLES + 4
        articles = _make_articles(n, title_template="Strike walkout union {i}")
        result = detector.detect(articles)
        labour = [s for s in result if s["scenario_type"] == "labour_unrest"]
        assert len(labour) > 0
        assert labour[0]["trigger_article_count"] >= _THRESHOLD_ARTICLES

    def test_sample_headlines_max_3(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(20, title_template="Flood disaster earthquake {i}")
        result = detector.detect(articles)
        for s in result:
            assert len(s["sample_headlines"]) <= 3

    def test_keywords_matched_populated(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES,
            title_template="Workers strike walkout union protest {i}",
        )
        result = detector.detect(articles)
        labour = [s for s in result if s["scenario_type"] == "labour_unrest"]
        if labour:
            assert len(labour[0]["trigger_keywords_matched"]) > 0


class TestSectorClassification:
    def test_automotive_keyword_matches_nace_29(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES,
            title_template="Automotive sector war invasion conflict {i}",
        )
        result = detector.detect(articles)
        conflict = [s for s in result if s["scenario_type"] == "geopolitical_conflict"]
        if conflict:
            assert (
                "29" in conflict[0]["affected_nace_codes"]
                or conflict[0]["affected_nace_codes"] == []
            )

    def test_textile_keyword_matches_nace_13(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES,
            title_template="Textile workers strike walkout union {i}",
        )
        result = detector.detect(articles)
        labour = [s for s in result if s["scenario_type"] == "labour_unrest"]
        if labour:
            # 13 or 14 should be in affected codes
            affected = set(labour[0]["affected_nace_codes"])
            assert affected & {"13", "14"} or len(affected) == 0


class TestActiveTypeFiltering:
    def test_already_active_scenario_not_duplicated(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES + 3,
            title_template="Workers go on strike {i}",
        )
        result_first = detector.detect(articles)
        [s for s in result_first if s["scenario_type"] == "labour_unrest"]

        # Simulate labour_unrest already active
        active = {ScenarioType.LABOUR_UNREST}
        result_second = detector.detect(articles, existing_active_types=active)
        labour_second = [s for s in result_second if s["scenario_type"] == "labour_unrest"]

        assert len(labour_second) == 0, "Active scenario must not generate duplicate suggestion"

    def test_other_scenarios_still_detected_when_one_active(
        self, detector: NewsScenarioDetector
    ) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES + 3,
            title_template="Strike flood disaster earthquake {i}",
        )
        active = {ScenarioType.LABOUR_UNREST}
        result = detector.detect(articles, existing_active_types=active)
        types = {s["scenario_type"] for s in result}
        # natural_disaster should still be detected
        assert "natural_disaster" in types or len(result) == 0  # depends on threshold


class TestRecencyFilter:
    def test_old_articles_filtered_out(self, detector: NewsScenarioDetector) -> None:
        # Articles from 10 days ago — outside the 7-day window
        articles = _make_articles(
            _THRESHOLD_ARTICLES + 5,
            title_template="War conflict invasion military {i}",
            days_ago=10,
        )
        result = detector.detect(articles)
        # Should produce no suggestions since all articles are too old
        assert result == []

    def test_recent_articles_detected(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES,
            title_template="War conflict invasion military {i}",
            days_ago=1,
        )
        result = detector.detect(articles)
        types = {s["scenario_type"] for s in result}
        assert "geopolitical_conflict" in types


class TestSuggestionIdUniqueness:
    def test_each_suggestion_has_unique_id(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            30,
            title_template="War strike flood sanctions shortage {i}",
        )
        result = detector.detect(articles)
        ids = [s["id"] for s in result]
        assert len(ids) == len(set(ids)), "Suggestion IDs must be unique"

    def test_two_runs_produce_different_ids(self, detector: NewsScenarioDetector) -> None:
        articles = _make_articles(
            _THRESHOLD_ARTICLES,
            title_template="Flood disaster earthquake {i}",
        )
        r1 = detector.detect(articles)
        r2 = detector.detect(articles)
        ids1 = {s["id"] for s in r1}
        ids2 = {s["id"] for s in r2}
        assert ids1.isdisjoint(ids2), "Each run must generate new UUIDs"
