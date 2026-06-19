"""Unit tests for M33 Copilot Intent Detector."""

from __future__ import annotations

import pytest

from application.copilot.intent_detector import detect_intent
from domain.enums import CopilotIntentType


class TestIntentDetector:
    def test_risk_question(self):
        assert detect_intent("What are our biggest supplier risks?") == CopilotIntentType.RISK

    def test_risk_deteriorating(self):
        assert detect_intent("Which suppliers are deteriorating?") == CopilotIntentType.RISK

    def test_compliance_question(self):
        assert detect_intent("Which CSRD requirements are uncovered?") == CopilotIntentType.COMPLIANCE

    def test_compliance_gap(self):
        assert detect_intent("What compliance gaps are most severe?") == CopilotIntentType.COMPLIANCE

    def test_disclosure_question(self):
        intent = detect_intent("Which disclosures are weakest?")
        assert intent == CopilotIntentType.DISCLOSURE

    def test_due_diligence_lksgg(self):
        assert detect_intent("Which suppliers create LkSG exposure?") == CopilotIntentType.DUE_DILIGENCE

    def test_due_diligence_csddd(self):
        assert detect_intent("What CSDDD requirements are we missing?") == CopilotIntentType.DUE_DILIGENCE

    def test_due_diligence_supply_chain(self):
        assert detect_intent("Explain our supply chain risks") == CopilotIntentType.DUE_DILIGENCE

    def test_executive_board(self):
        intent = detect_intent("What should the board focus on?")
        assert intent == CopilotIntentType.EXECUTIVE

    def test_executive_changed(self):
        intent = detect_intent("What changed since last month?")
        assert intent == CopilotIntentType.EXECUTIVE

    def test_action_question(self):
        intent = detect_intent("Which actions reduce risk fastest?")
        assert intent == CopilotIntentType.ACTION

    def test_action_next_steps(self):
        intent = detect_intent("What should we do next?")
        assert intent == CopilotIntentType.ACTION

    def test_general_fallback(self):
        assert detect_intent("hello world") == CopilotIntentType.GENERAL

    def test_empty_string_fallback(self):
        assert detect_intent("") == CopilotIntentType.GENERAL

    def test_case_insensitive(self):
        assert detect_intent("WHAT ARE OUR BIGGEST RISKS?") == CopilotIntentType.RISK

    def test_due_diligence_beats_risk_when_specific(self):
        # "human rights" is a DD keyword with higher weight
        intent = detect_intent("Show human rights findings")
        assert intent == CopilotIntentType.DUE_DILIGENCE
