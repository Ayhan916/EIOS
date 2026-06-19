"""AI Sustainability Copilot — main orchestration service.

Handles:
- Intent detection
- Context retrieval (routing by intent, with freshness metadata)
- Contradiction detection (pre-LLM)
- Budget-aware context assembly
- LLM answer generation
- Citation extraction (citation_map validated)
- Confidence calculation (evidence-based)
- Message persistence audit trail (full snapshot)
"""

from __future__ import annotations

import time
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.llm import LLMProvider, Message
from domain.copilot import CopilotConversation, CopilotMessage
from domain.enums import CopilotIntentType, CopilotMessageRole, EntityStatus

from .citation_extractor import extract_citations, format_citations_for_prompt
from .confidence_calculator import calculate_confidence
from .context_assembler import NO_CONTEXT_MSG, assemble_context_with_budget, build_citation_map
from .context_budget import budget_dict, format_budget_note
from .contradiction_detector import (
    ContradictionRecord,
    contradictions_to_dicts,
    detect_contradictions,
    format_contradictions_for_prompt,
)
from .freshness_tracker import (
    FreshnessReport,
    analyze_freshness,
    format_freshness_for_prompt,
    freshness_summary_dict,
)
from .intent_detector import detect_intent
from .retrieval.base import RetrievalResult
from .retrieval.compliance_retriever import retrieve_compliance_context
from .retrieval.disclosure_retriever import retrieve_disclosure_context
from .retrieval.due_diligence_retriever import retrieve_due_diligence_context
from .retrieval.executive_retriever import retrieve_executive_context
from .retrieval.supplier_retriever import retrieve_supplier_context

logger = structlog.get_logger(__name__)

_NO_DATA_RESPONSE = (
    "I could not find sufficient data in the EIOS platform to answer this question. "
    "Please ensure relevant suppliers, assessments, or compliance data has been added to the system."
)

_SYSTEM_PROMPT = """You are the EIOS AI Sustainability Copilot.

You assist sustainability professionals with questions about ESG risks, supplier due diligence, compliance gaps, and regulatory disclosures.

Rules:
1. Answer ONLY from the CONTEXT DATA provided below. Do not use outside knowledge.
2. If the data does not contain enough information to answer, say so explicitly.
3. Cite sources using [Type:id] notation (e.g. [Supplier:s-123], [Finding:f-456]).
4. Be concise and evidence-backed.
5. Never speculate about compliance status. Only state what the data shows.
6. Do not hallucinate supplier names, IDs, or regulation text.

{citation_hint}
{freshness_note}
{contradiction_note}
{budget_note}
CONTEXT DATA:
{context}
"""


async def _route_retrieval(
    intent: CopilotIntentType,
    org_id: str,
    session: AsyncSession,
) -> list[RetrievalResult]:
    results: list[RetrievalResult] = []

    if intent in (CopilotIntentType.RISK, CopilotIntentType.ACTION):
        results.append(await retrieve_supplier_context(org_id, session))
        results.append(await retrieve_compliance_context(org_id, session))

    elif intent == CopilotIntentType.COMPLIANCE:
        results.append(await retrieve_compliance_context(org_id, session))
        results.append(await retrieve_supplier_context(org_id, session))

    elif intent == CopilotIntentType.DISCLOSURE:
        results.append(await retrieve_disclosure_context(org_id, session))
        results.append(await retrieve_compliance_context(org_id, session))

    elif intent == CopilotIntentType.DUE_DILIGENCE:
        results.append(await retrieve_due_diligence_context(org_id, session))
        results.append(await retrieve_supplier_context(org_id, session))

    elif intent in (CopilotIntentType.EXECUTIVE, CopilotIntentType.GENERAL):
        results.append(await retrieve_executive_context(org_id, session))
        results.append(await retrieve_supplier_context(org_id, session))
        results.append(await retrieve_compliance_context(org_id, session))

    return results


async def ask(
    *,
    question: str,
    org_id: str,
    user_id: str,
    conversation_id: str | None,
    session: AsyncSession,
    llm: LLMProvider,
    max_tokens: int = 1024,
) -> tuple[CopilotMessage, CopilotMessage]:
    """Process a copilot question and return (user_message, assistant_message).

    Full pipeline:
      Intent → Retrieval → Freshness → Contradictions → Budget Assembly
      → Empty-Context Guard → Prompt → LLM → Citations → Confidence → Messages
    """
    t0 = time.monotonic()
    conv_id = conversation_id or str(uuid4())

    # 1. Intent detection
    intent = detect_intent(question)

    # 2. Retrieve context (with freshness metadata)
    retrieved = await _route_retrieval(intent, org_id, session)

    # 3. Freshness analysis
    freshness: FreshnessReport = analyze_freshness(retrieved)

    # 4. Pre-LLM contradiction detection
    contradictions: list[ContradictionRecord] = detect_contradictions(retrieved)

    # 5. Budget-aware context assembly
    context_str, budget = assemble_context_with_budget(retrieved)
    citation_map = build_citation_map(retrieved)

    # 6. Build full retrieval snapshot for audit trail
    retrieval_snapshot = {
        r.retriever: {
            "provenance": r.provenance,
            "citation_type": r.citation_type,
            "source_ids": r.source_ids,
            "data": r.data,
            "freshness_metadata": r.freshness_metadata,
        }
        for r in retrieved
    }

    retrieved_sources = {
        r.retriever: {
            "provenance": r.provenance,
            "source_count": len(r.source_ids),
            "citation_type": r.citation_type,
        }
        for r in retrieved
    }

    freshness_summary = freshness_summary_dict(freshness)
    budget_report = budget_dict(budget)
    contradiction_dicts = contradictions_to_dicts(contradictions)

    user_msg = CopilotMessage(
        conversation_id=conv_id,
        organization_id=org_id,
        user_id=user_id,
        role=CopilotMessageRole.USER,
        content=question,
        intent=intent.value,
        status=EntityStatus.ACTIVE,
        retrieval_snapshot=retrieval_snapshot,
        assembled_context=context_str,
        freshness_summary=freshness_summary,
        contradiction_count=len(contradictions),
        context_budget_used=budget.used_chars,
        context_truncated=budget.truncated,
    )

    # 7. Empty-context guard — skip LLM, return deterministic response
    if context_str == NO_CONTEXT_MSG:
        # Confidence = Low when no data
        empty_conf_level, empty_conf_factors = calculate_confidence(
            retrieved, [], contradictions, freshness
        )
        assistant_msg = CopilotMessage(
            conversation_id=conv_id,
            organization_id=org_id,
            user_id=user_id,
            role=CopilotMessageRole.ASSISTANT,
            content=_NO_DATA_RESPONSE,
            intent=intent.value,
            citations=[],
            retrieved_sources=retrieved_sources,
            model_used="",
            generation_ms=0,
            status=EntityStatus.ACTIVE,
            retrieval_snapshot=retrieval_snapshot,
            assembled_context=context_str,
            system_prompt_snapshot="",
            confidence_level=empty_conf_level.value,
            confidence_factors=empty_conf_factors,
            contradiction_count=len(contradictions),
            context_budget_used=budget.used_chars,
            context_truncated=budget.truncated,
            freshness_summary=freshness_summary,
        )
        logger.info(
            "copilot_empty_context",
            org_id=org_id,
            intent=intent.value,
            contradictions=len(contradictions),
        )
        return user_msg, assistant_msg

    # 8. Build enriched system prompt
    citation_hint = format_citations_for_prompt(citation_map)
    freshness_note = format_freshness_for_prompt(freshness)
    contradiction_note = format_contradictions_for_prompt(contradictions)
    budget_note = format_budget_note(budget)

    system = _SYSTEM_PROMPT.format(
        citation_hint=citation_hint,
        freshness_note=f"\n{freshness_note}\n" if freshness_note else "",
        contradiction_note=f"\n{contradiction_note}\n" if contradiction_note else "",
        budget_note=f"\n{budget_note}\n" if budget_note else "",
        context=context_str,
    )

    # 9. LLM call
    llm_response = await llm.complete(
        messages=[Message(role="user", content=question)],
        system=system,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    generation_ms = int((time.monotonic() - t0) * 1000)

    # 10. Extract citations (only IDs present in citation_map are accepted)
    citations = extract_citations(llm_response.content, citation_map)

    # 11. Evidence-based confidence calculation
    confidence_level, confidence_factors = calculate_confidence(
        retrieved, citations, contradictions, freshness
    )

    # 12. Construct assistant message with full audit snapshot
    assistant_msg = CopilotMessage(
        conversation_id=conv_id,
        organization_id=org_id,
        user_id=user_id,
        role=CopilotMessageRole.ASSISTANT,
        content=llm_response.content,
        intent=intent.value,
        citations=citations,
        retrieved_sources=retrieved_sources,
        model_used=f"{llm.provider_name()}:{llm.model_name()}",
        generation_ms=generation_ms,
        status=EntityStatus.ACTIVE,
        retrieval_snapshot=retrieval_snapshot,
        assembled_context=context_str,
        system_prompt_snapshot=system,
        confidence_level=confidence_level.value,
        confidence_factors=confidence_factors,
        contradiction_count=len(contradictions),
        context_budget_used=budget.used_chars,
        context_truncated=budget.truncated,
        freshness_summary=freshness_summary,
    )

    logger.info(
        "copilot_answer_generated",
        org_id=org_id,
        intent=intent.value,
        citations=len(citations),
        generation_ms=generation_ms,
        model=llm.model_name(),
        confidence=confidence_level.value,
        contradictions=len(contradictions),
        context_truncated=budget.truncated,
        stale_data=freshness.has_stale_data,
    )

    return user_msg, assistant_msg
