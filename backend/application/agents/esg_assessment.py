from application.ports.llm import Message

from .base import AgentContext, AgentResult, BaseAgent

_SYSTEM = """You are the EIOS ESG Assessment Agent — an expert in sector-level ESG risk assessment.

Your role: Assess ESG risks for NACE-classified sectors under the CSDDD, LkSG, CSRD, GRI Standards, and ESRS frameworks.

Primary scope: sector-level risk profile (Company and Supplier are secondary, anchored to the sector).

ESG Dimensions:
- Environmental (E): emissions, biodiversity, water, waste, land use
- Social (S): labour rights, child labour, forced labour, health & safety, community impact
- Governance (G): transparency, corruption, board accountability, supply chain oversight

For each material finding, provide:
- Category (E / S / G + sub-category)
- Severity (Low / Medium / High / Critical)
- Confidence (High / Medium / Low)
- Regulatory obligation (CSDDD Art. / LkSG § / CSRD standard / GRI)
- Evidence basis (reference evidence provided)
- Reasoning

Output format:
## Sector ESG Risk Profile
**NACE Sector:** [sector]
**Assessment scope:** [scope]

### Material Findings
[numbered list of findings with structured fields]

### Overall Risk Level
[Low / Medium / High / Critical] — [justification]

### Priority Actions
[top 3 immediate actions required]"""


class ESGAssessmentAgent(BaseAgent):
    agent_type = "esg_assessment"
    system_prompt = _SYSTEM

    async def run(self, context: AgentContext) -> AgentResult:
        user_content = f"ESG assessment request: {context.query}"
        user_content += self._build_knowledge_block(context.knowledge_chunks)
        user_content += self._build_prior_outputs_block(context.prior_outputs)

        if context.metadata.get("nace_code"):
            user_content += f"\n\nNACE code: {context.metadata['nace_code']}"
        if context.metadata.get("sector_name"):
            user_content += f"\nSector: {context.metadata['sector_name']}"

        response = await self._complete([Message(role="user", content=user_content)])
        return AgentResult(
            content=response.content,
            agent_type=self.agent_type,
            llm_response=response,
        )
