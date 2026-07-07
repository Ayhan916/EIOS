"""Document Intelligence Pipeline — REST API.

Endpoints:
  POST   /documents/sources            → Neue Quelle registrieren
  GET    /documents/sources            → Alle Quellen auflisten
  PATCH  /documents/sources/{id}       → Quelle aktualisieren
  DELETE /documents/sources/{id}       → Quelle löschen
  POST   /documents/sources/{id}/ingest → Manuelle Ingestion triggern
  GET    /documents/files              → Alle verarbeiteten Dokumente
  GET    /documents/files/{id}         → Dokument-Detail mit AI-Extrakten
  POST   /documents/ingest-all         → Alle aktiven Quellen ingesten
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.document_pipeline import (
    DocumentFileModel,
    DocumentSourceModel,
)
from application.rag.document_ingestion import ingest_all_active_sources, ingest_source
from domain.user import User
from interfaces.api.deps import get_current_user, get_db

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Document Intelligence"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class DocumentSourceCreate(BaseModel):
    supplier_id: str | None = None
    company_name: str | None = None
    doc_type: str  # annual_report | sustainability_report | audit_report | csrd_report | csddd_disclosure | sector_risk
    source_url: str
    schedule: str = "monthly"  # daily | weekly | monthly | manual


class DocumentSourceUpdate(BaseModel):
    company_name: str | None = None
    source_url: str | None = None
    schedule: str | None = None
    is_active: bool | None = None


class DocumentSourceOut(BaseModel):
    id: str
    organization_id: str
    supplier_id: str | None
    company_name: str | None
    doc_type: str
    source_url: str
    schedule: str
    is_active: bool
    last_fetched_at: datetime | None
    last_status: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentFileOut(BaseModel):
    id: str
    organization_id: str
    source_id: str
    supplier_id: str | None
    doc_type: str
    title: str | None
    company_name: str | None
    report_year: int | None
    language: str | None
    file_url: str | None
    pages: int | None
    chunks_count: int | None
    esg_score: float | None
    summary: str | None
    extracted_risks: Any | None
    extracted_targets: Any | None
    extracted_commitments: Any | None
    extracted_kpis: Any | None
    status: str
    error_msg: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Sources ───────────────────────────────────────────────────────────────────

@router.post("/sources", response_model=DocumentSourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: DocumentSourceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    source = DocumentSourceModel(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        supplier_id=payload.supplier_id,
        company_name=payload.company_name,
        doc_type=payload.doc_type,
        source_url=payload.source_url,
        schedule=payload.schedule,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(source)
    await db.flush()
    logger.info("documents.source_created", org=org_id, source_id=source.id, doc_type=payload.doc_type)
    return source


@router.get("/sources", response_model=list[DocumentSourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    stmt = select(DocumentSourceModel).where(
        DocumentSourceModel.organization_id == org_id
    ).order_by(DocumentSourceModel.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/sources/{source_id}", response_model=DocumentSourceOut)
async def update_source(
    source_id: str,
    payload: DocumentSourceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    source = await _get_source_or_404(source_id, org_id, db)
    if payload.company_name is not None:
        source.company_name = payload.company_name
    if payload.source_url is not None:
        source.source_url = payload.source_url
    if payload.schedule is not None:
        source.schedule = payload.schedule
    if payload.is_active is not None:
        source.is_active = payload.is_active
    source.updated_at = datetime.now(UTC)
    await db.flush()
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    source = await _get_source_or_404(source_id, org_id, db)
    await db.delete(source)
    await db.flush()


@router.post("/sources/{source_id}/ingest")
async def trigger_ingest(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    source = await _get_source_or_404(source_id, org_id, db)
    stats = await ingest_source(source, db)
    return {"source_id": source_id, "stats": stats}


# ── Files ─────────────────────────────────────────────────────────────────────

@router.get("/files", response_model=list[DocumentFileOut])
async def list_files(
    doc_type: str | None = None,
    supplier_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    stmt = select(DocumentFileModel).where(
        DocumentFileModel.organization_id == org_id
    )
    if doc_type:
        stmt = stmt.where(DocumentFileModel.doc_type == doc_type)
    if supplier_id:
        stmt = stmt.where(DocumentFileModel.supplier_id == supplier_id)
    if status:
        stmt = stmt.where(DocumentFileModel.status == status)
    stmt = stmt.order_by(DocumentFileModel.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/files/{file_id}", response_model=DocumentFileOut)
async def get_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    stmt = select(DocumentFileModel).where(
        DocumentFileModel.id == file_id,
        DocumentFileModel.organization_id == org_id,
    )
    file = (await db.execute(stmt)).scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="Document not found")
    return file


# ── Bulk Ingest ───────────────────────────────────────────────────────────────

@router.post("/ingest-all")
async def ingest_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    org_id = user.organization_id
    stats = await ingest_all_active_sources(org_id, db)
    return {"organization_id": org_id, "stats": stats}


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_source_or_404(source_id: str, org_id: str, db: AsyncSession) -> DocumentSourceModel:
    stmt = select(DocumentSourceModel).where(
        DocumentSourceModel.id == source_id,
        DocumentSourceModel.organization_id == org_id,
    )
    source = (await db.execute(stmt)).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source
