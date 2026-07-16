"""EIOS Intelligence Activator

Bridges company_signals (extracted from documents) into the Digital Twin
timeline and surveillance_signals table.

This makes all 714+ BMW document signals visible in:
  - Supplier Twin: timeline events, health score, dimensions
  - Surveillance: active signals tab
  - Intelligence: enriched with AI reasoning per event
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.supplier_digital_twin import IntelligenceTimelineEvent

logger = structlog.get_logger(__name__)

# ── Dimension mapping: company_signal.dimension → twin health dimension ───────
_DIMENSION_MAP: dict[str, str] = {
    "financial":    "financial_health",
    "esg":          "esg_health",
    "governance":   "governance_health",
    "supply_chain": "operational_health",
    "regulatory":   "compliance_health",
    "reputation":   "esg_health",
}

# ── Severity delta: positive direction inverts sign ────────────────────────────
_SEV_DELTA: dict[str, float] = {
    "critical": -15.0,
    "high":     -8.0,
    "medium":   -3.0,
    "low":      -1.0,
}

_CATEGORY_MAP: dict[str, str] = {
    "financial":    "FINANCIAL",
    "esg":          "ESG",
    "governance":   "COMPLIANCE",
    "supply_chain": "OPERATIONAL",
    "regulatory":   "COMPLIANCE",
    "reputation":   "ESG",
}

_POSITIVE_DIRECTIONS = {"up", "positive"}
_SURV_THRESHOLD = {"critical", "high"}


def _dedupe_key(supplier_id: str, signal_id: str) -> str:
    return hashlib.sha256(f"cs:{supplier_id}:{signal_id}".encode()).hexdigest()[:64]


def _delta(severity: str, direction: str) -> float:
    base = _SEV_DELTA.get(severity.lower(), -2.0)
    if direction.lower() in _POSITIVE_DIRECTIONS:
        base = abs(base) * 0.5  # positive events give half the magnitude
    return base


async def _llm_reasoning(signal_type: str, dimension: str, severity: str, description: str) -> dict[str, str]:
    try:
        from infrastructure.llm.deps import get_llm_provider
        llm = get_llm_provider()
        prompt = (
            f"Lieferantensignal aus Unternehmensdokument (Typ: {signal_type}, "
            f"Dimension: {dimension}, Schwere: {severity}):\n{description[:400]}\n\n"
            "Antworte NUR als JSON mit den Schlüsseln: "
            "\"why_important\", \"regulatory_impact\", \"recommended_action\" (je max 120 Zeichen)."
        )
        raw = await llm.complete(prompt, max_tokens=300, temperature=0.3)
        import json, re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
            if all(k in parsed for k in ("why_important", "regulatory_impact", "recommended_action")):
                return parsed
    except Exception:
        pass
    return {
        "why_important": f"Dieses {severity.upper()}-Signal in der {dimension}-Dimension beeinflusst den Lieferantenscore.",
        "regulatory_impact": "Mögliche Auswirkung auf CSDDD/CSRD-Berichterstattung prüfen.",
        "recommended_action": f"Risikoüberprüfung für Dimension '{dimension}' einleiten.",
    }


async def activate_supplier(
    supplier_id: str,
    organization_id: str,
    session: AsyncSession,
    max_signals: int = 1000,
) -> dict[str, Any]:
    """Convert all company_signals for a supplier into twin timeline events
    and surveillance signals.

    Returns a summary dict with counts.
    """
    from application.intelligence_engine.timeline_service import append_event
    from application.intelligence_engine.twin_service import update_twin_health
    from infrastructure.persistence.models.company_intelligence import CompanySignalModel
    from infrastructure.persistence.models.supplier_digital_twin import (
        IntelligenceTimelineEventModel,
        SupplierDigitalTwinModel,
    )
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    # ── Load company signals ──────────────────────────────────────────────────
    stmt = (
        select(CompanySignalModel)
        .where(
            CompanySignalModel.supplier_id == supplier_id,
            CompanySignalModel.organization_id == organization_id,
        )
        .order_by(CompanySignalModel.severity.asc(), CompanySignalModel.created_at.desc())
        .limit(max_signals)
    )
    signals = list((await session.execute(stmt)).scalars().all())

    if not signals:
        return {"twin_events": 0, "surveillance_signals": 0, "skipped": 0}

    # ── Already processed signal IDs (twin) ──────────────────────────────────
    # We tag doc-intelligence events via source_type="DOC_INTEL"
    existing_stmt = select(IntelligenceTimelineEventModel.signal_id).where(
        IntelligenceTimelineEventModel.supplier_id == supplier_id,
        IntelligenceTimelineEventModel.organization_id == organization_id,
        IntelligenceTimelineEventModel.source_type == "DOC_INTEL",
    )
    existing_ids = set((await session.execute(existing_stmt)).scalars().all())

    # ── Already processed dedupe keys (surveillance) ──────────────────────────
    surv_existing = select(SurveillanceSignalModel.dedupe_key).where(
        SurveillanceSignalModel.organization_id == organization_id,
        SurveillanceSignalModel.supplier_id == supplier_id,
    )
    surv_existing_keys = set((await session.execute(surv_existing)).scalars().all())

    twin_created = 0
    surv_created = 0
    rec_created = 0
    skipped = 0

    for sig in signals:
        # signal_id field is VARCHAR(36) — use the raw signal UUID
        twin_signal_id = sig.id
        if sig.id in existing_ids:
            skipped += 1
            continue

        dimension = _DIMENSION_MAP.get(sig.dimension, "esg_health")
        delta = _delta(sig.severity, sig.direction)
        category = _CATEGORY_MAP.get(sig.dimension, "ESG")
        occurred = sig.event_date or sig.created_at or datetime.now(UTC)

        # AI reasoning (non-blocking)
        reasoning = await _llm_reasoning(
            signal_type=sig.signal_type,
            dimension=sig.dimension,
            severity=sig.severity,
            description=sig.description,
        )

        title = _build_title(sig.signal_type, sig.severity, sig.description)

        event = IntelligenceTimelineEvent(
            supplier_id=supplier_id,
            organization_id=organization_id,
            event_type="COMPANY_SIGNAL",
            event_category=category,
            severity=sig.severity.upper(),
            title=title,
            summary=sig.description[:500] if sig.description else title,
            why_important=reasoning["why_important"],
            regulatory_impact=reasoning["regulatory_impact"],
            recommended_action=reasoning["recommended_action"],
            source_type="DOC_INTEL",   # max 30 chars
            source_name="Dokument-KI",
            source_url="",
            evidence_ids="[]",
            regulation_ids="[]",
            risk_ids="[]",
            signal_id=twin_signal_id,  # raw UUID (36 chars)
            twin_dimension_affected=dimension,
            health_delta=delta,
            confidence=0.85,
            occurred_at=occurred,
            processed_at=datetime.now(UTC),
            is_active=True,
            status=EntityStatus.ACTIVE,
        )

        await append_event(event, session)
        await update_twin_health(
            supplier_id=supplier_id,
            organization_id=organization_id,
            dimension=dimension,
            delta=delta,
            session=session,
            severity=sig.severity.upper(),
        )
        twin_created += 1
        if sig.severity.lower() in _SURV_THRESHOLD:
            rec_created += 1

        # ── Surveillance: HIGH/CRITICAL → surveillance_signals ────────────────
        if sig.severity.lower() in _SURV_THRESHOLD:
            dkey = _dedupe_key(supplier_id, sig.id)
            if dkey not in surv_existing_keys:
                surv_sig = SurveillanceSignalModel(
                    id=str(uuid.uuid4()),
                    organization_id=organization_id,
                    supplier_id=supplier_id,
                    source_type="DOCUMENT_INTELLIGENCE",
                    source_id=sig.id,
                    signal_type=sig.signal_type.upper().replace(" ", "_"),
                    severity=sig.severity.upper(),
                    confidence=0.85,
                    title=title,
                    description=sig.description[:1000] if sig.description else title,
                    detected_at=occurred,
                    signal_status="ACTIVE",
                    explainability_json={
                        "dimension": sig.dimension,
                        "direction": sig.direction,
                        "year": sig.year,
                        "source_doc_id": sig.source_doc_id,
                        "company_name": sig.company_name,
                    },
                    dedupe_key=dkey,
                    status="Active",
                    version=1,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(surv_sig)
                surv_existing_keys.add(dkey)
                surv_created += 1

    # ── Update open_recommendations counter on the twin ──────────────────────
    if rec_created > 0:
        twin_row = (
            await session.execute(
                select(SupplierDigitalTwinModel).where(
                    SupplierDigitalTwinModel.supplier_id == supplier_id,
                    SupplierDigitalTwinModel.organization_id == organization_id,
                )
            )
        ).scalar_one_or_none()
        if twin_row is not None:
            twin_row.open_recommendations = (twin_row.open_recommendations or 0) + rec_created
            await session.flush()

    await session.commit()

    logger.info(
        "activator.supplier_done",
        supplier_id=supplier_id,
        twin_events=twin_created,
        surveillance_signals=surv_created,
        skipped=skipped,
    )

    return {
        "twin_events": twin_created,
        "surveillance_signals": surv_created,
        "skipped": skipped,
        "total_signals": len(signals),
    }


async def activate_trends_to_surveillance(
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
) -> dict[str, Any]:
    """Convert intelligence trend alerts (consecutive drops, spikes) into
    surveillance_signals.
    """
    from application.intelligence.trend_analyzer import analyze_trends
    from infrastructure.persistence.models.company_intelligence import CompanyMetricModel
    from infrastructure.persistence.models.surveillance import SurveillanceSignalModel

    stmt = select(CompanyMetricModel).where(CompanyMetricModel.organization_id == organization_id)
    if supplier_id:
        stmt = stmt.where(CompanyMetricModel.supplier_id == supplier_id)
    stmt = stmt.order_by(
        CompanyMetricModel.company_name,
        CompanyMetricModel.metric_type,
        CompanyMetricModel.year,
    )
    rows = list((await session.execute(stmt)).scalars().all())

    if not rows:
        return {"trend_signals": 0}

    trends = analyze_trends(rows, min_consecutive=2, spike_threshold=20.0)

    # Build company_name → supplier_id map from the rows
    name_to_sid: dict[str, str | None] = {}
    for r in rows:
        if r.company_name and r.supplier_id and r.company_name not in name_to_sid:
            name_to_sid[r.company_name] = r.supplier_id

    created = 0
    for trend in trends:
        if trend.severity not in ("critical", "high"):
            continue

        sid = name_to_sid.get(trend.company_name) or supplier_id
        dkey = f"trend:{trend.company_name}:{trend.metric_type}:{trend.year_start}"
        dkey_hash = hashlib.sha256(dkey.encode()).hexdigest()[:64]

        existing = await session.execute(
            select(SurveillanceSignalModel.id).where(
                SurveillanceSignalModel.dedupe_key == dkey_hash,
                SurveillanceSignalModel.organization_id == organization_id,
            )
        )
        if existing.scalar():
            continue

        metric_label = trend.metric_type.replace("_", " ").title()
        title = (
            f"{'📉' if trend.direction == 'down' else '📈'} Trendwarnung: "
            f"{metric_label} {trend.direction.upper()} "
            f"({trend.year_start}–{trend.year_end}, ⌀{abs(trend.avg_pct_change):.1f}%)"
        )

        surv = SurveillanceSignalModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            supplier_id=sid,
            source_type="INTELLIGENCE_TREND",
            signal_type="TREND_ALERT",
            severity=trend.severity.upper(),
            confidence=0.90,
            title=title,
            description=trend.description,
            detected_at=datetime.now(UTC),
            signal_status="ACTIVE",
            explainability_json={
                "metric_type": trend.metric_type,
                "alert_type": trend.alert_type,
                "direction": trend.direction,
                "avg_pct_change": trend.avg_pct_change,
                "company_name": trend.company_name,
            },
            dedupe_key=dkey_hash,
            status="Active",
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(surv)
        created += 1

    await session.commit()
    return {"trend_signals": created}


def _build_title(signal_type: str, severity: str, description: str) -> str:
    _labels: dict[str, str] = {
        "revenue_decline":       "Umsatzrückgang erkannt",
        "margin_pressure":       "Margendruck identifiziert",
        "ebitda_decline":        "EBITDA-Rückgang",
        "debt_increase":         "Verschuldung gestiegen",
        "cashflow_risk":         "Cashflow-Risiko",
        "co2_increase":          "CO₂-Emissionen gestiegen",
        "esg_deterioration":     "ESG-Verschlechterung",
        "compliance_risk":       "Compliance-Risiko erkannt",
        "governance_issue":      "Governance-Problem",
        "supply_chain_risk":     "Lieferkettenrisiko",
        "layoff_risk":           "Stellenabbau-Signal",
        "restructuring":         "Restrukturierungssignal",
        "regulatory_violation":  "Regulatorischer Verstoß",
        "financial_stress":      "Finanzstress-Signal",
        "workforce_reduction":   "Personalabbau erkannt",
    }
    label = _labels.get(signal_type.lower(), signal_type.replace("_", " ").title())
    sev_prefix = {"critical": "⚠️ KRITISCH", "high": "🔴 HOCH", "medium": "🟡 MITTEL", "low": "🔵 NIEDRIG"}.get(
        severity.lower(), severity.upper()
    )
    short_desc = description[:80].rstrip() if description else ""
    if short_desc and len(description) > 80:
        short_desc += "…"
    return f"{sev_prefix}: {label}" + (f" — {short_desc}" if short_desc else "")
