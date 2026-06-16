from __future__ import annotations

from typing import TYPE_CHECKING

from application.agents.base import BaseAgent
from application.agents.esg_assessment import ESGAssessmentAgent
from application.agents.evaluation import EvaluationAgent
from application.agents.governance import GovernanceAgent
from application.agents.memory import MemoryAgent
from application.agents.reasoning import ReasoningAgent
from application.agents.recommendation import RecommendationAgent
from application.agents.reporting import ReportingAgent
from application.agents.research import ResearchAgent
from application.agents.retrieval import RetrievalAgent
from application.agents.risk_assessment import RiskAssessmentAgent

if TYPE_CHECKING:
    from application.ports.llm import LLMProvider

_AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    "research": ResearchAgent,
    "retrieval": RetrievalAgent,
    "reasoning": ReasoningAgent,
    "esg_assessment": ESGAssessmentAgent,
    "risk_assessment": RiskAssessmentAgent,
    "recommendation": RecommendationAgent,
    "evaluation": EvaluationAgent,
    "memory": MemoryAgent,
    "governance": GovernanceAgent,
    "reporting": ReportingAgent,
}

AGENT_TYPES: list[str] = list(_AGENT_CLASSES.keys())


def get_agent(agent_type: str, provider: LLMProvider) -> BaseAgent:
    cls = _AGENT_CLASSES.get(agent_type)
    if cls is None:
        raise ValueError(f"Unknown agent type: '{agent_type}'. Valid types: {AGENT_TYPES}")
    return cls(provider)
