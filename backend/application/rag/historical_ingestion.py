"""Phase 4 — Historisches Lernen: Ingestion-Pipeline.

Zwei Quellen werden in historical_knowledge eingelesen:

Quelle A: intelligence_timeline_events
  → Ereignis + empfohlene Massnahme + health_delta (bereits erfasst)
  → Lernt: welche Event-Typen welche CSDDD-Dimensionen am stärksten beeinflussen

Quelle B: Findings + geschlossene CAPs + Supplier-Score-Delta
  → Befund + Gegenmassnahme + Messung der Wirkung (Score vorher vs. nachher)
  → Lernt: welche Massnahmen bei welchen Befund-Kategorien wie gewirkt haben

Jeder Eintrag wird mit multilingual-e5-large eingebettet und ist über
retrieve_history() semantisch durchsuchbar.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .embedder import embed_passage, embed_passages_batch

logger = structlog.get_logger(__name__)

# ── CSDDD-Right Mapping ───────────────────────────────────────────────────────
# Dimension/Kategorie → CSDDD-Right-ID

_DIMENSION_TO_RIGHT: dict[str, str] = {
    "human_rights_health":       "human_dignity",
    "labour_rights_health":      "freedom_of_association",
    "environmental_health":      "environmental_destruction",
    "governance_health":         "community_rights",
    "child_labour":              "child_labour",
    "forced_labour":             "forced_labour",
    "freedom_of_association":    "freedom_of_association",
    "collective_bargaining":     "collective_bargaining",
    "discrimination":            "discrimination",
    "minimum_wage":              "minimum_wage",
    "working_hours":             "working_hours",
    "occupational_safety":       "occupational_safety",
    "land_rights":               "land_rights",
    "water_rights":              "water_rights",
    "environmental_destruction": "environmental_destruction",
    "harmful_chemicals":         "harmful_chemicals",
    "biodiversity":              "biodiversity",
    "mercury":                   "mercury",
    "hazardous_waste":           "hazardous_waste",
    "modern_slavery":            "modern_slavery",
    "migrant_worker_rights":     "migrant_worker_rights",
    "community_rights":          "community_rights",
}

_CATEGORY_TO_RIGHT: dict[str, str] = {
    "Labour Rights":             "freedom_of_association",
    "Child Labour":              "child_labour",
    "Forced Labour":             "forced_labour",
    "Modern Slavery":            "modern_slavery",
    "Discrimination":            "discrimination",
    "Wages":                     "minimum_wage",
    "Working Hours":             "working_hours",
    "Occupational Safety":       "occupational_safety",
    "Land Rights":               "land_rights",
    "Water Rights":              "water_rights",
    "Environmental":             "environmental_destruction",
    "Chemicals":                 "harmful_chemicals",
    "Biodiversity":              "biodiversity",
    "Mercury":                   "mercury",
    "Hazardous Waste":           "hazardous_waste",
    "Community Rights":          "community_rights",
    "Migrant Workers":           "migrant_worker_rights",
    "Human Dignity":             "human_dignity",
    "Privacy":                   "privacy",
    "Freedom of Expression":     "freedom_of_expression",
    "Governance":                "community_rights",
    "Supply Chain":              "community_rights",
    "Financial":                 "community_rights",
}

_OUTCOME_LABELS: dict[str, str] = {
    "effective":         "Massnahme wirksam — Health-Score verbessert",
    "partial":           "Massnahme teilweise wirksam",
    "ineffective":       "Massnahme ohne messbare Wirkung",
    "unknown":           "Wirkung nicht messbar (keine Score-Daten)",
}


def _map_right(dimension: str | None, category: str | None) -> str | None:
    if dimension:
        right = _DIMENSION_TO_RIGHT.get(dimension.strip())
        if right:
            return right
    if category:
        for key, right in _CATEGORY_TO_RIGHT.items():
            if key.lower() in category.lower():
                return right
    return None


def _outcome_from_delta(delta: float | None) -> str:
    if delta is None:
        return "unknown"
    if delta >= 3.0:
        return "effective"
    if delta >= 0.5:
        return "partial"
    if delta < 0:
        return "ineffective"
    return "partial"


# ── Quelle A: Intelligence Timeline Events ────────────────────────────────────

async def _ingest_timeline_events(
    organization_id: str, session: AsyncSession
) -> tuple[int, int]:
    """Ingests intelligence_timeline_events mit health_delta in historical_knowledge."""
    from infrastructure.persistence.models.supplier_digital_twin import (
        IntelligenceTimelineEventModel,
    )
    from infrastructure.persistence.models.historical_knowledge import HistoricalKnowledgeModel

    # Bereits bekannte source_event_ids
    existing = set(
        row[0]
        for row in (
            await session.execute(
                text(
                    "SELECT source_event_id FROM historical_knowledge "
                    "WHERE organization_id = :org AND source_event_id IS NOT NULL"
                ),
                {"org": organization_id},
            )
        ).fetchall()
    )

    events_result = await session.execute(
        select(IntelligenceTimelineEventModel).where(
            IntelligenceTimelineEventModel.organization_id == organization_id
        )
    )
    events = events_result.scalars().all()

    new_records: list[dict] = []
    skipped = 0

    for ev in events:
        if ev.id in existing:
            skipped += 1
            continue

        csddd_right = _map_right(ev.twin_dimension_affected, ev.event_category)
        delta = ev.health_delta if ev.health_delta != 0.0 else None
        outcome = _outcome_from_delta(delta)

        countermeasure = ev.recommended_action or ""
        outcome_desc = ""
        if delta is not None:
            direction = "verbessert" if delta > 0 else "verschlechtert"
            outcome_desc = f"Health-Score {direction} um {abs(delta):.1f} Punkte."
        if outcome == "unknown":
            outcome_desc = "Keine direkte Health-Score-Messung für dieses Ereignis."

        content = (
            f"Ereignis: {ev.title}. "
            f"Zusammenfassung: {ev.summary}. "
            f"Warum wichtig: {ev.why_important}. "
            + (f"Empfohlene Gegenmassnahme: {countermeasure}. " if countermeasure else "")
            + (f"CSDDD-Recht: {csddd_right}. " if csddd_right else "")
            + (f"Ergebnis: {outcome_desc}" if outcome_desc else "")
        ).strip()

        _now = datetime.now(timezone.utc)
        new_records.append({
            "id":                        str(uuid.uuid4()),
            "organization_id":           organization_id,
            "supplier_id":               ev.supplier_id,
            "event_description":         ev.summary,
            "event_type":                ev.event_type,
            "event_severity":            ev.severity,
            "countermeasure_description": countermeasure,
            "countermeasure_type":       "intelligence_recommendation",
            "outcome_description":       outcome_desc,
            "outcome_category":          outcome,
            "health_delta":              delta,
            "csddd_right":               csddd_right,
            "twin_dimension":            ev.twin_dimension_affected or None,
            "content_text":              content,
            "source_event_id":           ev.id,
            "reference_date":            ev.occurred_at,
            "status":                    "active",
            "version":                   1,
            "owner":                     organization_id,
            "created_by":                "system:rag_ingestion",
            "updated_by":                "system:rag_ingestion",
            "created_at":                _now,
            "updated_at":                _now,
        })

    if not new_records:
        return 0, skipped

    # Batch embed
    texts = [r["content_text"] for r in new_records]
    embeddings = embed_passages_batch(texts)

    for rec, emb in zip(new_records, embeddings):
        hk = HistoricalKnowledgeModel(**rec)
        hk.embedding = emb if isinstance(emb, list) else emb.tolist()
        session.add(hk)

    await session.flush()
    return len(new_records), skipped


# ── Quelle B: Findings + geschlossene CAPs + Supplier-Score-Delta ─────────────

async def _ingest_cap_findings(
    organization_id: str, session: AsyncSession
) -> tuple[int, int]:
    """Ingests closed CAPs mit zugehörigem Finding und Supplier-Score-Delta."""
    from infrastructure.persistence.models.corrective_action_plan import CorrectiveActionPlanModel
    from infrastructure.persistence.models.finding import FindingModel
    from infrastructure.persistence.models.assessment import AssessmentModel
    from infrastructure.persistence.models.supplier_score import SupplierScoreModel
    from infrastructure.persistence.models.historical_knowledge import HistoricalKnowledgeModel

    existing = set(
        row[0]
        for row in (
            await session.execute(
                text(
                    "SELECT source_cap_id FROM historical_knowledge "
                    "WHERE organization_id = :org AND source_cap_id IS NOT NULL"
                ),
                {"org": organization_id},
            )
        ).fetchall()
    )

    caps_result = await session.execute(
        select(CorrectiveActionPlanModel).where(
            CorrectiveActionPlanModel.organization_id == organization_id,
            CorrectiveActionPlanModel.cap_status.in_(["CLOSED", "VERIFIED", "COMPLETED"]),
        )
    )
    caps = caps_result.scalars().all()

    new_records: list[dict] = []
    skipped = 0

    for cap in caps:
        if cap.id in existing:
            skipped += 1
            continue

        # Finding laden
        finding_result = await session.execute(
            select(FindingModel).where(FindingModel.id == cap.finding_id)
        )
        finding = finding_result.scalar_one_or_none()
        if not finding:
            skipped += 1
            continue

        # Assessment → supplier_id
        assessment_result = await session.execute(
            select(AssessmentModel).where(AssessmentModel.id == finding.assessment_id)
        )
        assessment = assessment_result.scalar_one_or_none()
        supplier_id = assessment.supplier_id if assessment else None

        # Supplier-Score Delta: Score vor Finding (created_at) vs. nach CAP (closed_at)
        health_delta = None
        if supplier_id and cap.closed_at and finding.created_at:
            score_before_result = await session.execute(
                select(SupplierScoreModel.esg_score)
                .where(
                    SupplierScoreModel.supplier_id == supplier_id,
                    SupplierScoreModel.created_at <= finding.created_at,
                )
                .order_by(SupplierScoreModel.created_at.desc())
                .limit(1)
            )
            score_after_result = await session.execute(
                select(SupplierScoreModel.esg_score)
                .where(
                    SupplierScoreModel.supplier_id == supplier_id,
                    SupplierScoreModel.created_at >= cap.closed_at,
                )
                .order_by(SupplierScoreModel.created_at.asc())
                .limit(1)
            )
            score_before = score_before_result.scalar_one_or_none()
            score_after = score_after_result.scalar_one_or_none()
            if score_before is not None and score_after is not None:
                health_delta = round(score_after - score_before, 2)

        csddd_right = _map_right(None, finding.category)
        outcome = _outcome_from_delta(health_delta)

        finding_desc = f"{finding.title}: {finding.description[:400]}"
        cap_desc = f"{cap.title}: {cap.description[:400]}"
        outcome_desc = ""
        if health_delta is not None:
            direction = "verbessert" if health_delta > 0 else "verschlechtert"
            outcome_desc = f"ESG-Score {direction} um {abs(health_delta):.1f} Punkte nach Abschluss der Massnahme."
        else:
            outcome_desc = "Keine Score-Messung verfügbar (CAP geschlossen, Wirkung ungemessen)."

        content = (
            f"Befund ({finding.severity}): {finding_desc}. "
            f"Kategorie: {finding.category}. "
            f"Gegenmassnahme (CAP): {cap_desc}. "
            f"CAP-Status: {cap.cap_status}. "
            + (f"CSDDD-Recht: {csddd_right}. " if csddd_right else "")
            + f"Ergebnis: {outcome_desc}"
        )

        _now = datetime.now(timezone.utc)
        new_records.append({
            "id":                        str(uuid.uuid4()),
            "organization_id":           organization_id,
            "supplier_id":               supplier_id,
            "event_description":         finding_desc,
            "event_type":                "finding",
            "event_severity":            finding.severity,
            "countermeasure_description": cap_desc,
            "countermeasure_type":       "corrective_action_plan",
            "outcome_description":       outcome_desc,
            "outcome_category":          outcome,
            "health_delta":              health_delta,
            "csddd_right":               csddd_right,
            "twin_dimension":            None,
            "content_text":              content,
            "source_finding_id":         finding.id,
            "source_cap_id":             cap.id,
            "reference_date":            cap.closed_at or finding.created_at,
            "status":                    "active",
            "version":                   1,
            "owner":                     organization_id,
            "created_by":                "system:rag_ingestion",
            "updated_by":                "system:rag_ingestion",
            "created_at":                _now,
            "updated_at":                _now,
        })

    if not new_records:
        return 0, skipped

    texts = [r["content_text"] for r in new_records]
    embeddings = embed_passages_batch(texts)

    for rec, emb in zip(new_records, embeddings):
        hk = HistoricalKnowledgeModel(**rec)
        hk.embedding = emb if isinstance(emb, list) else emb.tolist()
        session.add(hk)

    await session.flush()
    return len(new_records), skipped


# ── Öffentliche API ───────────────────────────────────────────────────────────

async def ingest_historical_knowledge(
    organization_id: str, session: AsyncSession
) -> dict:
    """Führt beide Ingestion-Quellen aus und committed."""
    ev_new, ev_skip = await _ingest_timeline_events(organization_id, session)
    cap_new, cap_skip = await _ingest_cap_findings(organization_id, session)
    await session.commit()

    total_new = ev_new + cap_new
    logger.info(
        "historical_ingestion.done",
        org=organization_id,
        timeline_events_new=ev_new,
        timeline_events_skipped=ev_skip,
        cap_findings_new=cap_new,
        cap_findings_skipped=cap_skip,
        total_new=total_new,
    )
    return {
        "timeline_events_new":      ev_new,
        "timeline_events_skipped":  ev_skip,
        "cap_findings_new":         cap_new,
        "cap_findings_skipped":     cap_skip,
        "total_new":                total_new,
        "message": f"{total_new} neue Lerneinträge erstellt ({ev_new} Events, {cap_new} CAPs).",
    }
