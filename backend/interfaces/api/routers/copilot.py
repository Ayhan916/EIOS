"""
M33 AI Sustainability Copilot API

Routes:
  POST /copilot/ask                          — ask a question
  GET  /copilot/conversations                — list conversations
  POST /copilot/conversations                — create conversation
  GET  /copilot/conversations/{id}/messages  — list messages in conversation
  GET  /copilot/suggested-questions          — contextual suggested questions
  GET  /copilot/executive-brief              — evidence-backed executive brief
  GET  /copilot/action-advisor               — ranked action recommendations
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.copilot.action_advisor_engine import build_action_advisor_payload
from application.copilot.analytics_service import get_analytics
from application.copilot.audit_package_service import create_audit_package, generate_audit_pdf
from application.copilot.citation_integrity import verify_citations
from application.copilot.copilot_service import ask
from application.copilot.executive_brief_engine import build_executive_brief_payload
from application.copilot.reproducibility_verifier import verify_audit_package
from application.copilot.retrieval.compliance_retriever import retrieve_compliance_context
from application.copilot.retrieval.disclosure_retriever import retrieve_disclosure_context
from application.copilot.retrieval.executive_retriever import retrieve_executive_context
from application.copilot.retrieval.supplier_retriever import retrieve_supplier_context
from application.copilot.suggested_questions import get_suggested_questions
from application.ports.llm import LLMProvider, Message
from domain.copilot import CopilotConversation, CopilotMessage
from domain.copilot_audit import CopilotAnswerReview, CopilotFeedback
from domain.enums import CopilotMessageRole
from domain.enums import EntityStatus
from infrastructure.llm.deps import get_llm_provider
from infrastructure.observability.metrics import (
    record_answer,
    record_context_truncation,
    record_contradiction,
    record_empty_context,
    record_feedback,
    record_question,
)
from infrastructure.persistence.models.finding import FindingModel
from infrastructure.persistence.models.recommendation import RecommendationModel
from infrastructure.persistence.models.risk import RiskModel
from infrastructure.persistence.repositories.copilot import (
    SQLCopilotConversationRepository,
    SQLCopilotMessageRepository,
)
from infrastructure.persistence.repositories.copilot_audit import (
    SQLCopilotAnswerReviewRepository,
    SQLCopilotAuditPackageRepository,
    SQLCopilotCitationIntegrityRepository,
    SQLCopilotFeedbackRepository,
)
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_executive,
    scope_gate,
)
from interfaces.api.schemas.copilot import (
    ActionAdvisorResponse,
    AskRequest,
    CitationSchema,
    CopilotAnswerResponse,
    CopilotConversationSummary,
    CopilotMessageResponse,
    CreateConversationRequest,
    ExecutiveBriefResponse,
    SuggestedQuestionsResponse,
)
from interfaces.api.schemas.copilot_audit import (
    AnalyticsResponse,
    AuditPackageResponse,
    ContradictionSchema,
    FeedbackRequest,
    FeedbackResponse,
    ReviewRequest,
    ReviewResponse,
    VerificationCheckSchema,
    VerificationResultResponse,
)
from domain.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/copilot",
    tags=["AI Copilot"],
    dependencies=[Depends(scope_gate("copilot:read", "copilot:write"))],
)


def _citations(raw: list[dict]) -> list[CitationSchema]:
    return [CitationSchema(**c) for c in raw]


@router.post("/ask", response_model=CopilotAnswerResponse, status_code=status.HTTP_200_OK)
async def ask_copilot(
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> CopilotAnswerResponse:
    """Ask the AI Sustainability Copilot a question.

    The answer is grounded in retrieved EIOS data for this organisation.
    Every response includes citations traceable to source objects.
    """
    org_id = current_user.organization_id

    user_msg, assistant_msg = await ask(
        question=body.question,
        org_id=org_id,
        user_id=current_user.id,
        conversation_id=body.conversation_id,
        session=session,
        llm=llm,
    )

    conv_repo = SQLCopilotConversationRepository(session)
    msg_repo = SQLCopilotMessageRepository(session)

    # Upsert conversation — explicit None-check prevents swallowing HTTPException
    conv_id = user_msg.conversation_id
    conv = await conv_repo.get_by_id(conv_id)
    if conv is not None and conv.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conv is None:
        conv = CopilotConversation(
            id=conv_id,
            organization_id=org_id,
            user_id=current_user.id,
            title=body.question[:80],
            context_type=body.context_type,
            context_id=body.context_id,
            message_count=2,
            status=EntityStatus.ACTIVE,
        )
    else:
        conv.message_count += 2
    await conv_repo.save(conv)

    await msg_repo.save(user_msg)
    await msg_repo.save(assistant_msg)

    # M33.2 — emit Prometheus metrics
    record_question(org_id, assistant_msg.intent)
    if assistant_msg.model_used:
        record_answer(
            org_id,
            assistant_msg.confidence_level,
            assistant_msg.generation_ms or 0,
            assistant_msg.intent,
        )
    else:
        record_empty_context(org_id)
    if assistant_msg.context_truncated:
        record_context_truncation(org_id)
    # Record per-contradiction type
    for c in (assistant_msg.retrieved_sources.get("_contradictions") or []):
        record_contradiction(org_id, c.get("contradiction_type", "unknown"))

    contradictions_for_response = [
        ContradictionSchema(**c)
        for c in (assistant_msg.confidence_factors.get("_contradictions") or [])
    ]

    return CopilotAnswerResponse(
        conversation_id=conv_id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg.id,
        intent=assistant_msg.intent,
        answer=assistant_msg.content,
        citations=_citations(assistant_msg.citations),
        model_used=assistant_msg.model_used,
        generation_ms=assistant_msg.generation_ms,
        retrieved_sources=assistant_msg.retrieved_sources,
        confidence_level=assistant_msg.confidence_level,
        confidence_factors=assistant_msg.confidence_factors,
        contradictions=contradictions_for_response,
        freshness_summary=assistant_msg.freshness_summary,
        context_truncated=assistant_msg.context_truncated,
    )


@router.get("/conversations", response_model=list[CopilotConversationSummary])
async def list_conversations(
    include_archived: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CopilotConversationSummary]:
    """List all copilot conversations for the current user."""
    repo = SQLCopilotConversationRepository(session)
    convs = await repo.list_for_user(
        org_id=current_user.organization_id,
        user_id=current_user.id,
        include_archived=include_archived,
    )
    return [
        CopilotConversationSummary(
            id=c.id,
            title=c.title,
            context_type=c.context_type,
            message_count=c.message_count,
            is_archived=c.is_archived,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in convs
    ]


@router.post("/conversations", response_model=CopilotConversationSummary, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CopilotConversationSummary:
    """Create a new copilot conversation thread."""
    repo = SQLCopilotConversationRepository(session)
    conv = CopilotConversation(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        title=body.title,
        context_type=body.context_type,
        context_id=body.context_id,
        status=EntityStatus.ACTIVE,
    )
    await repo.save(conv)
    return CopilotConversationSummary(
        id=conv.id,
        title=conv.title,
        context_type=conv.context_type,
        message_count=conv.message_count,
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[CopilotMessageResponse])
async def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CopilotMessageResponse]:
    """List all messages in a conversation. Tenant-isolated — 404 on org mismatch."""
    conv_repo = SQLCopilotConversationRepository(session)
    conv = await conv_repo.get_by_id(conversation_id)
    if conv is None or conv.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    msg_repo = SQLCopilotMessageRepository(session)
    messages = await msg_repo.list_for_conversation(
        conversation_id=conversation_id,
        org_id=current_user.organization_id,
    )
    return [
        CopilotMessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            intent=m.intent,
            citations=_citations(m.citations),
            model_used=m.model_used,
            generation_ms=m.generation_ms,
            generated_at=m.generated_at,
        )
        for m in messages
    ]


@router.get("/suggested-questions", response_model=SuggestedQuestionsResponse)
async def suggested_questions(
    context_type: str = Query(default="general"),
    current_user: User = Depends(get_current_user),
) -> SuggestedQuestionsResponse:
    """Return contextual suggested questions for the given page context."""
    questions = get_suggested_questions(context_type=context_type, limit=5)
    return SuggestedQuestionsResponse(context_type=context_type, questions=questions)


@router.get("/executive-brief", response_model=ExecutiveBriefResponse, dependencies=[Depends(require_executive)])
async def executive_brief(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> ExecutiveBriefResponse:
    """Generate an evidence-backed executive brief. Restricted to executive role."""
    org_id = current_user.organization_id

    exec_result = await retrieve_executive_context(org_id, session)
    supplier_result = await retrieve_supplier_context(org_id, session)
    compliance_result = await retrieve_compliance_context(org_id, session)
    disclosure_result = await retrieve_disclosure_context(org_id, session)

    exec_data = exec_result.data[0] if exec_result.data else {}
    suppliers = supplier_result.data

    # Fetch overdue actions for executive payload
    from datetime import date
    from infrastructure.persistence.models.recommendation import RecommendationModel
    overdue_stmt = (
        select(RecommendationModel)
        .where(
            RecommendationModel.organization_id == org_id,
            RecommendationModel.action_status.in_(["open", "in_progress"]),
            RecommendationModel.due_date < date.today(),
        )
        .limit(10)
    )
    overdue_recs = (await session.execute(overdue_stmt)).scalars().all()
    overdue_data = [
        {"id": r.id, "title": r.title, "priority": r.priority,
         "due_date": str(r.due_date) if r.due_date else "",
         "days_overdue": (date.today() - r.due_date).days if r.due_date else 0}
        for r in overdue_recs
    ]

    payload = build_executive_brief_payload(
        risk_distribution=exec_data.get("risk_distribution", {}),
        critical_findings=exec_data.get("top_critical_findings", []),
        open_recommendations=exec_data.get("open_recommendations", 0),
        compliance_gaps=compliance_result.data,
        weak_disclosures=disclosure_result.data,
        overdue_actions=overdue_data,
        critical_suppliers=[s for s in suppliers if s.get("risk_band") in ("Critical", "High")],
    )

    import json
    context = json.dumps(payload, default=str, ensure_ascii=False)[:6000]
    system = (
        "You are the EIOS AI Sustainability Copilot generating an executive brief. "
        "Use ONLY the structured data below. Be evidence-backed and concise. "
        "Format as: Key Risks | Supplier Concerns | Compliance Concerns | Reporting Blockers | Recommended Actions.\n\n"
        f"DATA:\n{context}"
    )
    llm_resp = await llm.complete(
        messages=[Message(role="user", content="Generate an executive sustainability brief based on the data provided.")],
        system=system,
        max_tokens=1200,
        temperature=0.0,
    )

    all_source_ids = exec_result.source_ids + supplier_result.source_ids + compliance_result.source_ids
    from application.copilot.citation_extractor import extract_citations
    from application.copilot.context_assembler import build_citation_map
    cmap = build_citation_map([exec_result, supplier_result, compliance_result, disclosure_result])
    citations = extract_citations(llm_resp.content, cmap)

    return ExecutiveBriefResponse(
        answer=llm_resp.content,
        supplier_overview=payload["supplier_overview"],
        key_risks=payload["key_risks"],
        compliance_concerns=payload["compliance_concerns"],
        reporting_blockers=payload["reporting_blockers"],
        recommended_actions=payload["recommended_actions"],
        open_recommendations_total=payload["open_recommendations_total"],
        citations=_citations(citations),
        model_used=f"{llm.provider_name()}:{llm.model_name()}",
        generated_at=datetime.now(UTC),
    )


@router.get("/action-advisor", response_model=ActionAdvisorResponse)
async def action_advisor(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> ActionAdvisorResponse:
    """Return ranked action recommendations grounded in platform data."""
    org_id = current_user.organization_id

    # Fetch findings, risks, gaps, open recommendations
    from sqlalchemy import select
    from infrastructure.persistence.models.finding import FindingModel
    from infrastructure.persistence.models.risk import RiskModel

    findings_stmt = (
        select(FindingModel)
        .where(FindingModel.organization_id == org_id, FindingModel.severity.in_(["Critical", "High"]))
        .limit(20)
    )
    findings = (await session.execute(findings_stmt)).scalars().all()

    risks_stmt = (
        select(RiskModel)
        .where(RiskModel.organization_id == org_id, RiskModel.risk_level.in_(["Critical", "High"]))
        .limit(20)
    )
    risks = (await session.execute(risks_stmt)).scalars().all()

    compliance_result = await retrieve_compliance_context(org_id, session)

    from datetime import date
    recs_stmt = (
        select(RecommendationModel)
        .where(
            RecommendationModel.organization_id == org_id,
            RecommendationModel.action_status.in_(["open", "in_progress"]),
        )
        .limit(30)
    )
    recs = (await session.execute(recs_stmt)).scalars().all()
    today = date.today()
    recs_data = [
        {
            "id": r.id, "title": r.title, "priority": r.priority,
            "action_status": r.action_status,
            "due_date": str(r.due_date) if r.due_date else None,
            "overdue": bool(r.due_date and r.due_date < today),
        }
        for r in recs
    ]

    findings_data = [{"id": f.id, "title": f.title, "severity": f.severity, "category": getattr(f, "category", "")} for f in findings]
    risks_data = [{"id": r.id, "title": r.title, "risk_level": r.risk_level, "category": getattr(r, "category", "")} for r in risks]

    payload = build_action_advisor_payload(
        findings=findings_data,
        risks=risks_data,
        compliance_gaps=compliance_result.data,
        recommendations=recs_data,
    )

    import json
    context = json.dumps(payload, default=str, ensure_ascii=False)[:5000]
    system = (
        "You are the EIOS AI Action Advisor. "
        "Given the ranked actions below, explain which actions to prioritise and WHY. "
        "Every claim must reference the data. Use [Finding:id], [Risk:id], [Recommendation:id] citations.\n\n"
        f"DATA:\n{context}"
    )
    llm_resp = await llm.complete(
        messages=[Message(role="user", content="Which actions should we take to reduce ESG risk fastest?")],
        system=system,
        max_tokens=1000,
        temperature=0.0,
    )

    from application.copilot.citation_extractor import extract_citations
    from application.copilot.context_assembler import build_citation_map
    cmap = build_citation_map([compliance_result])
    cmap.update({f.id: "Finding" for f in findings})
    cmap.update({r.id: "Risk" for r in risks})
    cmap.update({r.id: "Recommendation" for r in recs})
    citations = extract_citations(llm_resp.content, cmap)

    return ActionAdvisorResponse(
        answer=llm_resp.content,
        highest_impact_actions=payload["highest_impact_actions"],
        fastest_remediations=payload["fastest_remediations"],
        risk_reduction_priorities=payload["risk_reduction_priorities"],
        top_compliance_gaps=payload["top_compliance_gaps"],
        finding_hotspots=payload["finding_hotspots"],
        open_action_count=payload["open_action_count"],
        citations=_citations(citations),
        model_used=f"{llm.provider_name()}:{llm.model_name()}",
        generated_at=datetime.now(UTC),
    )


# ── GAP-04 Founder Chat ────────────────────────────────────────────────────────

_FOUNDER_SYSTEM_PROMPT = """You are the EIOS Founder Intelligence Assistant.

You answer questions about EIOS platform health, AI quality metrics, evaluation
benchmark results, agent monitoring status, and cost trends.

STRICT RULES:
1. Answer ONLY from the PLATFORM DATA below — never use outside knowledge.
2. If the data does not contain enough information to answer a question, say so
   explicitly: "The platform does not have sufficient data to answer this."
3. Never invent numbers, scores, agent names, or benchmark results.
4. Structure every response as:
   **Observed Facts:** (what the data shows)
   **Inference:** (what this means, clearly labelled as inference)
   **Assumptions:** (what you assumed when the data was ambiguous)
   **Uncertainty:** (what you cannot determine from available data)
5. This endpoint is admin-only — do not include supplier or customer PII.

PLATFORM DATA:
{context}
"""

_FOUNDER_NO_DATA = (
    "The EIOS platform has not run any evaluation yet. "
    "Please trigger an evaluation run from the Mission Control dashboard "
    "before asking platform health questions."
)

_FOUNDER_QUICK_ACTIONS = [
    "Wie ist der aktuelle Platform Health Score?",
    "Warum hat sich die Accuracy verschlechtert?",
    "Welches Modul performt am schlechtesten?",
    "Was sollte als nächstes verbessert werden?",
    "Welche Agents haben Fehler?",
    "Wie hoch sind die API-Kosten dieser Woche?",
]


class FounderAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    conversation_id: str | None = None
    window_days: int = Field(default=30, ge=1, le=365)


class FounderChatResponse(BaseModel):
    conversation_id: str
    answer: str
    model_used: str
    generation_ms: int | None
    context_available: bool
    quick_actions: list[str]


@router.post(
    "/founder",
    response_model=FounderChatResponse,
    dependencies=[Depends(require_admin)],
    summary="Founder Chat — platform health Q&A grounded in internal EIOS metrics",
)
async def founder_chat(
    body: FounderAskRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> FounderChatResponse:
    """Founder-only chat grounded exclusively in internal EIOS platform data.

    Answers questions about evaluation metrics, benchmark status, agent errors,
    and cost trends. Never uses supplier or ESG data.
    """
    from uuid import uuid4 as _uuid4
    from application.copilot.founder_context import build_founder_context

    org_id = current_user.organization_id
    context_json = await build_founder_context(session, window_days=body.window_days)

    # Detect if we have real data
    import json as _json
    ctx_data = _json.loads(context_json)
    context_available = ctx_data.get("platform_health") is not None

    if not context_available:
        conv_id = body.conversation_id or str(_uuid4())
        return FounderChatResponse(
            conversation_id=conv_id,
            answer=_FOUNDER_NO_DATA,
            model_used="none",
            generation_ms=0,
            context_available=False,
            quick_actions=_FOUNDER_QUICK_ACTIONS,
        )

    system = _FOUNDER_SYSTEM_PROMPT.format(context=context_json[:8000])

    t0 = time.perf_counter()
    llm_resp = await llm.complete(
        messages=[Message(role="user", content=body.question)],
        system=system,
        max_tokens=1500,
        temperature=0.0,
    )
    generation_ms = int((time.perf_counter() - t0) * 1000)

    # Persist conversation + messages for audit trail
    conv_repo = SQLCopilotConversationRepository(session)
    msg_repo = SQLCopilotMessageRepository(session)

    conv_id = body.conversation_id or str(_uuid4())
    conv = await conv_repo.get_by_id(conv_id)
    if conv is None:
        conv = CopilotConversation(
            id=conv_id,
            organization_id=org_id,
            user_id=current_user.id,
            title=body.question[:80],
            context_type="founder",
            message_count=2,
            status=EntityStatus.ACTIVE,
        )
    else:
        conv.message_count += 2
    await conv_repo.save(conv)

    user_id = str(current_user.id)
    user_msg = CopilotMessage(
        conversation_id=conv_id,
        organization_id=org_id,
        user_id=user_id,
        role=CopilotMessageRole.USER,
        content=body.question,
        intent="founder_platform_health",
        status=EntityStatus.ACTIVE,
        citations=[],
        retrieved_sources={},
        confidence_factors={},
        freshness_summary={},
        retrieval_snapshot={},
    )
    assistant_msg = CopilotMessage(
        conversation_id=conv_id,
        organization_id=org_id,
        user_id=user_id,
        role=CopilotMessageRole.ASSISTANT,
        content=llm_resp.content,
        intent="founder_platform_health",
        model_used=f"{llm.provider_name()}:{llm.model_name()}",
        generation_ms=generation_ms,
        confidence_level="data_grounded",
        status=EntityStatus.ACTIVE,
        citations=[],
        retrieved_sources={"founder_context": True},
        confidence_factors={"source": "internal_metrics_only"},
        freshness_summary={},
        retrieval_snapshot={},
    )
    await msg_repo.save(user_msg)
    await msg_repo.save(assistant_msg)
    await session.commit()

    return FounderChatResponse(
        conversation_id=conv_id,
        answer=llm_resp.content,
        model_used=f"{llm.provider_name()}:{llm.model_name()}",
        generation_ms=generation_ms,
        context_available=True,
        quick_actions=_FOUNDER_QUICK_ACTIONS,
    )


# ── M33.2 Audit & Governance endpoints ───────────────────────────────────────


@router.post(
    "/messages/{message_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    message_id: str,
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Submit feedback on a Copilot assistant message."""
    org_id = current_user.organization_id
    msg_repo = SQLCopilotMessageRepository(session)
    msg = await msg_repo.get_by_id(message_id)
    if msg is None or msg.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    fb = CopilotFeedback(
        message_id=message_id,
        conversation_id=msg.conversation_id,
        organization_id=org_id,
        user_id=current_user.id,
        rating=body.rating,
        reason=body.reason,
        submitted_at=datetime.now(UTC),
        status=EntityStatus.ACTIVE,
    )
    fb_repo = SQLCopilotFeedbackRepository(session)
    saved = await fb_repo.save(fb)
    record_feedback(org_id, body.rating)

    return FeedbackResponse(
        id=saved.id,
        message_id=saved.message_id,
        rating=saved.rating,
        reason=saved.reason,
        submitted_at=saved.submitted_at,
    )


@router.post(
    "/messages/{message_id}/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_executive)],
)
async def review_answer(
    message_id: str,
    body: ReviewRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Executive review: approve, flag as misleading, or request investigation."""
    org_id = current_user.organization_id
    msg_repo = SQLCopilotMessageRepository(session)
    msg = await msg_repo.get_by_id(message_id)
    if msg is None or msg.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    review = CopilotAnswerReview(
        message_id=message_id,
        conversation_id=msg.conversation_id,
        organization_id=org_id,
        reviewer_id=current_user.id,
        decision=body.decision,
        notes=body.notes,
        reviewed_at=datetime.now(UTC),
        status=EntityStatus.ACTIVE,
    )
    review_repo = SQLCopilotAnswerReviewRepository(session)
    saved = await review_repo.save(review)

    logger.info(
        "copilot_answer_reviewed",
        message_id=message_id,
        org_id=org_id,
        decision=body.decision,
        reviewer=current_user.id,
    )

    return ReviewResponse(
        id=saved.id,
        message_id=saved.message_id,
        reviewer_id=saved.reviewer_id,
        decision=saved.decision,
        notes=saved.notes,
        reviewed_at=saved.reviewed_at,
    )


@router.get("/audit/{message_id}", response_model=AuditPackageResponse)
async def get_audit_package(
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AuditPackageResponse:
    """Download the immutable JSON audit package for a Copilot answer."""
    org_id = current_user.organization_id
    pkg_repo = SQLCopilotAuditPackageRepository(session)
    pkg = await pkg_repo.get_for_message(message_id, org_id)

    if pkg is None:
        msg_repo = SQLCopilotMessageRepository(session)
        msg = await msg_repo.get_by_id(message_id)
        if msg is None or msg.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

        from application.copilot.audit_package_service import compute_package_hash
        from domain.copilot_audit import CopilotAuditPackage
        from domain.enums import AuditVerificationStatus
        payload = {
            "schema_version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "message_id": msg.id,
            "organization_id": org_id,
            "answer": msg.content,
            "intent": msg.intent,
            "model_used": msg.model_used,
            "generation_ms": msg.generation_ms,
            "citations": msg.citations,
            "retrieval_snapshot": msg.retrieval_snapshot,
            "assembled_context": msg.assembled_context,
            "system_prompt_snapshot": msg.system_prompt_snapshot,
            "confidence_level": msg.confidence_level,
            "confidence_factors": msg.confidence_factors,
            "freshness_summary": msg.freshness_summary,
            "contradictions": [],
            "context_budget": {},
        }
        pkg_hash = compute_package_hash(payload)
        pkg = CopilotAuditPackage(
            message_id=message_id,
            organization_id=org_id,
            package_hash=pkg_hash,
            json_payload=payload,
            generated_at=datetime.now(UTC),
            verification_status=AuditVerificationStatus.PENDING,
            status=EntityStatus.ACTIVE,
        )
        pkg = await pkg_repo.save(pkg)

    return AuditPackageResponse(
        package_id=pkg.id,
        message_id=pkg.message_id,
        package_hash=pkg.package_hash,
        generated_at=pkg.generated_at,
        verification_status=pkg.verification_status,
        json_payload=pkg.json_payload,
    )


@router.get("/audit/{message_id}/verify", response_model=VerificationResultResponse)
async def verify_answer_audit(
    message_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VerificationResultResponse:
    """Verify the integrity of a stored audit package."""
    org_id = current_user.organization_id
    pkg_repo = SQLCopilotAuditPackageRepository(session)
    pkg = await pkg_repo.get_for_message(message_id, org_id)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audit package found. Request the package first via GET /audit/{message_id}.",
        )
    result = await verify_audit_package(pkg.id, org_id, session)
    return VerificationResultResponse(
        package_id=result.package_id,
        message_id=result.message_id,
        overall=result.overall,
        checks=[VerificationCheckSchema(**c.__dict__) for c in result.checks],
        verified_at=result.verified_at,
    )


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    dependencies=[Depends(require_executive)],
)
async def conversation_analytics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """Conversation analytics. Executive and admin only."""
    org_id = current_user.organization_id
    a = await get_analytics(org_id, session)
    return AnalyticsResponse(
        organization_id=a.organization_id,
        total_questions=a.total_questions,
        total_conversations=a.total_conversations,
        questions_by_intent=a.questions_by_intent,
        average_confidence_score=round(a.average_confidence_score, 3),
        confidence_distribution=a.confidence_distribution,
        average_citations_per_answer=round(a.average_citations_per_answer, 2),
        empty_context_count=a.empty_context_count,
        empty_context_rate=round(a.empty_context_rate, 4),
        contradiction_rate=round(a.contradiction_rate, 4),
        average_contradiction_count=round(a.average_contradiction_count, 2),
        feedback_helpful_count=a.feedback_helpful_count,
        feedback_not_helpful_count=a.feedback_not_helpful_count,
        feedback_incorrect_count=a.feedback_incorrect_count,
        feedback_outdated_count=a.feedback_outdated_count,
        feedback_total=a.feedback_total,
    )
