"""G-056 — AI-assisted risk draft Celery task.

Given a surveillance signal, calls the configured LLM to produce a structured
risk description (title, severity, category, likelihood, explanation).
The result is saved as a RiskDraft record with review_status="pending".

SECURITY INVARIANT:
  - This task ONLY creates RiskDraft records — it NEVER creates Risk records.
  - Human promotion via POST /risks/drafts/{id}/accept is the ONLY path to a real Risk.
  - The LLM output is stored verbatim and is NOT applied directly to any business entity.

The draft includes a prompt_hash (SHA-256 of the full prompt) for reproducibility auditing.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)

_DRAFT_SYSTEM_PROMPT = """You are an ESG risk analyst assistant. Given a surveillance signal,
produce a concise structured risk assessment draft for human review.

Output ONLY valid JSON with this exact schema:
{
  "title": "<concise risk title, max 120 chars>",
  "description": "<2-4 sentence risk description>",
  "severity": "<Critical|High|Medium|Low>",
  "category": "<category e.g. Regulatory, Environmental, Social, Governance, Operational, Reputational>",
  "likelihood": "<High|Medium|Low>"
}

Rules:
- Be factual. Do not extrapolate beyond the signal.
- Severity=Critical only when regulatory fine or license revocation is likely.
- This is a DRAFT for human review — do not overstate certainty."""


@celery_app.task(
    bind=True,
    name="eios.risk_drafts.generate",
    max_retries=2,
    default_retry_delay=60,
)
def generate_risk_draft_task(
    self,
    signal_id: str,
    organization_id: str,
    supplier_id: str | None,
    signal_description: str,
    signal_type: str,
    signal_severity: str,
    actor_id: str,
) -> dict[str, object]:
    """Generate an AI risk draft from a surveillance signal."""
    try:
        return asyncio.run(
            _run_draft_generation(
                signal_id=signal_id,
                organization_id=organization_id,
                supplier_id=supplier_id,
                signal_description=signal_description,
                signal_type=signal_type,
                signal_severity=signal_severity,
                actor_id=actor_id,
            )
        )
    except Exception as exc:
        logger.error("risk_draft_failed", signal_id=signal_id, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_draft_generation(
    *,
    signal_id: str,
    organization_id: str,
    supplier_id: str | None,
    signal_description: str,
    signal_type: str,
    signal_severity: str,
    actor_id: str,
) -> dict[str, object]:
    from application.ports.llm import Message  # noqa: PLC0415
    from infrastructure.llm.deps import init_llm_provider  # noqa: PLC0415
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.models.m46_3 import RiskDraftModel  # noqa: PLC0415

    user_prompt = (
        f"Signal type: {signal_type}\n"
        f"Signal severity: {signal_severity}\n"
        f"Description: {signal_description}\n\n"
        "Produce a risk draft JSON for this signal."
    )

    prompt_hash = hashlib.sha256((_DRAFT_SYSTEM_PROMPT + user_prompt).encode()).hexdigest()

    llm = init_llm_provider()
    response = await llm.complete(
        messages=[Message(role="user", content=user_prompt)],
        system=_DRAFT_SYSTEM_PROMPT,
        max_tokens=512,
        temperature=0.0,
    )

    # Parse LLM JSON output
    try:
        raw = response.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
    except (json.JSONDecodeError, IndexError) as exc:
        logger.error("risk_draft_parse_failed", error=str(exc), raw=response.content[:200])
        raise ValueError(f"LLM response was not valid JSON: {exc}") from exc

    now = datetime.now(UTC)
    draft = RiskDraftModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        supplier_id=supplier_id,
        signal_id=signal_id,
        draft_title=str(parsed.get("title", ""))[:500],
        draft_description=str(parsed.get("description", "")),
        draft_severity=str(parsed.get("severity", "Medium")),
        draft_category=str(parsed.get("category", "")) or None,
        draft_likelihood=str(parsed.get("likelihood", "")) or None,
        llm_model=response.model,
        llm_prompt_hash=prompt_hash,
        review_status="pending",
        reviewed_by=None,
        reviewed_at=None,
        promoted_risk_id=None,
        created_at=now,
    )

    async with AsyncSessionFactory() as session, session.begin():
        session.add(draft)

    logger.info(
        "risk_draft_created",
        draft_id=draft.id,
        signal_id=signal_id,
        severity=draft.draft_severity,
    )
    return {
        "draft_id": draft.id,
        "review_status": "pending",
        "draft_title": draft.draft_title,
        "draft_severity": draft.draft_severity,
    }
