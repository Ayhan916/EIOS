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
from datetime import UTC, datetime

import structlog
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
    "ofac": "OFAC Sanktionsliste",
    "eu_sanctions": "EU Konsolidierte Sanktionsliste",
    "un_sanctions": "UN Sicherheitsrat Sanktionen",
    "gdelt_news": "GDELT Globale Nachrichtenintelligenz",
    "gnews": "GNews Nachrichtenintelligenz",
    "transparency_international": "Transparency International CPI",
    "world_bank": "Weltbank Governance-Indikatoren",
    "ilo": "ILO Arbeitnehmerrechtsindex",
    "unicef": "UNICEF Kinderrechts-Risikobewertung",
    "manual": "Manuelle Eingabe",
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
        summary=signal.description or f"{signal_type}-Signal erkannt von {source_display}",
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
    from sqlalchemy import select

    from application.external_intelligence.signal_service import list_signals_for_supplier
    from infrastructure.persistence.models.supplier_digital_twin import (
        IntelligenceTimelineEventModel,
    )

    # Get signals already processed (to avoid re-processing)
    existing_stmt = select(IntelligenceTimelineEventModel.signal_id).where(
        IntelligenceTimelineEventModel.supplier_id == supplier_id,
        IntelligenceTimelineEventModel.organization_id == organization_id,
        IntelligenceTimelineEventModel.signal_id != "",
    )
    existing_signal_ids = {row for row in (await session.execute(existing_stmt)).scalars().all()}

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
        "SANCTIONS": "Sanktionseintrag erkannt",
        "HUMAN_RIGHTS_VIOLATION": "Menschenrechtsverletzung gemeldet",
        "ENVIRONMENTAL_VIOLATION": "Umweltverstoss identifiziert",
        "CORRUPTION": "Korruptionsverdacht erkannt",
        "LABOUR_RIGHTS": "Arbeitnehmerrechtsproblem gemeldet",
        "FINANCIAL_DISTRESS": "Finanzielles Risikosignal",
        "REGULATORY_BREACH": "Regulatorischer Verstoss identifiziert",
        "CYBER_INCIDENT": "Cybersicherheitsvorfall",
        "COUNTRY_RISK": "Länderrisiko erhöht",
        "GEOPOLITICAL": "Geopolitisches Risikoereignis",
        "SUPPLY_CHAIN_DISRUPTION": "Lieferkettenstörung",
        "ESG_CONTROVERSY": "ESG-Kontroverse erkannt",
        "CREDIT_DOWNGRADE": "Kreditrating herabgestuft",
        "DATA_BREACH": "Datenschutzverletzung gemeldet",
        "REGULATORY_INVESTIGATION": "Behördliche Untersuchung eingeleitet",
    }
    label = type_labels.get(signal_type, signal_type.replace("_", " ").title())
    if len(description) <= 60:
        return f"{label}: {description}"
    return label


_REASONING_TEMPLATES: dict[str, dict[str, str]] = {
    "SANCTIONS": {
        "why_important": (
            "Ein Sanktionseintrag begründet direkte rechtliche und finanzielle Verpflichtungen. "
            "Die Fortführung von Geschäftsbeziehungen mit einer sanktionierten Partei kann gegen "
            "nationales und internationales Recht verstossen, Bussgelder auslösen und "
            "Offenlegungspflichten nach CSDDD und LkSG aktivieren."
        ),
        "regulatory_impact": (
            "Betroffen: EU-Dual-Use-Verordnung, OFAC SDN-Compliance, "
            "LkSG §10 (Lieferkettensorgfaltspflichtengesetz), CSDDD Artikel 10. "
            "Sofortige Meldung an Rechts- und Compliance-Teams erforderlich."
        ),
        "recommended_action": (
            "1. Alle laufenden Transaktionen mit diesem Lieferanten einfrieren. "
            "2. Notfall-Rechtsprüfung innerhalb von 24 Stunden einleiten. "
            "3. Compliance-, Rechts- und Einkaufsleitung benachrichtigen. "
            "4. Entscheidung im EIOS-Prüfpfad dokumentieren."
        ),
    },
    "HUMAN_RIGHTS_VIOLATION": {
        "why_important": (
            "Menschenrechtsverletzungen in der Lieferkette begründen direkte Haftung "
            "nach dem Lieferkettensorgfaltspflichtengesetz (LkSG) und der EU CSDDD. "
            "Als grosses Unternehmen unterliegt die Organisation verpflichtenden Sorgfaltspflichten."
        ),
        "regulatory_impact": (
            "Betroffen: LkSG §3 (Sorgfaltspflichten), "
            "CSDDD Artikel 8 (Präventivmassnahmen), "
            "UN-Leitprinzipien für Wirtschaft und Menschenrechte. "
            "Bei Untätigkeit drohen BAFA-Bussgelder von bis zu 2 % des weltweiten Jahresumsatzes."
        ),
        "recommended_action": (
            "1. Erweiterte Sorgfaltsprüfung innerhalb von 30 Tagen einleiten. "
            "2. Korrekturmassnahmenplan vom Lieferanten anfordern. "
            "3. Aussetzung neuer Bestellungen bis zur Klärung prüfen. "
            "4. An den Chief Compliance Officer eskalieren."
        ),
    },
    "ENVIRONMENTAL_VIOLATION": {
        "why_important": (
            "Umweltverstösse gefährden die Reputation und können zu Bussgeldern sowie "
            "Haftung bei der Scope-3-Emissionsberichterstattung nach CSRD führen. "
            "Dies kann Nachhaltigkeits-KPIs und ESG-Ratings beeinträchtigen."
        ),
        "regulatory_impact": (
            "Betroffen: CSRD Artikel 29b (Umweltoffenlegungen), "
            "EU-Taxonomie-Verordnung, LkSG §2 (Umwelt-Sorgfaltspflicht), "
            "CSDDD Kapitel III."
        ),
        "recommended_action": (
            "1. Umweltaudit-Dokumentation beim Lieferanten anfordern. "
            "2. ESG-Bewertung mit neuen Informationen aktualisieren. "
            "3. Umweltmanagementsystem des Lieferanten überprüfen (ISO 14001). "
            "4. Nachhaltigkeitsteam benachrichtigen."
        ),
    },
    "CORRUPTION": {
        "why_important": (
            "Korruptionsvorwürfe begründen Governance-Risiken und mögliche Verstösse "
            "gegen Antikorruptionsgesetze, die für die Organisation gelten."
        ),
        "regulatory_impact": (
            "Betroffen: Deutsches Antikorruptionsrecht, "
            "UK Bribery Act (sofern anwendbar), "
            "FCPA (bei US-Geschäftstätigkeit), "
            "ISO 37001 Antikorruptions-Managementsystem."
        ),
        "recommended_action": (
            "1. Antikorruptions-Sorgfaltsprüfung einleiten. "
            "2. Neue Auftragsvergaben bis zur Untersuchung aussetzen. "
            "3. Bestehende Antikorruptionsklauseln in Verträgen überprüfen. "
            "4. Rechts- und Interne-Revision-Abteilung benachrichtigen."
        ),
    },
    "FINANCIAL_DISTRESS": {
        "why_important": (
            "Finanzkrisensignale weisen auf potenzielle Lieferkettenunterbrechungsrisiken hin. "
            "Eine Insolvenz des Lieferanten könnte die Produktion stoppen und "
            "Vertragsstrafen in bestehenden Vereinbarungen auslösen."
        ),
        "regulatory_impact": (
            "Kein direkter Regelungsverstoss, aber Betriebskontinuitätspflichten "
            "gelten nach ISO 31000 und internen Risikomanagement-Rahmenwerken."
        ),
        "recommended_action": (
            "1. Aktuelle geprüfte Jahresabschlüsse anfordern. "
            "2. Alternativlieferanten für kritische Komponenten identifizieren. "
            "3. Lieferketten-Notfallpläne prüfen und aktivieren. "
            "4. Einkaufs- und Betriebsleitung benachrichtigen."
        ),
    },
    "SUPPLY_CHAIN_DISRUPTION": {
        "why_important": (
            "Lieferkettenstörungen können die Produktionskontinuität gefährden "
            "und erfordern sofortige Massnahmen zur Risikominimierung."
        ),
        "regulatory_impact": (
            "Betroffen: LkSG §4 (Präventionsmassnahmen), "
            "ISO 31000 Risikomanagement, interne Business-Continuity-Vorgaben."
        ),
        "recommended_action": (
            "1. Betroffene Liefermengen und Auswirkungen auf die Produktion bewerten. "
            "2. Alternativlieferanten aktivieren und Lagerbestände prüfen. "
            "3. Kunden und interne Stakeholder über mögliche Verzögerungen informieren. "
            "4. Business-Continuity-Plan aktivieren."
        ),
    },
}

_DEFAULT_REASONING = {
    "why_important": (
        "Dieses externe Intelligenzsignal deutet auf einen potenziellen Risikofaktor "
        "für diesen Lieferanten hin, der die Lieferkettenintegrität, "
        "Compliance-Stellung oder ESG-Performance der Organisation beeinträchtigen könnte."
    ),
    "regulatory_impact": (
        "Relevante LkSG-, CSDDD- und CSRD-Verpflichtungen prüfen, um festzustellen, "
        "ob formelle Sorgfaltsprüfungsschritte erforderlich sind."
    ),
    "recommended_action": (
        "1. Vollständige Signaldetails in der Intelligence-Timeline prüfen. "
        "2. Dem verantwortlichen Team zur Bewertung zuweisen. "
        "3. Reaktion im EIOS für Prüfzwecke dokumentieren."
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
            f"Du bist ein Enterprise-Risikointelligenz-Analyst.\n"
            f"Signal: {signal_type}, Schweregrad: {severity}\n"
            f"Beschreibung: {signal.description}\n"
            f"Quelle: {source_display}\n"
            f"Land: {signal.country_code or 'Unbekannt'}\n\n"
            f"Erstelle ein JSON mit den Schlüsseln: why_important, regulatory_impact, recommended_action.\n"
            f"Jeder Wert ist 1-3 Sätze auf Deutsch. Fokus auf EU/deutschen Regulierungskontext (LkSG, CSDDD, CSRD).\n"
            f"Sei spezifisch und handlungsorientiert. Gib NUR das JSON-Objekt zurück."
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
        existing = (
            await session.execute(
                select(RecommendationModel)
                .where(RecommendationModel.description.contains(event.signal_id))
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return

        from uuid import uuid4

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
