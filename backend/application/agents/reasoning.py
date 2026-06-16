from application.ports.llm import Message
from .base import AgentContext, AgentResult, BaseAgent

_SYSTEM = """You are the EIOS Reasoning Agent for ESG risk analysis.

Your role: Perform structured logical analysis of ESG risks, findings, and compliance gaps.

Responsibilities:
- Apply explicit chain-of-thought reasoning: evidence → finding → risk → business impact
- Assess uncertainty and alternative interpretations
- Identify causal chains and systemic risk factors
- Draw defensible, audit-ready conclusions from available evidence
- Distinguish between established facts, inferences, and assumptions

Output format:
1. Premises (established facts from evidence)
2. Inference chain (step-by-step reasoning)
3. Conclusions
4. Uncertainties and alternative interpretations
5. Confidence level (0.0–1.0) with justification"""


class ReasoningAgent(BaseAgent):
    agent_type = "reasoning"
    system_prompt = _SYSTEM

    async def run(self, context: AgentContext) -> AgentResult:
        user_content = f"Analyse: {context.query}"
        user_content += self._build_knowledge_block(context.knowledge_chunks)
        user_content += self._build_prior_outputs_block(context.prior_outputs)

        response = await self._complete([Message(role="user", content=user_content)])
        return AgentResult(
            content=response.content,
            agent_type=self.agent_type,
            llm_response=response,
        )
