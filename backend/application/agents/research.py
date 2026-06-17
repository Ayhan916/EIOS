from application.ports.llm import Message

from .base import AgentContext, AgentResult, BaseAgent

_SYSTEM = """You are the EIOS Research Agent for ESG due diligence and risk intelligence.

Your role: Analyse the given ESG context and identify what evidence and information is needed for a comprehensive assessment.

Responsibilities:
- Identify the relevant NACE sector(s) and applicable regulatory frameworks (CSDDD, LkSG, CSRD, GRI Standards, ESRS)
- Surface the most material ESG risk domains (labour rights, environmental impact, governance, supply chain)
- Generate targeted research questions and evidence-gathering priorities
- Prioritise by materiality and regulatory obligation

Output format:
1. Context summary
2. Key ESG risk domains identified
3. Applicable frameworks and obligations
4. Prioritised evidence-gathering questions (numbered list)
5. Recommended data sources"""


class ResearchAgent(BaseAgent):
    agent_type = "research"
    system_prompt = _SYSTEM

    async def run(self, context: AgentContext) -> AgentResult:
        user_content = f"Research request: {context.query}"
        user_content += self._build_knowledge_block(context.knowledge_chunks)
        user_content += self._build_prior_outputs_block(context.prior_outputs)

        if context.metadata.get("sector_id"):
            user_content += f"\n\nSector ID: {context.metadata['sector_id']}"
        if context.metadata.get("nace_code"):
            user_content += f"\nNACE code: {context.metadata['nace_code']}"

        response = await self._complete([Message(role="user", content=user_content)])
        return AgentResult(
            content=response.content,
            agent_type=self.agent_type,
            llm_response=response,
        )
