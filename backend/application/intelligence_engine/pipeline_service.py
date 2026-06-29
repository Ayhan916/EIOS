"""Intelligence Pipeline Service — M50.

Transforms ExternalRiskSignals into Supplier Digital Twin updates.

Pipeline:
  ExternalRiskSignal
  ↓ resolve affected supplier
  ↓ classify → event_type + event_category
  ↓ compute health impact (deterministic)
  ↓ generate AI reasoning (why_important, regulatory_impact, recommended_action)
  ↓ append IntelligenceTimelineEvent
  ↓ update SupplierDigitalTwin health dimensions
  ↓ create Recommendation (if severity >= HIGH)
  ↓ create Notifications

AI reasoning uses Claude but the SCORE UPDATE is always deterministic.
See health_engine.py for the full deterministic mapping table.
"""

from __future__ import annotations

import json
import structlog
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.external_intelligence import ExternalRiskSignal
from domain.supplier_digital_twin import IntelligenceTimelineEvent

from .health_engine import (
    compute_delta,
    resolve_category,
    resolve_dimension,
)
from .timeline_service import append_event
from .twin_service import update_twin_health

logger = structlog.get_logger(__name__)

# Severity levels that trigger recommendations
_RECOMMENDATION_THRESHOLD = {"CRITICAL", "HIGH"}

# Source name normalisation
_SOURCE_DISPLAY: dict[str, str] = {
    "ofac": "OFAC Sanctions List",
    "eu_sanctions": "EU Consolidated Sanctions List",
    "un_sanctions": "UN Security Council Sanctions",
    "gdelt_news": "GDELT Global News Intelligence",
    "transparency_international": "Transparency International CPI",
    "world_bank": "World Bank Governance Indicators",
    "ilo": "ILO Labour Rights Index",
    "unicef": "UNICEF Child Risk Assessment",
    "manual": "Manual Intelligence Entry",
}

_SOURCE_URL: dict[str, str] = {
    "ofac": "https://ofac.treasury.gov/specially-designated-nationals-list-sdn",
    "eu_sanctions": "https://webgate.ec.europa.eu/fsd/fsf/",
    "un_sanctions": "https://www.un.org/securitycouncil/content/un-sc-consolidated-list",
    "world_bank": "https://databank.worldbank.org/source/worldwide-governance-indicators",
    "gdelt_news": "",  # per-article URL embedded in signal description
}


async def process_signal(
    signal: ExternalRiskSignal,
    session: AsyncSession,
) -> IntelligenceTimelineEvent | None:
    """Run the full intelligence pipeline for one ExternalRiskSignal.

    Returns the created IntelligenceTimelineEvent, or None if the signal
    does not have a supplier_id (country-level signals are not yet processed
    into twin events — that is a future enhancement).
    """
    if not signal.supplier_id:
        # Country-level signals: skip twin update (no supplier resolution yet)
        return None

    signal_type = signal.signal_type.upper() if signal.signal_type else "OTHER"
    severity = signal.severity.upper() if signal.severity else "MEDIUM"

    # Deterministic: dimension + delta
    dimension = resolve_dimension(signal_type)
    delta = compute_delta(severity, signal_type)
    category = resolve_category("EXTERNAL_SIGNAL", signal_type)

    source_key = (signal.source_name or "").lower()
    source_display = _SOURCE_DISPLAY.get(source_key, signal.source_name or "External Source")

    # Resolve source URL: static for known sources, extract from GDELT description
    source_url = _SOURCE_URL.get(source_key, "")
    if source_key == "gdelt_news" and signal.description:
        # Description format: "News signal: "...". Published: ... Source URL: https://..."
        import re as _re
        _m = _re.search(r"Source URL:\s*(https?://\S+)", signal.description)
        if _m:
            source_url = _m.group(1)

    # Generate AI reasoning (non-blocking — if LLM is unavailable, use templates)
    reasoning = await _generate_reasoning(signal, dimension, severity, source_display)

    # Build timeline event
    event = IntelligenceTimelineEvent(
        supplier_id=signal.supplier_id,
        organization_id=signal.organization_id,
        event_type="EXTERNAL_SIGNAL",
        event_category=category,
        severity=severity,
        title=_build_title(signal_type, severity, signal.description),
        summary=signal.description or f"{signal_type} signal detected from {source_display}",
        why_important=reasoning["why_important"],
        regulatory_impact=reasoning["regulatory_impact"],
        recommended_action=reasoning["recommended_action"],
        source_type="EXTERNAL_DATASET",
        source_name=source_display,
        source_url=source_url,
        evidence_ids="[]",
        regulation_ids="[]",
        risk_ids="[]",
        signal_id=signal.id,
        twin_dimension_affected=dimension,
        health_delta=delta,
        confidence=0.75,
        occurred_at=signal.observed_at or datetime.now(UTC),
        processed_at=datetime.now(UTC),
        is_active=True,
        status=EntityStatus.ACTIVE,
    )

    # Persist timeline event
    event = await append_event(event, session)

    # Update twin health (deterministic)
    await update_twin_health(
        supplier_id=signal.supplier_id,
        organization_id=signal.organization_id,
        dimension=dimension,
        delta=delta,
        session=session,
        severity=severity,
    )

    # Create recommendation for HIGH/CRITICAL events
    if severity in _RECOMMENDATION_THRESHOLD:
        await _create_recommendation(event, session)

    logger.info(
        "intelligence_pipeline.signal_processed",
        supplier_id=signal.supplier_id,
        signal_type=signal_type,
        severity=severity,
        dimension=dimension,
        delta=delta,
        event_id=event.id,
    )

    return event


async def process_signals_for_supplier(
    supplier_id: str,
    organization_id: str,
    session: AsyncSession,
) -> list[IntelligenceTimelineEvent]:
    """Process all unprocessed signals for a supplier through the pipeline."""
    from application.external_intelligence.signal_service import list_signals_for_supplier
    from infrastructure.persistence.models.supplier_digital_twin import IntelligenceTimelineEventModel
    from sqlalchemy import select

    # Get signals already processed (to avoid re-processing)
    existing_stmt = select(IntelligenceTimelineEventModel.signal_id).where(
        IntelligenceTimelineEventModel.supplier_id == supplier_id,
        IntelligenceTimelineEventModel.organization_id == organization_id,
        IntelligenceTimelineEventModel.signal_id != "",
    )
    existing_signal_ids = {
        row for row in (await session.execute(existing_stmt)).scalars().all()
    }

    signals = await list_signals_for_supplier(
        supplier_id=supplier_id,
        organization_id=organization_id,
        session=session,
        active_only=True,
    )

    created: list[IntelligenceTimelineEvent] = []
    for signal in signals:
        if signal.id in existing_signal_ids:
            continue
        event = await process_signal(signal, session)
        if event:
            created.append(event)

    return created


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_title(signal_type: str, severity: str, description: str) -> str:
    """Build a concise event title from signal metadata."""
    type_labels = {
        "SANCTIONS": "Sanctions Listing Detected",
        "HUMAN_RIGHTS_VIOLATION": "Human Rights Violation Reported",
        "ENVIRONMENTAL_VIOLATION": "Environmental Violation Identified",
        "CORRUPTION": "Corruption Allegation Detected",
        "LABOUR_RIGHTS": "Labour Rights Issue Flagged",
        "FINANCIAL_DISTRESS": "Financial Distress Signal",
        "REGULATORY_BREACH": "Regulatory Breach Identified",
        "CYBER_INCIDENT": "Cyber Security Incident",
        "COUNTRY_RISK": "Country Risk Elevation",
        "GEOPOLITICAL": "Geopolitical Risk Event",
        "SUPPLY_CHAIN_DISRUPTION": "Supply Chain Disruption",
        "ESG_CONTROVERSY": "ESG Controversy Detected",
        "CREDIT_DOWNGRADE": "Credit Rating Downgrade",
        "DATA_BREACH": "Data Breach Reported",
        "REGULATORY_INVESTIGATION": "Regulatory Investigation Opened",
    }
    label = type_labels.get(signal_type, signal_type.replace("_", " ").title())
    if len(description) <= 60:
        return f"{label}: {description}"
    return label


_REASONING_TEMPLATES: dict[str, dict[str, str]] = {
    "SANCTIONS": {
        "why_important": (
            "Sanctions exposure creates direct legal and financial obligations. "
            "Continued business with a sanctioned entity may violate national and "
            "international law, expose the organisation to fines, and trigger "
            "mandatory disclosure requirements under CSDDD and LkSG."
        ),
        "regulatory_impact": (
            "Affected: EU Dual-Use Regulation, OFAC SDN compliance, "
            "LkSG §10 (Germany Supply Chain Act), CSDDD Article 10. "
            "Immediate reporting to legal and compliance teams required."
        ),
        "recommended_action": (
            "1. Freeze all pending transactions with this supplier. "
            "2. Initiate emergency legal review within 24 hours. "
            "3. Notify Compliance, Legal, and Procurement leadership. "
            "4. Document the decision in the EIOS audit trail."
        ),
    },
    "HUMAN_RIGHTS_VIOLATION": {
        "why_important": (
            "Human rights violations in the supply chain create direct liability "
            "under the German Supply Chain Act (LkSG) and the forthcoming EU CSDDD. "
            "BMW AG as a large enterprise faces mandatory due diligence obligations."
        ),
        "regulatory_impact": (
            "Affected: LkSG §3 (due diligence obligations), "
            "CSDDD Article 8 (preventive action), "
            "UN Guiding Principles on Business and Human Rights. "
            "Failure to act may result in BaFa fines up to 2% of global turnover."
        ),
        "recommended_action": (
            "1. Initiate enhanced due diligence assessment within 30 days. "
            "2. Request corrective action plan from the supplier. "
            "3. Consider suspension of new purchase orders pending review. "
            "4. Escalate to Chief Compliance Officer."
        ),
    },
    "ENVIRONMENTAL_VIOLATION": {
        "why_important": (
            "Environmental violations expose the organisation to reputational damage, "
            "regulatory fines, and potential liability for scope 3 emissions reporting "
            "under CSRD. This may affect sustainability KPIs and ESG ratings."
        ),
        "regulatory_impact": (
            "Affected: CSRD Article 29b (environmental disclosures), "
            "EU Taxonomy Regulation, LkSG §2 (environmental due diligence), "
            "CSDDD Chapter III."
        ),
        "recommended_action": (
            "1. Request environmental audit documentation from supplier. "
            "2. Update ESG assessment to reflect new information. "
            "3. Review supplier's environmental management system (ISO 14001). "
            "4. Notify Sustainability team."
        ),
    },
    "CORRUPTION": {
        "why_important": (
            "Corruption allegations trigger governance risk and potential violation "
            "of anti-bribery laws applicable to the organisation."
        ),
        "regulatory_impact": (
            "Affected: German Anti-Corruption Law, "
            "UK Bribery Act (if applicable), "
            "FCPA (if US operations involved), "
            "ISO 37001 Anti-bribery management."
        ),
        "recommended_action": (
            "1. Initiate anti-corruption due diligence review. "
            "2. Suspend new contract awards pending investigation. "
            "3. Review existing contractual anti-corruption clauses. "
            "4. Notify Legal and Internal Audit."
        ),
    },
    "FINANCIAL_DISTRESS": {
        "why_important": (
            "Financial distress signals indicate potential supply chain disruption "
            "risk. Supplier insolvency could halt production and trigger penalty "
            "clauses in existing contracts."
        ),
        "regulatory_impact": (
            "No direct regulatory breach, but operational continuity obligations "
            "apply under ISO 31000 and internal risk management frameworks."
        ),
        "recommended_action": (
            "1. Request latest audited financial statements. "
            "2. Identify alternative suppliers for critical components. "
            "3. Review and activate supply chain contingency plans. "
            "4. Notify Procurement and Operations leadership."
        ),
    },
}

_DEFAULT_REASONING = {
    "why_important": (
        "This external intelligence signal indicates a potential risk factor for "
        "this supplier that may affect BMW AG's supply chain integrity, compliance "
        "posture, or ESG performance."
    ),
    "regulatory_impact": (
        "Review relevant LkSG, CSDDD, and CSRD obligations to determine "
        "whether formal due diligence steps are required."
    ),
    "recommended_action": (
        "1. Review the full signal details in the intelligence timeline. "
        "2. Assign to the responsible team for assessment. "
        "3. Document response in EIOS for audit trail purposes."
    ),
}


async def _generate_reasoning(
    signal: ExternalRiskSignal,
    dimension: str,
    severity: str,
    source_display: str,
) -> dict[str, str]:
    """Generate AI reasoning for a signal.

    Uses pre-defined templates for common signal types (fast, deterministic).
    Falls back to LLM generation for uncommon types when API key is available.
    """
    signal_type = (signal.signal_type or "OTHER").upper()
    template = _REASONING_TEMPLATES.get(signal_type, _DEFAULT_REASONING)

    # Try to enrich with LLM if available (non-blocking)
    try:
        from infrastructure.llm.deps import get_llm_provider
        provider = get_llm_provider()
        if provider is None:
            return template

        prompt = (
            f"You are an enterprise risk intelligence analyst at BMW AG.\n"
            f"Signal: {signal_type}, Severity: {severity}\n"
            f"Description: {signal.description}\n"
            f"Source: {source_display}\n"
            f"Country: {signal.country_code or 'Unknown'}\n\n"
            f"Provide a JSON with keys: why_important, regulatory_impact, recommended_action.\n"
            f"Each value is 1-3 sentences. Focus on EU/German regulatory context (LkSG, CSDDD, CSRD).\n"
            f"Be specific and actionable. Return ONLY the JSON object."
        )

        result = await provider.complete(
            prompt=prompt,
            max_tokens=400,
            temperature=0.2,
        )
        parsed = json.loads(result.strip())
        if all(k in parsed for k in ("why_important", "regulatory_impact", "recommended_action")):
            return parsed
    except Exception:
        pass  # Fall through to template

    return template


async def _create_recommendation(
    event: IntelligenceTimelineEvent,
    session: AsyncSession,
) -> None:
    """Create a Recommendation from an intelligence event (if service available)."""
    try:
        from sqlalchemy import select
        from infrastructure.persistence.models.recommendation import RecommendationModel

        # Avoid duplicate recommendations for the same signal
        existing = (await session.execute(
            select(RecommendationModel).where(
                RecommendationModel.description.contains(event.signal_id)
            ).limit(1)
        )).scalar_one_or_none()
        if existing:
            return

        from uuid import uuid4
        from datetime import date

        rec = RecommendationModel(
            id=str(uuid4()),
            status="Draft",
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            organization_id=event.organization_id,
            title=f"[Intelligence] {event.title}",
            description=(
                f"External intelligence event detected (Signal: {event.signal_id}).\n\n"
                f"{event.recommended_action}"
            ),
            priority=event.severity,
            category="EXTERNAL_INTELLIGENCE",
            supplier_id=event.supplier_id,
        )
        session.add(rec)
        await session.flush()
    except Exception as exc:
        logger.warning("intelligence_pipeline.recommendation_failed", error=str(exc))
