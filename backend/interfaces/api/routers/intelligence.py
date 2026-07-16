"""Company Intelligence API — Metriken und Signale aus Dokumenten.

Endpoints:
  GET  /intelligence/metrics          → Alle Kennzahlen (filterbar)
  GET  /intelligence/signals          → Alle Signale (filterbar)
  POST /intelligence/extract-all      → Retroaktive Extraktion aller existing docs
  POST /intelligence/cross-analyze    → Cross-Source-Analyse (NACE-basiert)
  GET  /intelligence/cross-alerts     → Alle Cross-Source-Alerts
  PATCH /intelligence/cross-alerts/{id}/status → Status aktualisieren
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.user import User
from infrastructure.persistence.models.company_intelligence import (
    CompanyMetricModel,
    CompanySignalModel,
)
from infrastructure.persistence.models.document_pipeline import DocumentFileModel
from infrastructure.persistence.models.rag_documents import RagDocumentModel
from interfaces.api.deps import get_current_user, get_db

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/intelligence", tags=["Company Intelligence"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MetricOut(BaseModel):
    id: str
    company_name: str
    supplier_id: str | None
    metric_type: str
    value: float
    unit: str
    year: int
    period: str
    source_doc_id: str | None
    confidence: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalOut(BaseModel):
    id: str
    company_name: str
    supplier_id: str | None
    signal_type: str
    dimension: str
    direction: str
    severity: str
    description: str
    year: int | None
    event_date: Any | None
    source_doc_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class YearChangeOut(BaseModel):
    year_from: int
    year_to: int
    value_from: float
    value_to: float
    pct_change: float
    unit: str


class TrendAlertOut(BaseModel):
    company_name: str
    metric_type: str
    unit: str
    alert_type: str
    direction: str
    sentiment: str
    severity: str
    year_start: int
    year_end: int
    avg_pct_change: float
    description: str
    changes: list[YearChangeOut]
    reference_source: str | None = None
    reference_url: str | None = None
    verification_note: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=list[MetricOut])
async def list_metrics(
    company_name: str | None = None,
    metric_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    supplier_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    stmt = select(CompanyMetricModel).where(CompanyMetricModel.organization_id == org_id)
    if company_name:
        stmt = stmt.where(CompanyMetricModel.company_name.ilike(f"%{company_name}%"))
    if metric_type:
        stmt = stmt.where(CompanyMetricModel.metric_type == metric_type)
    if year_from:
        stmt = stmt.where(CompanyMetricModel.year >= year_from)
    if year_to:
        stmt = stmt.where(CompanyMetricModel.year <= year_to)
    if supplier_id:
        stmt = stmt.where(CompanyMetricModel.supplier_id == supplier_id)
    stmt = stmt.order_by(CompanyMetricModel.company_name, CompanyMetricModel.metric_type, CompanyMetricModel.year)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/signals", response_model=list[SignalOut])
async def list_signals(
    company_name: str | None = None,
    dimension: str | None = None,
    direction: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    supplier_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    stmt = select(CompanySignalModel).where(CompanySignalModel.organization_id == org_id)
    if company_name:
        stmt = stmt.where(CompanySignalModel.company_name.ilike(f"%{company_name}%"))
    if dimension:
        stmt = stmt.where(CompanySignalModel.dimension == dimension)
    if direction:
        stmt = stmt.where(CompanySignalModel.direction == direction)
    if year_from:
        stmt = stmt.where(CompanySignalModel.year >= year_from)
    if year_to:
        stmt = stmt.where(CompanySignalModel.year <= year_to)
    if supplier_id:
        stmt = stmt.where(CompanySignalModel.supplier_id == supplier_id)
    stmt = stmt.order_by(CompanySignalModel.company_name, CompanySignalModel.year.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/trends", response_model=list[TrendAlertOut])
async def get_trends(
    company_name: str | None = None,
    supplier_id: str | None = None,
    min_consecutive: int = 2,
    spike_threshold: float = 20.0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trend-Analyse über company_metrics — erkennt konsekutive Trends und Sprünge."""
    from application.intelligence.trend_analyzer import analyze_trends

    org_id = user.organization_id
    stmt = select(CompanyMetricModel).where(CompanyMetricModel.organization_id == org_id)
    if company_name:
        stmt = stmt.where(CompanyMetricModel.company_name.ilike(f"%{company_name}%"))
    if supplier_id:
        stmt = stmt.where(CompanyMetricModel.supplier_id == supplier_id)
    stmt = stmt.order_by(CompanyMetricModel.company_name, CompanyMetricModel.metric_type, CompanyMetricModel.year)
    rows = (await db.execute(stmt)).scalars().all()

    alerts = analyze_trends(rows, min_consecutive=min_consecutive, spike_threshold=spike_threshold)

    return [
        TrendAlertOut(
            company_name=a.company_name,
            metric_type=a.metric_type,
            unit=a.unit,
            alert_type=a.alert_type,
            direction=a.direction,
            sentiment=a.sentiment,
            severity=a.severity,
            year_start=a.year_start,
            year_end=a.year_end,
            avg_pct_change=a.avg_pct_change,
            description=a.description,
            reference_source=a.reference_source,
            reference_url=a.reference_url,
            verification_note=a.verification_note,
            changes=[
                YearChangeOut(
                    year_from=c.year_from,
                    year_to=c.year_to,
                    value_from=c.value_from,
                    value_to=c.value_to,
                    pct_change=c.pct_change,
                    unit=c.unit,
                )
                for c in a.changes
            ],
        )
        for a in alerts
    ]




@router.post("/detect-contradictions")
async def detect_contradictions(
    company_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Erkennt Widersprüche zwischen Commitments und tatsächlichen Kennzahlen."""
    from application.intelligence.contradiction_detector import (
        detect_contradictions_for_company,
        detect_all_contradictions,
    )
    from sqlalchemy import func

    org_id = user.organization_id

    if company_name:
        async with db.begin_nested():
            result = await detect_contradictions_for_company(
                organization_id=org_id,
                company_name=company_name,
                supplier_id=None,
                session=db,
            )
        await db.commit()
        return result

    # Alle Firmen
    async with db.begin_nested():
        result = await detect_all_contradictions(organization_id=org_id, session=db)
    await db.commit()
    return result


@router.post("/verify-metrics")
async def verify_metrics(
    company_name: str | None = None,
    metric_types: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verifiziert extrahierte Metriken gegen Online-Quellen (yfinance + Web).

    Markiert Werte als verified/discrepant und speichert Quellenangaben.
    """
    import asyncio
    from application.intelligence.metric_verifier import verify_metric

    org_id = user.organization_id
    stmt = select(CompanyMetricModel).where(
        CompanyMetricModel.organization_id == org_id,
        CompanyMetricModel.is_verified == False,  # noqa: E712
    )
    if company_name:
        stmt = stmt.where(CompanyMetricModel.company_name.ilike(f"%{company_name}%"))
    if metric_types:
        types = [t.strip() for t in metric_types.split(",")]
        stmt = stmt.where(CompanyMetricModel.metric_type.in_(types))

    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return {"verified": 0, "discrepant": 0, "not_found": 0}

    verified = discrepant = not_found = 0

    for row in rows:
        try:
            result = await verify_metric(
                company_name=row.company_name,
                metric_type=row.metric_type,
                year=row.year,
                extracted_value=float(row.value),
                unit=row.unit,
            )

            row.is_verified = True
            row.reference_value = result.reference_value
            row.reference_source = result.reference_source
            row.reference_url = result.reference_url
            row.verification_note = result.note

            if result.status == "verified":
                verified += 1
            elif result.status == "discrepant":
                discrepant += 1
            else:
                not_found += 1

            await asyncio.sleep(0.5)  # Rate-limiting

        except Exception as exc:
            logger.warning("verify_metrics.row_error", metric_id=row.id, error=str(exc))
            not_found += 1

    await db.commit()

    logger.info("verify_metrics.done", org=org_id, verified=verified,
                discrepant=discrepant, not_found=not_found)
    return {"verified": verified, "discrepant": discrepant, "not_found": not_found, "total": len(rows)}


@router.post("/link-signals")
async def link_signals_to_suppliers(
    min_confidence: float = 0.7,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Link unlinked company signals and metrics to supplier records via EntityLinker (E2-F3).

    Matches company_name variants ("BMW Group", "Bayerische Motorenwerke AG") to
    known suppliers using exact → alias → fuzzy tiers. Only matches at or above
    min_confidence are applied (default 0.7 = fuzzy threshold).
    """
    from application.intelligence.entity_linker_service import link_signals, link_metrics

    org_id = user.organization_id

    async with db.begin_nested():
        signals_result = await link_signals(org_id, db, min_confidence=min_confidence)
        metrics_result = await link_metrics(org_id, db, min_confidence=min_confidence)

    await db.commit()

    logger.info(
        "intelligence.link_signals_done",
        org=org_id,
        signals=signals_result,
        metrics=metrics_result,
    )
    return {
        "signals": signals_result,
        "metrics": metrics_result,
    }


# Erwartete Metriken je Dokumenttyp
# core = wird für den Score erwartet (70 Punkte)
# bonus = nice-to-have (30 Punkte)
# Erwartete Metriken je Dokumenttyp.
# Narrative Dokumente (Statements, Q&A, Pressemitteilungen) haben core=[] —
# es ist kein Fehler wenn dort keine Zahlen stehen.
_DOC_EXPECTATIONS: dict[str, dict[str, list[str]]] = {
    # ── Strukturierte Berichte mit Zahlenpflicht ──────────────────────────────
    "annual_report": {
        "core":  ["revenue", "ebitda", "net_income", "employees", "co2_scope1", "co2_scope2", "renewable_energy_pct"],
        "bonus": ["ebitda_margin", "capex", "free_cashflow", "debt_ratio", "roce", "eps", "energy_gwh", "water_m3"],
    },
    "sustainability_report": {
        "core":  ["co2_scope1", "co2_scope2", "renewable_energy_pct", "employees", "women_leadership_pct"],
        "bonus": ["co2_scope3", "energy_gwh", "water_m3", "supplier_audited_pct", "esg_score", "lost_time_injury_rate"],
    },
    "esg_overview": {
        "core":  ["co2_scope1", "co2_scope2", "renewable_energy_pct", "esg_score"],
        "bonus": ["co2_scope3", "energy_gwh", "water_m3", "women_leadership_pct", "supplier_audited_pct"],
    },
    "csrd_report": {
        "core":  ["co2_scope1", "co2_scope2", "co2_scope3", "renewable_energy_pct", "employees", "women_leadership_pct"],
        "bonus": ["energy_gwh", "water_m3", "supplier_audited_pct", "esg_score", "lost_time_injury_rate"],
    },
    "csddd_disclosure": {
        "core":  ["employees", "supplier_audited_pct"],
        "bonus": ["co2_scope1", "co2_scope2", "women_leadership_pct", "lost_time_injury_rate"],
    },
    "governance_report": {
        "core":  ["employees", "women_leadership_pct"],
        "bonus": ["esg_score", "supplier_audited_pct"],
    },
    "key_metrics": {
        "core":  ["revenue", "ebitda", "co2_scope1"],
        "bonus": ["net_income", "employees", "renewable_energy_pct"],
    },
    "cdp_questionnaire": {
        "core":  ["co2_scope1", "co2_scope2", "co2_scope3", "renewable_energy_pct"],
        "bonus": ["energy_gwh", "water_m3"],
    },
    "audit_report": {
        "core":  ["employees"],
        "bonus": ["supplier_audited_pct", "co2_scope1"],
    },
    "sector_risk": {
        "core":  [],
        "bonus": ["co2_scope1", "revenue", "employees"],
    },
    # ── Investor Relations — Zahlen vorhanden aber selektiv ──────────────────
    "investor_presentation": {
        "core":  ["revenue", "ebitda"],
        "bonus": ["net_income", "ebitda_margin", "capex", "free_cashflow", "eps", "roce"],
    },
    # ── Narrative Dokumente — keine Pflicht-Metriken ─────────────────────────
    "press_release": {
        "core":  [],
        "bonus": ["revenue", "net_income", "employees"],
    },
    "executive_statement": {
        "core":  [],
        "bonus": ["revenue", "co2_scope1", "employees"],
    },
    "qa_document": {
        "core":  [],
        "bonus": ["revenue", "co2_scope1", "employees", "net_income"],
    },
    "_default": {
        "core":  ["revenue", "co2_scope1", "employees"],
        "bonus": ["ebitda", "net_income", "renewable_energy_pct"],
    },
}


def _doc_quality_score(found_types: set[str], doc_type: str) -> tuple[float, list[str], int, int]:
    """Berechnet Score + fehlende Core-Metriken für einen Dokumenttyp."""
    exp = _DOC_EXPECTATIONS.get(doc_type, _DOC_EXPECTATIONS["_default"])
    core: list[str] = exp["core"]
    bonus: list[str] = exp["bonus"]

    found_core = [m for m in core if m in found_types]
    missing_core = [m for m in core if m not in found_types]
    found_bonus = [m for m in bonus if m in found_types]

    if core:
        core_score = (len(found_core) / len(core)) * 70
    else:
        core_score = 70.0  # Dokumenttyp ohne Pflicht-Metriken bekommt vollen Core-Score

    bonus_score = (len(found_bonus) / max(1, len(bonus))) * 30 if bonus else 0.0

    score = round(min(100.0, core_score + bonus_score), 1)
    return score, missing_core, len(found_core), len(core)


class DocQualityOut(BaseModel):
    doc_file_id: str
    doc_id: str
    doc_type: str
    title: str | None = None
    company_name: str | None = None
    supplier_id: str | None = None
    report_year: int | None = None
    metric_count: int
    metrics_count: int
    metric_types: list[str]
    years: list[int]
    confidence_dist: dict[str, int]
    quality_score: float
    missing_core: list[str]
    found_core: int
    total_core: int


@router.get("/doc-quality", response_model=list[DocQualityOut])
async def get_doc_quality(
    supplier_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Datenqualität pro Dokument — dokumenttyp-bewusst, mit fehlenden Kernmetriken."""
    org_id = user.organization_id

    where_conds = [
        CompanyMetricModel.organization_id == org_id,
        CompanyMetricModel.source_doc_id.isnot(None),
    ]
    if supplier_id:
        where_conds.append(CompanyMetricModel.supplier_id == supplier_id)

    stmt = (
        select(
            CompanyMetricModel,
            DocumentFileModel.doc_type,
            DocumentFileModel.title,
            DocumentFileModel.company_name.label("doc_company_name"),
            DocumentFileModel.supplier_id.label("doc_supplier_id"),
            DocumentFileModel.report_year,
        )
        .join(DocumentFileModel, CompanyMetricModel.source_doc_id == DocumentFileModel.id, isouter=True)
        .where(*where_conds)
    )
    rows = (await db.execute(stmt)).all()

    _NARRATIVE_KEYWORDS = (
        "statement", "speech", "rede", "interview", "q&a", "qa session",
        "press conference", "pressekonferenz", "annual conference", "hauptversammlung",
        "vorstandsrede", "ceo letter", "letter to shareholders", "brief an die aktionäre",
    )

    def _effective_doc_type(doc_type: str, title: str | None) -> str:
        if title:
            tl = title.lower()
            if any(kw in tl for kw in _NARRATIVE_KEYWORDS):
                return "executive_statement"
        return doc_type or "_default"

    by_doc: dict[str, dict] = {}
    for metric, doc_type, title, doc_company_name, doc_supplier_id, report_year in rows:
        if metric.source_doc_id not in by_doc:
            effective = _effective_doc_type(doc_type or "_default", title)
            by_doc[metric.source_doc_id] = {
                "metrics": [],
                "doc_type": effective,
                "title": title,
                "company_name": doc_company_name or metric.company_name,
                "supplier_id": doc_supplier_id or metric.supplier_id,
                "report_year": report_year,
            }
        by_doc[metric.source_doc_id]["metrics"].append(metric)

    result = []
    for doc_id, data in by_doc.items():
        metrics = data["metrics"]
        doc_type = data["doc_type"]
        types = sorted({m.metric_type for m in metrics})
        years = sorted({m.year for m in metrics if m.year})
        conf_dist: dict[str, int] = {}
        for m in metrics:
            conf_dist[m.confidence] = conf_dist.get(m.confidence, 0) + 1

        score, missing_core, found_core, total_core = _doc_quality_score(set(types), doc_type)
        count = len(metrics)

        result.append(DocQualityOut(
            doc_file_id=doc_id,
            doc_id=doc_id,
            doc_type=doc_type,
            title=data["title"],
            company_name=data["company_name"],
            supplier_id=data["supplier_id"],
            report_year=data["report_year"],
            metric_count=count,
            metrics_count=count,
            metric_types=types,
            years=years,
            confidence_dist=conf_dist,
            quality_score=score,
            missing_core=missing_core,
            found_core=found_core,
            total_core=total_core,
        ))

    return sorted(result, key=lambda x: -x.metric_count)


@router.post("/extract-all")
async def extract_all_intelligence(
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retroaktive Extraktion: nur neue Dokumente → company_metrics + company_signals.

    Bereits extrahierte Dokumente werden übersprungen (kein LLM-Aufruf).
    Guard: document_files.last_extracted_at — gesetzt nach jeder Extraktion (auch bei 0 Ergebnissen).
    Mit ?force=true alle Dokumente neu extrahieren (Budget-intensiv!).
    """
    import asyncio
    from datetime import UTC, datetime
    from application.rag.metric_extractor import extract_and_store_intelligence
    from application.rag.document_classifier import get_doc_class
    from infrastructure.persistence.database import AsyncSessionFactory

    org_id = user.organization_id

    doc_files = (await db.execute(
        select(DocumentFileModel).where(
            DocumentFileModel.organization_id == org_id,
            DocumentFileModel.status == "done",
        ).order_by(DocumentFileModel.report_year.asc())
    )).scalars().all()

    results = []
    for i, doc_file in enumerate(doc_files):
        # Skip if already extracted — last_extracted_at is set after every run (even 0-result runs)
        if not force and doc_file.last_extracted_at is not None:
            results.append({
                "id": doc_file.id,
                "skipped": True,
                "reason": "already_extracted",
                "year": doc_file.report_year,
                "last_extracted_at": doc_file.last_extracted_at.isoformat(),
            })
            continue

        chunk_rows = (await db.execute(
            select(RagDocumentModel.content)
            .where(RagDocumentModel.document_file_id == doc_file.id)
            .order_by(RagDocumentModel.created_at.asc())
            .limit(60)
        )).scalars().all()

        if not chunk_rows or not doc_file.company_name:
            results.append({"id": doc_file.id, "skipped": True, "reason": "no_chunks_or_company"})
            continue

        try:
            async with AsyncSessionFactory() as session:
                async with session.begin():
                    intel = await extract_and_store_intelligence(
                        organization_id=org_id,
                        doc_file_id=doc_file.id,
                        doc_class=get_doc_class(doc_file.doc_type),
                        company_name=doc_file.company_name,
                        supplier_id=doc_file.supplier_id,
                        report_year=doc_file.report_year,
                        chunks=list(chunk_rows),
                        session=session,
                    )
            # Mark as extracted — even if 0 results, prevents future budget waste
            doc_file.last_extracted_at = datetime.now(UTC)
            await db.flush()
            results.append({
                "id": doc_file.id,
                "doc_type": doc_file.doc_type,
                "year": doc_file.report_year,
                **intel,
            })
        except Exception as exc:
            logger.error("intelligence.extract_error", doc_id=doc_file.id, error=str(exc))
            results.append({"id": doc_file.id, "error": str(exc)[:200]})

        if i < len(doc_files) - 1:
            await asyncio.sleep(2.0)

    await db.commit()

    skipped = sum(1 for r in results if r.get("skipped"))
    total_metrics = sum(r.get("metrics", 0) for r in results)
    total_signals = sum(r.get("signals", 0) for r in results)
    llm_calls = len(results) - skipped

    logger.info("intelligence.extract_all_done", org=org_id, docs=len(results),
                skipped=skipped, llm_calls=llm_calls, metrics=total_metrics,
                signals=total_signals, force=force)

    return {
        "processed": len(results),
        "skipped_already_extracted": skipped,
        "llm_calls_made": llm_calls,
        "total_metrics": total_metrics,
        "total_signals": total_signals,
        "details": results,
    }


# ── Cross-Source Intelligence ─────────────────────────────────────────────────

class CrossAnalyzeRequest(BaseModel):
    trigger_company: str
    trigger_signal_type: str
    trigger_description: str
    trigger_nace: str | None = None
    trigger_signal_id: str | None = None


class CrossAlertStatusUpdate(BaseModel):
    status: str  # open | acknowledged | resolved


@router.post("/cross-analyze")
async def post_cross_analyze(
    req: CrossAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analysiert ein Signal und erzeugt einen Cross-Source-Alert (NACE-basiert)."""
    from application.intelligence.cross_source_analyzer import analyze_cross_impact

    org_id = str(current_user.organization_id)
    result = await analyze_cross_impact(
        organization_id=org_id,
        trigger_company=req.trigger_company,
        trigger_nace=req.trigger_nace,
        trigger_signal_type=req.trigger_signal_type,
        trigger_description=req.trigger_description,
        trigger_signal_id=req.trigger_signal_id,
        session=db,
    )
    return result


@router.post("/cross-analyze-bulk")
async def post_cross_analyze_bulk(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Führt Cross-Source-Analyse für alle einzigartigen HIGH/CRITICAL Signal-Typen eines Lieferanten durch.

    Pro signal_type wird genau eine Analyse ausgeführt (mit dem impactreichsten Beispiel-Signal).
    Bereits existierende Alerts für denselben Lieferanten + Signal-Typ werden übersprungen.
    """
    import asyncio
    from application.intelligence.cross_source_analyzer import analyze_cross_impact
    from infrastructure.persistence.models.company_intelligence import CompanySignalModel

    org_id = str(current_user.organization_id)

    # Nur negative Risiko-Signaltypen für Cross-Source relevant
    RISK_SIGNAL_TYPES = {
        "profit_warning", "warning", "yoy_comparison", "outlook_negative",
        "litigation", "human_rights_issue", "contradiction", "product_recall",
        "environmental_incident", "restructuring", "layoff_risk", "financial_stress",
        "compliance_risk", "regulatory_violation", "esg_deterioration",
    }

    # Alle HIGH/CRITICAL Signale des Lieferanten laden
    stmt = (
        select(CompanySignalModel)
        .where(
            CompanySignalModel.supplier_id == supplier_id,
            CompanySignalModel.organization_id == org_id,
            CompanySignalModel.severity.in_(["high", "critical"]),
        )
        .order_by(CompanySignalModel.severity.asc(), CompanySignalModel.created_at.desc())
    )
    all_signals = list((await db.execute(stmt)).scalars().all())

    if not all_signals:
        return {"created": 0, "skipped": 0, "message": "Keine HIGH/CRITICAL Signale gefunden."}

    # Firmennamen und NACE-Code des Lieferanten ermitteln
    company_name = all_signals[0].company_name or ""
    nace_row = (await db.execute(
        text("SELECT nace_code FROM suppliers WHERE id = :sid LIMIT 1"),
        {"sid": supplier_id},
    )).fetchone()
    trigger_nace = nace_row[0] if nace_row else None

    # Bereits vorhandene Alerts für diesen Lieferanten + Signaltypen
    existing_rows = (await db.execute(
        text("""
            SELECT DISTINCT trigger_signal_type FROM cross_source_alerts
            WHERE organization_id = :org AND trigger_company ILIKE :company
        """),
        {"org": org_id, "company": f"%{company_name[:20]}%"},
    )).fetchall()
    existing_types = {r[0] for r in existing_rows}

    # Pro signal_type den repräsentativsten Signal nehmen
    best_by_type: dict[str, CompanySignalModel] = {}
    for sig in all_signals:
        st = sig.signal_type.lower()
        if st not in RISK_SIGNAL_TYPES:
            continue
        if st not in best_by_type:
            best_by_type[st] = sig

    created = 0
    skipped = 0
    for signal_type, sig in best_by_type.items():
        if signal_type in existing_types:
            skipped += 1
            continue
        try:
            await analyze_cross_impact(
                organization_id=org_id,
                trigger_company=company_name,
                trigger_nace=trigger_nace,
                trigger_signal_type=signal_type,
                trigger_description=sig.description or f"{signal_type} bei {company_name}",
                trigger_signal_id=sig.id,
                session=db,
            )
            await db.flush()
            created += 1
        except Exception as exc:
            logger.warning("cross_analyze_bulk.error", signal_type=signal_type, error=str(exc))
        if created > 0:
            await asyncio.sleep(1.0)

    await db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "signal_types_analyzed": list(best_by_type.keys()),
        "message": f"{created} neue Cross-Source-Alerts erstellt, {skipped} bereits vorhanden.",
    }


@router.get("/cross-alerts")
async def get_cross_alerts(
    status: str | None = None,
    severity: str | None = None,
    supplier_id: str | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gibt alle Cross-Source-Alerts der Organisation zurück."""
    org_id = str(current_user.organization_id)

    where_clauses = ["organization_id = :org"]
    params: dict = {"org": org_id}

    if status:
        where_clauses.append("status = :status")
        params["status"] = status
    if severity:
        where_clauses.append("severity = :severity")
        params["severity"] = severity
    if supplier_id:
        where_clauses.append("affected_suppliers::text LIKE :sid_like")
        params["sid_like"] = f"%{supplier_id}%"

    params["limit"] = min(limit, 200)

    rows = (await db.execute(
        text(f"""
            SELECT id, trigger_company, trigger_nace, trigger_signal_type,
                   trigger_description, impact_type, severity,
                   affected_nace_codes, affected_suppliers, reasoning,
                   recommended_actions, status, created_at
            FROM cross_source_alerts
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        params,
    )).fetchall()

    alerts = []
    for r in rows:
        alerts.append({
            "id": str(r[0]),
            "trigger_company": r[1],
            "trigger_nace": r[2],
            "trigger_signal_type": r[3],
            "trigger_description": r[4],
            "impact_type": r[5],
            "severity": r[6],
            "affected_nace_codes": r[7] if isinstance(r[7], dict) else json.loads(r[7] or "{}"),
            "affected_suppliers": r[8] if isinstance(r[8], list) else json.loads(r[8] or "[]"),
            "reasoning": r[9],
            "recommended_actions": r[10] if isinstance(r[10], list) else json.loads(r[10] or "[]"),
            "status": r[11],
            "created_at": r[12].isoformat() if r[12] else None,
        })

    return {"alerts": alerts, "total": len(alerts)}


@router.post("/activate/{supplier_id}")
async def activate_supplier_intelligence(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aktiviert die vollständige Intelligence-Schicht für einen Lieferanten:
    - company_signals → Digital Twin Timeline (mit KI-Begründungen)
    - HIGH/CRITICAL signals → Surveillance-Tab
    - Trend Alerts → Surveillance-Signale
    """
    from application.intelligence.activator_service import (
        activate_supplier,
        activate_trends_to_surveillance,
    )

    org_id = str(current_user.organization_id)

    signal_result = await activate_supplier(
        supplier_id=supplier_id,
        organization_id=org_id,
        session=db,
    )

    trend_result = {"trend_signals": 0}
    try:
        trend_result = await activate_trends_to_surveillance(
            organization_id=org_id,
            session=db,
            supplier_id=supplier_id,
        )
    except Exception as exc:
        logger.warning("activate.trend_skip", error=str(exc))

    return {
        "supplier_id": supplier_id,
        "twin_events_created": signal_result["twin_events"],
        "surveillance_signals_created": signal_result["surveillance_signals"] + trend_result["trend_signals"],
        "skipped": signal_result["skipped"],
        "total_company_signals": signal_result["total_signals"],
        "message": (
            f"{signal_result['twin_events']} Twin-Ereignisse erstellt, "
            f"{signal_result['surveillance_signals'] + trend_result['trend_signals']} Surveillance-Signale erstellt."
        ),
    }


@router.patch("/cross-alerts/{alert_id}/status")
async def patch_cross_alert_status(
    alert_id: str,
    body: CrossAlertStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aktualisiert den Status eines Cross-Source-Alerts."""
    if body.status not in ("open", "acknowledged", "resolved"):
        raise HTTPException(status_code=400, detail="Invalid status")

    org_id = str(current_user.organization_id)
    async with db.begin():
        result = await db.execute(
            text("""
                UPDATE cross_source_alerts
                SET status = :status
                WHERE id = :id AND organization_id = :org
                RETURNING id
            """),
            {"status": body.status, "id": alert_id, "org": org_id},
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Alert not found")

    return {"id": alert_id, "status": body.status}
