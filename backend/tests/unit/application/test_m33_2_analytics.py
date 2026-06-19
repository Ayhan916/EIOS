"""M33.2 — Conversation Analytics Tests.

Tests the ConversationAnalytics dataclass and analytics response schema.
DB-level analytics is integration-tested via the mock session pattern.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.copilot.analytics_service import ConversationAnalytics, get_analytics
from interfaces.api.schemas.copilot_audit import AnalyticsResponse


class TestConversationAnalyticsDefaults:
    def test_defaults_to_zero(self):
        a = ConversationAnalytics(organization_id="org-1")
        assert a.total_questions == 0
        assert a.total_conversations == 0
        assert a.average_confidence_score == 0.0
        assert a.average_citations_per_answer == 0.0
        assert a.empty_context_count == 0
        assert a.empty_context_rate == 0.0
        assert a.contradiction_rate == 0.0
        assert a.feedback_total == 0

    def test_org_id_set(self):
        a = ConversationAnalytics(organization_id="org-42")
        assert a.organization_id == "org-42"

    def test_dict_fields_default_empty(self):
        a = ConversationAnalytics(organization_id="org-1")
        assert a.questions_by_intent == {}
        assert a.confidence_distribution == {}

    def test_feedback_counts_default_zero(self):
        a = ConversationAnalytics(organization_id="org-1")
        assert a.feedback_helpful_count == 0
        assert a.feedback_not_helpful_count == 0
        assert a.feedback_incorrect_count == 0
        assert a.feedback_outdated_count == 0


class TestAnalyticsResponse:
    def test_schema_accepts_valid_analytics(self):
        response = AnalyticsResponse(
            organization_id="org-1",
            total_questions=10,
            total_conversations=3,
            questions_by_intent={"supplier_risk": 5, "compliance": 5},
            average_confidence_score=3.2,
            confidence_distribution={"High": 5, "Moderate": 3, "Low": 2},
            average_citations_per_answer=2.5,
            empty_context_count=1,
            empty_context_rate=0.1,
            contradiction_rate=0.3,
            average_contradiction_count=0.5,
            feedback_helpful_count=7,
            feedback_not_helpful_count=1,
            feedback_incorrect_count=1,
            feedback_outdated_count=1,
            feedback_total=10,
        )
        assert response.total_questions == 10
        assert response.organization_id == "org-1"

    def test_schema_serializes_to_dict(self):
        response = AnalyticsResponse(
            organization_id="org-1",
            total_questions=5,
            total_conversations=2,
            questions_by_intent={},
            average_confidence_score=2.5,
            confidence_distribution={},
            average_citations_per_answer=1.0,
            empty_context_count=0,
            empty_context_rate=0.0,
            contradiction_rate=0.0,
            average_contradiction_count=0.0,
            feedback_helpful_count=0,
            feedback_not_helpful_count=0,
            feedback_incorrect_count=0,
            feedback_outdated_count=0,
            feedback_total=0,
        )
        d = response.model_dump()
        assert "organization_id" in d
        assert "total_questions" in d
        assert "questions_by_intent" in d


def _make_session_side_effect(
    conv_count: int = 2,
    user_rows: list | None = None,
    asst_rows: list | None = None,
    fb_rows: list | None = None,
) -> AsyncMock:
    """Build a session mock with predictable execute() return sequence."""
    if user_rows is None:
        ur = MagicMock()
        ur.intent = "supplier_risk"
        user_rows = [ur]
    if asst_rows is None:
        ar = MagicMock()
        ar.confidence_level = "High"
        ar.citations = [{"object_id": "s1"}]
        ar.model_used = "openai:gpt-4o"
        ar.contradiction_count = 0
        asst_rows = [ar]
    if fb_rows is None:
        fr = MagicMock()
        fr.rating = "helpful"
        fb_rows = [fr]

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv_count

    user_result = MagicMock()
    user_result.scalars.return_value.all.return_value = user_rows

    asst_result = MagicMock()
    asst_result.scalars.return_value.all.return_value = asst_rows

    fb_result = MagicMock()
    fb_result.scalars.return_value.all.return_value = fb_rows

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[conv_result, user_result, asst_result, fb_result])
    return session


class TestGetAnalytics:
    @pytest.mark.asyncio
    async def test_returns_analytics_for_org(self):
        session = _make_session_side_effect()
        result = await get_analytics("org-1", session)
        assert isinstance(result, ConversationAnalytics)
        assert result.organization_id == "org-1"
        assert result.total_conversations == 2
        assert result.total_questions == 1
        assert result.feedback_total == 1
        assert result.feedback_helpful_count == 1

    @pytest.mark.asyncio
    async def test_empty_org_returns_zero_analytics(self):
        session = _make_session_side_effect(
            conv_count=0, user_rows=[], asst_rows=[], fb_rows=[]
        )
        result = await get_analytics("empty-org", session)
        assert result.total_questions == 0
        assert result.total_conversations == 0
        assert result.feedback_total == 0
        assert result.average_confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_multiple_feedback_types_counted_correctly(self):
        def _fb(r: str):
            m = MagicMock()
            m.rating = r
            return m

        session = _make_session_side_effect(
            fb_rows=[_fb("helpful"), _fb("not_helpful"), _fb("incorrect"), _fb("outdated")]
        )
        result = await get_analytics("org-1", session)
        assert result.feedback_helpful_count == 1
        assert result.feedback_not_helpful_count == 1
        assert result.feedback_incorrect_count == 1
        assert result.feedback_outdated_count == 1
        assert result.feedback_total == 4

    @pytest.mark.asyncio
    async def test_intent_distribution_counted(self):
        def _user_row(intent: str):
            m = MagicMock()
            m.intent = intent
            return m

        session = _make_session_side_effect(
            user_rows=[
                _user_row("supplier_risk"),
                _user_row("supplier_risk"),
                _user_row("compliance"),
            ]
        )
        result = await get_analytics("org-1", session)
        assert result.questions_by_intent.get("supplier_risk") == 2
        assert result.questions_by_intent.get("compliance") == 1


class TestFeedbackCounting:
    def test_feedback_total_is_sum(self):
        a = ConversationAnalytics(
            organization_id="org-1",
            feedback_helpful_count=5,
            feedback_not_helpful_count=2,
            feedback_incorrect_count=1,
            feedback_outdated_count=1,
            feedback_total=9,
        )
        expected = 5 + 2 + 1 + 1
        assert a.feedback_total == expected

    def test_contradiction_rate_bounds(self):
        a = ConversationAnalytics(
            organization_id="org-1",
            contradiction_rate=0.5,
        )
        assert 0.0 <= a.contradiction_rate <= 1.0

    def test_empty_context_rate_bounds(self):
        a = ConversationAnalytics(
            organization_id="org-1",
            empty_context_rate=0.1,
        )
        assert 0.0 <= a.empty_context_rate <= 1.0
