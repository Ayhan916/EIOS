"""Conversation Analytics Service — M33.2.

Aggregates Copilot usage metrics per organisation from existing message
and feedback data. No separate aggregation table — computes on demand.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import CopilotMessageRole


@dataclass
class ConversationAnalytics:
    organization_id: str
    total_questions: int = 0
    questions_by_intent: dict[str, int] = field(default_factory=dict)
    average_confidence_score: float = 0.0
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    average_citations_per_answer: float = 0.0
    empty_context_count: int = 0
    empty_context_rate: float = 0.0
    contradiction_rate: float = 0.0
    average_contradiction_count: float = 0.0
    feedback_helpful_count: int = 0
    feedback_not_helpful_count: int = 0
    feedback_incorrect_count: int = 0
    feedback_outdated_count: int = 0
    feedback_total: int = 0
    total_conversations: int = 0


async def get_analytics(
    org_id: str,
    session: AsyncSession,
) -> ConversationAnalytics:
    """Compute analytics for an organisation by querying copilot tables."""
    from infrastructure.persistence.models.copilot import (
        CopilotConversationModel,
        CopilotMessageModel,
    )
    from infrastructure.persistence.models.copilot_audit import CopilotFeedbackModel

    analytics = ConversationAnalytics(organization_id=org_id)

    # Total conversations
    conv_count_stmt = select(func.count()).where(
        CopilotConversationModel.organization_id == org_id,
        CopilotConversationModel.is_archived.is_(False),
    )
    analytics.total_conversations = (
        await session.execute(conv_count_stmt)
    ).scalar_one_or_none() or 0

    # User messages = questions
    user_msg_stmt = select(CopilotMessageModel).where(
        CopilotMessageModel.organization_id == org_id,
        CopilotMessageModel.role == CopilotMessageRole.USER,
    )
    user_rows = (await session.execute(user_msg_stmt)).scalars().all()
    analytics.total_questions = len(user_rows)

    # Intent distribution
    intent_counts: dict[str, int] = {}
    for row in user_rows:
        intent = row.intent or "general"
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
    analytics.questions_by_intent = intent_counts

    # Assistant messages for answer-level analytics
    asst_msg_stmt = select(CopilotMessageModel).where(
        CopilotMessageModel.organization_id == org_id,
        CopilotMessageModel.role == CopilotMessageRole.ASSISTANT,
    )
    asst_rows = (await session.execute(asst_msg_stmt)).scalars().all()
    total_answers = len(asst_rows)

    if total_answers > 0:
        # Confidence distribution
        _level_score = {"Very High": 4, "High": 3, "Moderate": 2, "Low": 1}
        conf_dist: dict[str, int] = {}
        conf_scores: list[float] = []
        citation_counts: list[int] = []
        empty_count = 0
        contradiction_sum = 0

        for row in asst_rows:
            level = row.confidence_level or ""
            conf_dist[level] = conf_dist.get(level, 0) + 1
            score = _level_score.get(level, 0)
            if score > 0:
                conf_scores.append(float(score))

            citations = row.citations or []
            citation_counts.append(len(citations))

            # Empty context = model_used is empty and content is the no-data response
            if not (row.model_used or ""):
                empty_count += 1

            contradiction_sum += row.contradiction_count or 0

        analytics.confidence_distribution = conf_dist
        analytics.average_confidence_score = (
            sum(conf_scores) / len(conf_scores) if conf_scores else 0.0
        )
        analytics.average_citations_per_answer = (
            sum(citation_counts) / len(citation_counts) if citation_counts else 0.0
        )
        analytics.empty_context_count = empty_count
        analytics.empty_context_rate = empty_count / total_answers
        analytics.average_contradiction_count = contradiction_sum / total_answers
        analytics.contradiction_rate = (
            sum(1 for r in asst_rows if (r.contradiction_count or 0) > 0) / total_answers
        )

    # Feedback stats
    feedback_stmt = select(CopilotFeedbackModel).where(
        CopilotFeedbackModel.organization_id == org_id
    )
    fb_rows = (await session.execute(feedback_stmt)).scalars().all()
    for fb in fb_rows:
        r = fb.rating or ""
        if r == "helpful":
            analytics.feedback_helpful_count += 1
        elif r == "not_helpful":
            analytics.feedback_not_helpful_count += 1
        elif r == "incorrect":
            analytics.feedback_incorrect_count += 1
        elif r == "outdated":
            analytics.feedback_outdated_count += 1
    analytics.feedback_total = len(fb_rows)

    return analytics
