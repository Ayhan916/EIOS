from application.ports.llm import Message
from .base import AgentContext, AgentResult, BaseAgent

_SYSTEM = """You are the EIOS Retrieval Agent for ESG due diligence.

Your role: Synthesise evidence from the EIOS knowledge base to answer ESG and compliance questions.

Responsibilities:
- Ground all answers strictly in the provided evidence chunks
- Cite the evidence source (chunk number) when making substantive claims
- Flag explicitly when evidence is insufficient, contradictory, or absent
- Never invent information not present in the evidence
- Note the confidence level of each synthesised finding

Output format:
1. Direct answer to the query
2. Supporting evidence (with chunk references)
3. Evidence gaps or contradictions
4. Confidence assessment (High / Medium / Low) with reasoning"""


class RetrievalAgent(BaseAgent):
    agent_type = "retrieval"
    system_prompt = _SYSTEM

    async def run(self, context: AgentContext) -> AgentResult:
        if not context.knowledge_chunks:
            return AgentResult(
                content="No knowledge chunks provided. Ingest relevant evidence via POST /api/v1/knowledge/ingest before running the Retrieval Agent.",
                agent_type=self.agent_type,
                confidence=0.0,
            )

        user_content = f"Query: {context.query}"
        user_content += self._build_knowledge_block(context.knowledge_chunks)

        response = await self._complete([Message(role="user", content=user_content)])
        return AgentResult(
            content=response.content,
            agent_type=self.agent_type,
            llm_response=response,
        )
