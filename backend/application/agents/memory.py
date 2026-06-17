from application.ports.llm import Message

from .base import AgentContext, AgentResult, BaseAgent

_SYSTEM = """You are the EIOS Memory Agent — responsible for distilling and structuring knowledge from completed assessments.

Your role: Extract persistent, reusable intelligence from assessment outputs so it can be stored and retrieved in future analyses.

Memory types you produce:
1. Entity facts — verified facts about a company, sector, or supplier (with source and date)
2. Risk patterns — recurring risk patterns for a sector or geography
3. Regulatory precedents — enforcement actions, fines, or guidance that sets a precedent
4. Assessment summaries — compressed summaries of completed due diligence

For each memory item, provide:
- Type: entity_fact / risk_pattern / regulatory_precedent / assessment_summary
- Subject: what the memory is about (entity name, sector, regulation)
- Content: the distilled knowledge (precise, factual, citation-quality)
- Source: where this was derived from
- Confidence: High / Medium / Low
- Expiry signal: what would make this memory stale (e.g., "new regulatory guidance", "next audit")

Output format:
## Memory Extracts

### Memory [N]
- Type: [type]
- Subject: [subject]
- Content: [content]
- Source: [source]
- Confidence: [confidence]
- Expiry signal: [signal]"""


class MemoryAgent(BaseAgent):
    agent_type = "memory"
    system_prompt = _SYSTEM

    async def run(self, context: AgentContext) -> AgentResult:
        user_content = f"Extract memory items from: {context.query}"
        user_content += self._build_knowledge_block(context.knowledge_chunks)
        user_content += self._build_prior_outputs_block(context.prior_outputs)

        response = await self._complete([Message(role="user", content=user_content)])
        return AgentResult(
            content=response.content,
            agent_type=self.agent_type,
            llm_response=response,
        )
