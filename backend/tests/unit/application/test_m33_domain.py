"""Unit tests for M33 domain entities: CopilotConversation and CopilotMessage."""

from __future__ import annotations

from domain.copilot import CopilotConversation, CopilotMessage
from domain.enums import (
    CitationType,
    CopilotContextType,
    CopilotIntentType,
    CopilotMessageRole,
    EntityStatus,
)


class TestCopilotConversation:
    def test_required_fields(self):
        conv = CopilotConversation(
            organization_id="org-1",
            user_id="user-1",
            status=EntityStatus.ACTIVE,
        )
        assert conv.organization_id == "org-1"
        assert conv.user_id == "user-1"

    def test_default_fields(self):
        conv = CopilotConversation(
            organization_id="org-1", user_id="u1", status=EntityStatus.ACTIVE
        )
        assert conv.title == ""
        assert conv.context_type == "general"
        assert conv.context_id is None
        assert conv.message_count == 0
        assert conv.is_archived is False

    def test_unique_ids(self):
        c1 = CopilotConversation(organization_id="o", user_id="u", status=EntityStatus.ACTIVE)
        c2 = CopilotConversation(organization_id="o", user_id="u", status=EntityStatus.ACTIVE)
        assert c1.id != c2.id


class TestCopilotMessage:
    def test_required_fields(self):
        msg = CopilotMessage(
            conversation_id="conv-1",
            organization_id="org-1",
            user_id="user-1",
            role=CopilotMessageRole.USER,
            content="What are our risks?",
            status=EntityStatus.ACTIVE,
        )
        assert msg.conversation_id == "conv-1"
        assert msg.content == "What are our risks?"

    def test_default_fields(self):
        msg = CopilotMessage(
            conversation_id="conv-1",
            organization_id="org-1",
            user_id="u",
            role="user",
            content="hello",
            status=EntityStatus.ACTIVE,
        )
        assert msg.intent == ""
        assert msg.citations == []
        assert msg.retrieved_sources == {}
        assert msg.model_used == ""
        assert msg.generation_ms is None

    def test_citations_stored(self):
        citations = [{"citation_type": "Supplier", "object_id": "s1", "relevance": "explicit"}]
        msg = CopilotMessage(
            conversation_id="c",
            organization_id="o",
            user_id="u",
            role="assistant",
            content="...",
            citations=citations,
            status=EntityStatus.ACTIVE,
        )
        assert len(msg.citations) == 1
        assert msg.citations[0]["citation_type"] == "Supplier"


class TestCopilotEnums:
    def test_intent_type_values(self):
        values = {t.value for t in CopilotIntentType}
        assert "risk" in values
        assert "compliance" in values
        assert "disclosure" in values
        assert "due_diligence" in values
        assert "executive" in values
        assert "action" in values
        assert "general" in values

    def test_message_role_values(self):
        assert CopilotMessageRole.USER.value == "user"
        assert CopilotMessageRole.ASSISTANT.value == "assistant"

    def test_citation_type_values(self):
        values = {t.value for t in CitationType}
        assert "Supplier" in values
        assert "Finding" in values
        assert "Risk" in values
        assert "Recommendation" in values
        assert "Evidence" in values
        assert "Assessment" in values
        assert "ComplianceGap" in values
        assert "Disclosure" in values
        assert "Report" in values

    def test_context_type_values(self):
        values = {t.value for t in CopilotContextType}
        assert "general" in values
        assert "supplier" in values
        assert "compliance" in values
        assert "disclosure" in values
        assert "due_diligence" in values
        assert "executive" in values
