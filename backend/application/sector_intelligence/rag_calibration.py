"""
CSDDD Sector Risk Register — RAG Calibration Pipeline (TASK-003 Phase 3)

Uses pgvector knowledge search + Groq LLM to suggest probability scores for
NACE sector × CSDDD right pairs from ILO/OECD source documents.

Flow:
  1. Query pgvector for chunks relevant to (sector, right)
  2. Pass chunks as context to Groq LLM
  3. Parse structured JSON response → CalibrationSuggestion
  4. Persist suggestion (status=pending) — never auto-apply
  5. Founder reviews via /calibrate/{id}/approve or /calibrate/{id}/reject
  6. On approval: write to sector_right_scores table

M43 compliance: LLM is used ONLY here for calibration, never for live scoring.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from application.ports.llm import LLMProvider, Message
from domain.enums import CalibrationStatus, CSDDDRight, ConfidenceLevel

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt template — structured JSON output enforced
# ---------------------------------------------------------------------------

_CALIBRATION_PROMPT = """\
You are an ESG and human rights due diligence expert specialising in CSDDD \
(Corporate Sustainability Due Diligence Directive) sector risk analysis.

Your task: estimate the PROBABILITY that suppliers in NACE sector {nace_code} \
({sector_name}) are involved in violations of the following CSDDD protected right:
"{right_name}"

Base your estimate on the following excerpts from ILO reports, OECD guidance, \
and sector risk literature:

---
{context}
---

Scale: 1 = very unlikely (structural absence of this risk in the sector)
       5 = moderate (some inherent exposure, sector has documented cases)
      10 = near-certain (systemic, pervasive, well-documented in literature)

Respond ONLY in this exact JSON format (no markdown, no explanation outside JSON):
{{
  "probability": <integer 1-10>,
  "confidence": "<Low|Medium|High>",
  "reasoning": "<max 250 characters explaining the score>",
  "key_sources": ["<source title 1>", "<source title 2>"]
}}"""

_RIGHT_DISPLAY_NAMES: dict[CSDDDRight, str] = {
    CSDDDRight.CHILD_LABOUR: "Child Labour (ILO C138, C182)",
    CSDDDRight.FORCED_LABOUR: "Forced Labour (ILO C029, C105)",
    CSDDDRight.FREEDOM_OF_ASSOCIATION: "Freedom of Association (ILO C087)",
    CSDDDRight.COLLECTIVE_BARGAINING: "Collective Bargaining (ILO C098)",
    CSDDDRight.DISCRIMINATION: "Non-Discrimination (ILO C100, C111)",
    CSDDDRight.MINIMUM_WAGE: "Minimum Wage (ILO C131)",
    CSDDDRight.WORKING_HOURS: "Working Hours (ILO C001)",
    CSDDDRight.OCCUPATIONAL_SAFETY: "Occupational Safety (ILO C155, C187)",
    CSDDDRight.LAND_RIGHTS: "Land Rights (UNDRIP, VGGT)",
    CSDDDRight.WATER_RIGHTS: "Right to Water (UN A/RES/64/292)",
    CSDDDRight.ENVIRONMENTAL_DESTRUCTION: "Environmental Destruction",
    CSDDDRight.HARMFUL_CHEMICALS: "Harmful Chemicals (Stockholm/Rotterdam)",
    CSDDDRight.BIODIVERSITY: "Biodiversity (CBD)",
    CSDDDRight.MERCURY: "Mercury (Minamata Convention)",
    CSDDDRight.HAZARDOUS_WASTE: "Hazardous Waste (Basel Convention)",
    CSDDDRight.PRIVACY: "Right to Privacy (ICCPR Art. 17)",
    CSDDDRight.FREEDOM_OF_EXPRESSION: "Freedom of Expression (ICCPR Art. 19)",
    CSDDDRight.HUMAN_DIGNITY: "Human Dignity (UDHR Art. 1)",
    CSDDDRight.MODERN_SLAVERY: "Modern Slavery (Palermo Protocol)",
    CSDDDRight.MIGRANT_WORKER_RIGHTS: "Migrant Worker Rights (ICRMW)",
    CSDDDRight.COMMUNITY_RIGHTS: "Community Rights (ILO C169, UNDRIP)",
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class CalibrationSuggestionDTO:
    """In-memory representation before DB persistence."""

    def __init__(
        self,
        id: str,
        nace_2digit: str,
        csddd_right: CSDDDRight,
        suggested_probability: int,
        confidence: ConfidenceLevel,
        reasoning: str,
        sources: list[str],
        status: CalibrationStatus = CalibrationStatus.PENDING,
        created_at: str = "",
    ) -> None:
        self.id = id
        self.nace_2digit = nace_2digit
        self.csddd_right = csddd_right
        self.suggested_probability = suggested_probability
        self.confidence = confidence
        self.reasoning = reasoning
        self.sources = sources
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class SectorRiskCalibrationPipeline:
    """RAG-based calibration pipeline for CSDDD sector risk scores.

    Requires an LLMProvider (Groq) and a knowledge_search callable that
    returns a list of chunk dicts with at least {"text": str, "evidence_title": str}.
    """

    def __init__(
        self,
        llm: LLMProvider,
        knowledge_search: Any,  # KnowledgeSearchPort.search coroutine
    ) -> None:
        self._llm = llm
        self._knowledge_search = knowledge_search

    async def calibrate(
        self,
        nace_2digit: str,
        right: CSDDDRight,
    ) -> CalibrationSuggestionDTO:
        """Run RAG + LLM calibration for one NACE × right pair.

        Returns a CalibrationSuggestionDTO with status=PENDING.
        Never persisted automatically — caller must save to DB.
        """
        from application.sector_intelligence.nace_taxonomy import get_division_name

        sector_name = get_division_name(nace_2digit)
        right_name = _RIGHT_DISPLAY_NAMES[right]

        # 1. Semantic search in pgvector knowledge base
        query = (
            f"{sector_name} sector {right.value.replace('_', ' ')} "
            f"risk probability CSDDD human rights due diligence"
        )
        try:
            chunks = await self._knowledge_search(query, limit=6)
        except Exception as exc:
            logger.warning("rag_calibration_search_failed", error=str(exc))
            chunks = []

        # 2. Build context from retrieved chunks
        if chunks:
            context_parts = []
            for chunk in chunks:
                title = getattr(chunk, "evidence_title", "") or chunk.get("evidence_title", "")
                text = getattr(chunk, "text", "") or chunk.get("text", "")
                if text:
                    context_parts.append(f"[{title}]\n{text[:600]}")
            context = "\n\n".join(context_parts)
            chunk_sources = list({
                getattr(c, "evidence_title", None) or c.get("evidence_title", "")
                for c in chunks
                if getattr(c, "evidence_title", None) or c.get("evidence_title", "")
            })
        else:
            # No documents in knowledge base yet — LLM uses parametric knowledge
            context = (
                "No specific documents found in knowledge base. "
                "Use your general knowledge of ILO reports and OECD HRDD guidance."
            )
            chunk_sources = ["LLM parametric knowledge (no RAG documents available)"]

        # 3. Call LLM
        prompt = _CALIBRATION_PROMPT.format(
            nace_code=nace_2digit,
            sector_name=sector_name,
            right_name=right_name,
            context=context,
        )
        try:
            response = await self._llm.complete(
                [Message(role="user", content=prompt)],
                max_tokens=512,
                temperature=0.0,
            )
            parsed = self._parse_response(response.content)
        except Exception as exc:
            logger.error("rag_calibration_llm_failed", error=str(exc))
            # Fallback: return a low-confidence suggestion based on global average
            parsed = {
                "probability": 4,
                "confidence": "Low",
                "reasoning": f"LLM call failed ({exc!s:.100}). Fallback to global average.",
                "key_sources": [],
            }

        probability = max(1, min(10, int(parsed.get("probability", 4))))
        confidence_str = str(parsed.get("confidence", "Low")).capitalize()
        try:
            confidence = ConfidenceLevel(confidence_str)
        except ValueError:
            confidence = ConfidenceLevel.LOW

        reasoning = str(parsed.get("reasoning", ""))[:500]
        llm_sources = parsed.get("key_sources", [])
        all_sources = list({*chunk_sources, *llm_sources})

        suggestion = CalibrationSuggestionDTO(
            id=str(uuid.uuid4()),
            nace_2digit=nace_2digit,
            csddd_right=right,
            suggested_probability=probability,
            confidence=confidence,
            reasoning=reasoning,
            sources=all_sources[:5],
        )

        logger.info(
            "rag_calibration_suggestion_created",
            nace=nace_2digit,
            right=right.value,
            probability=probability,
            confidence=confidence.value,
            rag_chunks=len(chunks),
        )
        return suggestion

    def _parse_response(self, content: str) -> dict:
        """Extract JSON from LLM response, tolerating minor formatting issues."""
        content = content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object within the response
            import re
            match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        logger.warning("rag_calibration_parse_failed", content_preview=content[:200])
        return {}


# ---------------------------------------------------------------------------
# DB persistence helpers (called from router with active SQLAlchemy session)
# ---------------------------------------------------------------------------

async def save_suggestion(dto: CalibrationSuggestionDTO, session: Any) -> str:
    """Persist a CalibrationSuggestionDTO to the calibration_suggestions table."""
    from infrastructure.persistence.models.sector_risk_register import CalibrationSuggestionModel

    now = datetime.now(timezone.utc)
    model = CalibrationSuggestionModel(
        id=dto.id,
        status=CalibrationStatus.PENDING.value,
        version=1,
        created_at=now,
        updated_at=now,
        nace_2digit=dto.nace_2digit,
        csddd_right=dto.csddd_right.value,
        suggested_probability=dto.suggested_probability,
        confidence=dto.confidence.value,
        reasoning=dto.reasoning,
        sources=dto.sources,
    )
    session.add(model)
    await session.flush()
    return dto.id


async def approve_suggestion(
    suggestion_id: str,
    reviewer_id: str,
    session: Any,
) -> bool:
    """Approve a pending suggestion → write to sector_right_scores."""
    from sqlalchemy import select
    from infrastructure.persistence.models.sector_risk_register import (
        CalibrationSuggestionModel,
        SectorRightScoreModel,
    )
    from application.sector_intelligence.base_matrix import CALIBRATION_VERSION

    result = await session.execute(
        select(CalibrationSuggestionModel).where(
            CalibrationSuggestionModel.id == suggestion_id,
            CalibrationSuggestionModel.status == CalibrationStatus.PENDING.value,
        )
    )
    model = result.scalar_one_or_none()
    if model is None:
        return False

    now = datetime.now(timezone.utc)
    model.status = CalibrationStatus.APPROVED.value
    model.reviewed_by = reviewer_id
    model.reviewed_at = now
    model.updated_at = now

    # Write to sector_right_scores
    score_model = SectorRightScoreModel(
        id=str(uuid.uuid4()),
        status="Active",
        version=1,
        created_at=now,
        updated_at=now,
        nace_2digit=model.nace_2digit,
        csddd_right=model.csddd_right,
        probability=model.suggested_probability,
        confidence=model.confidence,
        sources=model.sources,
        calibration_version=CALIBRATION_VERSION,
        approved_by=reviewer_id,
        approved_at=now,
    )
    session.add(score_model)
    await session.flush()

    logger.info(
        "calibration_suggestion_approved",
        suggestion_id=suggestion_id,
        nace=model.nace_2digit,
        right=model.csddd_right,
        probability=model.suggested_probability,
        reviewer=reviewer_id,
    )
    return True


async def reject_suggestion(
    suggestion_id: str,
    reviewer_id: str,
    reason: str,
    session: Any,
) -> bool:
    """Reject a pending calibration suggestion."""
    from sqlalchemy import select
    from infrastructure.persistence.models.sector_risk_register import CalibrationSuggestionModel

    result = await session.execute(
        select(CalibrationSuggestionModel).where(
            CalibrationSuggestionModel.id == suggestion_id,
            CalibrationSuggestionModel.status == CalibrationStatus.PENDING.value,
        )
    )
    model = result.scalar_one_or_none()
    if model is None:
        return False

    now = datetime.now(timezone.utc)
    model.status = CalibrationStatus.REJECTED.value
    model.reviewed_by = reviewer_id
    model.reviewed_at = now
    model.rejection_reason = reason[:500]
    model.updated_at = now
    await session.flush()
    return True


async def list_suggestions(
    status: CalibrationStatus | None,
    session: Any,
    limit: int = 50,
) -> list[CalibrationSuggestionModel]:
    from sqlalchemy import select
    from infrastructure.persistence.models.sector_risk_register import CalibrationSuggestionModel

    stmt = select(CalibrationSuggestionModel).order_by(
        CalibrationSuggestionModel.created_at.desc()
    ).limit(limit)
    if status is not None:
        stmt = stmt.where(CalibrationSuggestionModel.status == status.value)
    result = await session.execute(stmt)
    return list(result.scalars().all())
