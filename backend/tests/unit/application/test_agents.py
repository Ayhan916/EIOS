"""Unit tests for all 10 EIOS canonical agents.

Uses a mock LLMProvider so no API keys or network are needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.agents.base import AgentContext, AgentResult, BaseAgent
from application.agents.esg_assessment import ESGAssessmentAgent
from application.agents.evaluation import EvaluationAgent
from application.agents.governance import GovernanceAgent
from application.agents.memory import MemoryAgent
from application.agents.reasoning import ReasoningAgent
from application.agents.recommendation import RecommendationAgent
from application.agents.registry import AGENT_TYPES, get_agent
from application.agents.reporting import ReportingAgent
from application.agents.research import ResearchAgent
from application.agents.retrieval import RetrievalAgent
from application.agents.risk_assessment import RiskAssessmentAgent
from application.ports.llm import LLMResponse


def make_mock_provider(content: str = "mock response") -> MagicMock:
    response = LLMResponse(
        content=content,
        model="mock-model",
        provider="mock",
        input_tokens=10,
        output_tokens=20,
        stop_reason="end_turn",
    )
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=response)
    provider.model_name = MagicMock(return_value="mock-model")
    provider.provider_name = MagicMock(return_value="mock")
    return provider


def make_context(**kwargs: object) -> AgentContext:
    defaults: dict = {
        "query": "Test query",
        "knowledge_chunks": [],
        "prior_outputs": [],
        "metadata": {},
    }
    defaults.update(kwargs)
    return AgentContext(**defaults)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    def test_all_ten_types_registered(self) -> None:
        expected = {
            "research", "retrieval", "reasoning", "esg_assessment",
            "risk_assessment", "recommendation", "evaluation",
            "memory", "governance", "reporting",
        }
        assert set(AGENT_TYPES) == expected

    def test_get_agent_returns_correct_class(self) -> None:
        provider = make_mock_provider()
        for agent_type in AGENT_TYPES:
            agent = get_agent(agent_type, provider)
            assert isinstance(agent, BaseAgent)
            assert agent.agent_type == agent_type

    def test_get_agent_raises_on_unknown_type(self) -> None:
        provider = make_mock_provider()
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_agent("nonexistent", provider)


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

class TestBaseAgent:
    def test_build_knowledge_block_empty(self) -> None:
        agent = ResearchAgent(make_mock_provider())
        result = agent._build_knowledge_block([])
        assert result == ""

    def test_build_knowledge_block_populated(self) -> None:
        agent = ResearchAgent(make_mock_provider())
        result = agent._build_knowledge_block(["chunk one", "chunk two"])
        assert "<knowledge>" in result
        assert "chunk one" in result
        assert "chunk two" in result

    def test_build_prior_outputs_block_empty(self) -> None:
        agent = ResearchAgent(make_mock_provider())
        result = agent._build_prior_outputs_block([])
        assert result == ""

    def test_build_prior_outputs_block_populated(self) -> None:
        agent = ReasoningAgent(make_mock_provider())
        result = agent._build_prior_outputs_block(["prior 1"])
        assert "<prior_agent_outputs>" in result
        assert "prior 1" in result


# ---------------------------------------------------------------------------
# Individual agents
# ---------------------------------------------------------------------------

class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_run_returns_agent_result(self) -> None:
        agent = ResearchAgent(make_mock_provider("research output"))
        result = await agent.run(make_context(query="ESG risks in textile sector"))
        assert isinstance(result, AgentResult)
        assert result.agent_type == "research"
        assert result.content == "research output"
        assert result.llm_response is not None

    @pytest.mark.asyncio
    async def test_run_passes_knowledge_to_provider(self) -> None:
        provider = make_mock_provider()
        agent = ResearchAgent(provider)
        ctx = make_context(knowledge_chunks=["chunk A", "chunk B"])
        await agent.run(ctx)
        call_args = provider.complete.call_args
        messages = call_args[0][0]
        assert "chunk A" in messages[0].content
        assert "chunk B" in messages[0].content


class TestRetrievalAgent:
    @pytest.mark.asyncio
    async def test_run_returns_no_chunks_warning_when_empty(self) -> None:
        agent = RetrievalAgent(make_mock_provider())
        result = await agent.run(make_context(knowledge_chunks=[]))
        assert result.confidence == 0.0
        assert "No knowledge chunks" in result.content

    @pytest.mark.asyncio
    async def test_run_calls_provider_when_chunks_present(self) -> None:
        provider = make_mock_provider("retrieval output")
        agent = RetrievalAgent(provider)
        result = await agent.run(make_context(knowledge_chunks=["chunk 1"]))
        assert result.content == "retrieval output"
        provider.complete.assert_awaited_once()


class TestReasoningAgent:
    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        agent = ReasoningAgent(make_mock_provider("reasoning output"))
        result = await agent.run(make_context())
        assert result.agent_type == "reasoning"
        assert result.content == "reasoning output"


class TestESGAssessmentAgent:
    @pytest.mark.asyncio
    async def test_run_includes_nace_metadata(self) -> None:
        provider = make_mock_provider()
        agent = ESGAssessmentAgent(provider)
        ctx = make_context(metadata={"nace_code": "C13", "sector_name": "Textiles"})
        await agent.run(ctx)
        call_args = provider.complete.call_args
        messages = call_args[0][0]
        assert "C13" in messages[0].content
        assert "Textiles" in messages[0].content

    @pytest.mark.asyncio
    async def test_run_without_metadata_succeeds(self) -> None:
        agent = ESGAssessmentAgent(make_mock_provider("esg output"))
        result = await agent.run(make_context())
        assert result.agent_type == "esg_assessment"


class TestRiskAssessmentAgent:
    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        agent = RiskAssessmentAgent(make_mock_provider("risk register"))
        result = await agent.run(make_context())
        assert result.agent_type == "risk_assessment"
        assert "risk register" in result.content


class TestRecommendationAgent:
    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        agent = RecommendationAgent(make_mock_provider("recommendations"))
        result = await agent.run(make_context())
        assert result.agent_type == "recommendation"
        assert "recommendations" in result.content


class TestEvaluationAgent:
    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        agent = EvaluationAgent(make_mock_provider("quality assessment"))
        result = await agent.run(make_context())
        assert result.agent_type == "evaluation"


class TestMemoryAgent:
    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        agent = MemoryAgent(make_mock_provider("memory extracts"))
        result = await agent.run(make_context())
        assert result.agent_type == "memory"


class TestGovernanceAgent:
    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        agent = GovernanceAgent(make_mock_provider("governance assessment"))
        result = await agent.run(make_context())
        assert result.agent_type == "governance"


class TestReportingAgent:
    @pytest.mark.asyncio
    async def test_run_includes_entity_metadata(self) -> None:
        provider = make_mock_provider()
        agent = ReportingAgent(provider)
        ctx = make_context(metadata={"entity_name": "Acme GmbH", "report_date": "2026-06-16"})
        await agent.run(ctx)
        call_args = provider.complete.call_args
        messages = call_args[0][0]
        assert "Acme GmbH" in messages[0].content
        assert "2026-06-16" in messages[0].content

    @pytest.mark.asyncio
    async def test_run_returns_result(self) -> None:
        agent = ReportingAgent(make_mock_provider("full report"))
        result = await agent.run(make_context())
        assert result.agent_type == "reporting"
        assert "full report" in result.content


# ---------------------------------------------------------------------------
# Token usage propagation
# ---------------------------------------------------------------------------

class TestTokenUsagePropagation:
    @pytest.mark.asyncio
    async def test_llm_response_attached_to_result(self) -> None:
        provider = make_mock_provider()
        agent = ReasoningAgent(provider)
        result = await agent.run(make_context())
        assert result.llm_response is not None
        assert result.llm_response.input_tokens == 10
        assert result.llm_response.output_tokens == 20
        assert result.llm_response.provider == "mock"
