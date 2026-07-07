"""Unit tests for M33 Suggested Questions."""

from __future__ import annotations

from application.copilot.suggested_questions import get_suggested_questions
from domain.enums import CopilotContextType


class TestSuggestedQuestions:
    def test_general_returns_questions(self):
        qs = get_suggested_questions(CopilotContextType.GENERAL)
        assert len(qs) >= 1
        assert all(isinstance(q, str) for q in qs)

    def test_supplier_context(self):
        qs = get_suggested_questions(CopilotContextType.SUPPLIER)
        assert len(qs) >= 1
        assert any("supplier" in q.lower() or "risk" in q.lower() for q in qs)

    def test_compliance_context(self):
        qs = get_suggested_questions(CopilotContextType.COMPLIANCE)
        assert len(qs) >= 1
        assert any(
            "compliance" in q.lower() or "gap" in q.lower() or "requirement" in q.lower()
            for q in qs
        )

    def test_disclosure_context(self):
        qs = get_suggested_questions(CopilotContextType.DISCLOSURE)
        assert len(qs) >= 1
        assert any("disclosure" in q.lower() for q in qs)

    def test_due_diligence_context(self):
        qs = get_suggested_questions(CopilotContextType.DUE_DILIGENCE)
        assert len(qs) >= 1

    def test_executive_context(self):
        qs = get_suggested_questions(CopilotContextType.EXECUTIVE)
        assert len(qs) >= 1
        assert any(
            "board" in q.lower()
            or "executive" in q.lower()
            or "changed" in q.lower()
            or "brief" in q.lower()
            or "summary" in q.lower()
            for q in qs
        )

    def test_limit_respected(self):
        qs = get_suggested_questions(CopilotContextType.GENERAL, limit=3)
        assert len(qs) <= 3

    def test_unknown_context_falls_back_to_general(self):
        qs = get_suggested_questions("unknown_type")
        assert len(qs) >= 1

    def test_returns_list_of_strings(self):
        qs = get_suggested_questions()
        assert isinstance(qs, list)
        for q in qs:
            assert isinstance(q, str)
            assert len(q) > 5
