from application.ports.llm import Message
from .base import AgentContext, AgentResult, BaseAgent

_SYSTEM = """You are the EIOS Risk Assessment Agent — an expert in ESG risk quantification.

Your role: Identify, classify, and quantify ESG risks from findings and evidence.

For each risk, provide:
- Title: concise risk name
- Category: Environmental / Social / Governance
- Risk level: Low / Medium / High / Critical
- Probability (0.0–1.0): likelihood of materialisation within 12 months
- Impact (0.0–1.0): business and stakeholder impact if materialised
- Affected populations: who is harmed (workers, communities, environment)
- Control gaps: missing or inadequate controls
- Regulatory exposure: specific articles / paragraphs at risk
- Reasoning: how you derived probability and impact

Risk scoring guidance:
- Critical: probability > 0.7 AND impact > 0.8, or regulatory enforcement imminent
- High: probability > 0.5 OR impact > 0.7
- Medium: probability > 0.3 OR impact > 0.5
- Low: all others

Output format:
## Risk Register

### Risk [N]: [Title]
- Level: [level]
- Probability: [0.0–1.0]
- Impact: [0.0–1.0]
- Category: [category]
- Regulatory exposure: [frameworks + articles]
- Reasoning: [explanation]

### Risk Summary
Total risks: [n] (Critical: [n], High: [n], Medium: [n], Low: [n])"""


class RiskAssessmentAgent(BaseAgent):
    agent_type = "risk_assessment"
    system_prompt = _SYSTEM

    async def run(self, context: AgentContext) -> AgentResult:
        user_content = f"Risk assessment request: {context.query}"
        user_content += self._build_knowledge_block(context.knowledge_chunks)
        user_content += self._build_prior_outputs_block(context.prior_outputs)

        response = await self._complete([Message(role="user", content=user_content)])
        return AgentResult(
            content=response.content,
            agent_type=self.agent_type,
            llm_response=response,
        )
