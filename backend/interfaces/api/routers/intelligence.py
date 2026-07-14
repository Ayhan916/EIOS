"""Company Intelligence API — Metriken und Signale aus Dokumenten.

Endpoints:
  GET  /intelligence/metrics          → Alle Kennzahlen (filterbar)
  GET  /intelligence/signals          → Alle Signale (filterbar)
  POST /intelligence/extract-all      → Retroaktive Extraktion aller existing docs
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
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


@router.post("/extract-all")
async def extract_all_intelligence(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retroaktive Extraktion: alle 'done' Dokumente → company_metrics + company_signals."""
    import asyncio
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
        # Load chunks from rag_documents
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

    total_metrics = sum(r.get("metrics", 0) for r in results)
    total_signals = sum(r.get("signals", 0) for r in results)

    logger.info("intelligence.extract_all_done", org=org_id, docs=len(results),
                metrics=total_metrics, signals=total_signals)

    return {
        "processed": len(results),
        "total_metrics": total_metrics,
        "total_signals": total_signals,
        "details": results,
    }
