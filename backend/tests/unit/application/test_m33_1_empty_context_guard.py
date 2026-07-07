"""M33.1 — Empty Context Guard Tests.

Verifies that the copilot service returns a deterministic response without
calling the LLM when no data was retrieved for a question.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.copilot.context_assembler import NO_CONTEXT_MSG
from application.copilot.retrieval.base import RetrievalResult


def _empty_result(retriever: str = "supplier_retriever") -> RetrievalResult:
    return RetrievalResult(
        retriever=retriever,
        provenance="no data",
        data=[],
        source_ids=[],
        citation_type="Supplier",
    )


def _make_llm_mock() -> MagicMock:
    llm = MagicMock()
    llm.complete = AsyncMock()
    llm.provider_name = MagicMock(return_value="openai")
    llm.model_name = MagicMock(return_value="gpt-4o")
    return llm


class TestEmptyContextGuard:
    @pytest.mark.asyncio
    async def test_llm_not_called_when_no_data(self):
        """LLM.complete must NOT be called when all retrievers return empty data."""
        llm = _make_llm_mock()
        session = AsyncMock()

        with patch(
            "application.copilot.copilot_service._route_retrieval",
            new=AsyncMock(return_value=[_empty_result()]),
        ):
            from application.copilot.copilot_service import ask

            _user, _assistant = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )

        llm.complete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_deterministic_response_returned(self):
        """Same empty-context question returns the same canned answer every time."""
        llm = _make_llm_mock()
        session = AsyncMock()

        with patch(
            "application.copilot.copilot_service._route_retrieval",
            new=AsyncMock(return_value=[_empty_result()]),
        ):
            from application.copilot.copilot_service import ask

            _, assistant1 = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )
            _, assistant2 = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )

        assert assistant1.content == assistant2.content

    @pytest.mark.asyncio
    async def test_empty_context_response_has_no_citations(self):
        """Canned empty-context response must carry zero citations."""
        llm = _make_llm_mock()
        session = AsyncMock()

        with patch(
            "application.copilot.copilot_service._route_retrieval",
            new=AsyncMock(return_value=[_empty_result()]),
        ):
            from application.copilot.copilot_service import ask

            _, assistant = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )

        assert assistant.citations == []

    @pytest.mark.asyncio
    async def test_empty_context_model_used_is_empty(self):
        """model_used must be empty string when LLM is skipped."""
        llm = _make_llm_mock()
        session = AsyncMock()

        with patch(
            "application.copilot.copilot_service._route_retrieval",
            new=AsyncMock(return_value=[_empty_result()]),
        ):
            from application.copilot.copilot_service import ask

            _, assistant = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )

        assert assistant.model_used == ""

    @pytest.mark.asyncio
    async def test_empty_context_assembled_context_stored(self):
        """assembled_context on the assistant message must be the fallback string."""
        llm = _make_llm_mock()
        session = AsyncMock()

        with patch(
            "application.copilot.copilot_service._route_retrieval",
            new=AsyncMock(return_value=[_empty_result()]),
        ):
            from application.copilot.copilot_service import ask

            _, assistant = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )

        assert assistant.assembled_context == NO_CONTEXT_MSG

    @pytest.mark.asyncio
    async def test_llm_called_when_data_present(self):
        """LLM IS called when at least one retriever returns non-empty data."""
        llm = _make_llm_mock()
        llm_resp = MagicMock()
        llm_resp.content = "Based on [Supplier:s1], the risk is high."
        llm.complete = AsyncMock(return_value=llm_resp)
        session = AsyncMock()

        result_with_data = RetrievalResult(
            retriever="supplier_retriever",
            provenance="top suppliers",
            data=[{"supplier_id": "s1", "risk_score": 0.9}],
            source_ids=["s1"],
            citation_type="Supplier",
        )

        with patch(
            "application.copilot.copilot_service._route_retrieval",
            new=AsyncMock(return_value=[result_with_data]),
        ):
            from application.copilot.copilot_service import ask

            _, assistant = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )

        llm.complete.assert_awaited_once()
        assert assistant.model_used != ""

    @pytest.mark.asyncio
    async def test_user_message_snapshot_stored_even_on_empty_context(self):
        """Retrieval snapshot is stored on user message even when LLM is skipped."""
        llm = _make_llm_mock()
        session = AsyncMock()

        with patch(
            "application.copilot.copilot_service._route_retrieval",
            new=AsyncMock(return_value=[_empty_result("supplier_retriever")]),
        ):
            from application.copilot.copilot_service import ask

            user_msg, _ = await ask(
                question="What are our risks?",
                org_id="org-1",
                user_id="user-1",
                conversation_id=None,
                session=session,
                llm=llm,
            )

        assert "supplier_retriever" in user_msg.retrieval_snapshot
