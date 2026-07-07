"""Document Ingestion Orchestrator — koordiniert alle 5 Agenten.

Pipeline pro DocumentSource:
  1. Crawler Agent   → findet Dokument-URLs
  2. Download Agent  → lädt PDF/HTML herunter
  3. Parser Agent    → Text-Extraktion + Chunking
  4. Analyzer Agent  → LLM-Extraktion (Risiken, Ziele, KPIs)
  5. Indexer Agent   → Embeddings → rag_documents

Sicherheit: Keine automatische Genehmigung, kein Scoring — reine Extraktion.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.document_pipeline import (
    DocumentFileModel,
    DocumentSourceModel,
)

from .crawler_agent import crawl
from .document_analyzer import analyze_document
from .document_indexer import index_document_chunks
from .document_parser import parse_html, parse_pdf, parse_text
from .download_agent import download

logger = structlog.get_logger(__name__)


async def ingest_source(
    source: DocumentSourceModel,
    session: AsyncSession,
) -> dict:
    """Run the full pipeline for one DocumentSource. Returns stats dict."""
    logger.info("doc_ingest.start", source_id=source.id, url=source.source_url)
    stats = {"urls_found": 0, "files_processed": 0, "chunks_indexed": 0, "errors": []}

    try:
        # ── Step 1: Crawl ────────────────────────────────────────────────────
        crawl_result = await crawl(source.source_url, source.doc_type)
        if not crawl_result.ok:
            raise RuntimeError(f"Crawl failed: {crawl_result.error}")
        stats["urls_found"] = len(crawl_result.urls)

        for url in crawl_result.urls:
            try:
                chunks_added = await _process_url(url, source, session)
                stats["files_processed"] += 1
                stats["chunks_indexed"] += chunks_added
            except Exception as exc:
                stats["errors"].append(f"{url}: {exc}")
                logger.error("doc_ingest.url_error", url=url, error=str(exc))

        # Update source status
        source.last_fetched_at = datetime.now(UTC)
        source.last_status = "ok"
        source.last_error = None
        await session.commit()

    except Exception as exc:
        source.last_fetched_at = datetime.now(UTC)
        source.last_status = "error"
        source.last_error = str(exc)
        await session.commit()
        stats["errors"].append(str(exc))

    logger.info("doc_ingest.done", source_id=source.id, **stats)
    return stats


async def _process_url(
    url: str,
    source: DocumentSourceModel,
    session: AsyncSession,
) -> int:
    """Download, parse, analyze and index one URL. Returns chunk count."""

    # ── Step 2: Download ─────────────────────────────────────────────────────
    dl = await download(url)
    if not dl.ok:
        raise RuntimeError(f"Download failed: {dl.error}")

    # ── Step 3: Parse ────────────────────────────────────────────────────────
    if dl.content_type == "pdf":
        parse_result = parse_pdf(dl.content)
    elif dl.content_type == "html":
        parse_result = parse_html(dl.content, url=url)
    else:
        text = dl.content.decode("utf-8", errors="replace") if dl.content else ""
        parse_result = parse_text(text)

    if not parse_result.ok or not parse_result.document:
        raise RuntimeError(f"Parse failed: {parse_result.error}")

    doc = parse_result.document

    # Skip duplicate files by hash
    existing_stmt = select(DocumentFileModel).where(
        DocumentFileModel.organization_id == source.organization_id,
        DocumentFileModel.file_hash == doc.file_hash,
    )
    if (await session.execute(existing_stmt)).scalar_one_or_none():
        logger.info("doc_ingest.duplicate_skipped", hash=doc.file_hash)
        return 0

    # Detect report year from URL or title
    report_year = _extract_year(url) or _extract_year(doc.title or "")

    # Create document_files record
    doc_file = DocumentFileModel(
        id=str(uuid.uuid4()),
        organization_id=source.organization_id,
        source_id=source.id,
        supplier_id=source.supplier_id,
        doc_type=source.doc_type,
        title=doc.title,
        company_name=source.company_name,
        report_year=report_year,
        language=doc.language,
        file_url=url,
        file_hash=doc.file_hash,
        pages=doc.pages,
        status="analyzing",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(doc_file)
    await session.flush()

    # ── Step 4: Analyze ──────────────────────────────────────────────────────
    analysis = analyze_document(
        chunks=doc.chunks,
        doc_type=source.doc_type,
        company_name=source.company_name,
        report_year=report_year,
        language=doc.language,
    )

    doc_file.summary = analysis.get("summary")
    doc_file.extracted_risks = {"items": analysis.get("risks", [])}
    doc_file.extracted_targets = {"items": analysis.get("targets", [])}
    doc_file.extracted_commitments = {"items": analysis.get("commitments", [])}
    doc_file.extracted_kpis = analysis.get("kpis", {})
    doc_file.status = "indexing"
    doc_file.updated_at = datetime.now(UTC)

    # ── Step 5: Index ────────────────────────────────────────────────────────
    chunks_added = await index_document_chunks(
        organization_id=source.organization_id,
        document_file_id=doc_file.id,
        supplier_id=source.supplier_id,
        doc_type=source.doc_type,
        company_name=source.company_name,
        report_year=report_year,
        language=doc.language,
        chunks=doc.chunks,
        session=session,
    )

    doc_file.chunks_count = chunks_added
    doc_file.status = "done"
    doc_file.updated_at = datetime.now(UTC)

    return chunks_added


async def ingest_all_active_sources(
    organization_id: str,
    session: AsyncSession,
) -> dict:
    """Ingest all active document sources for an organization."""
    stmt = select(DocumentSourceModel).where(
        DocumentSourceModel.organization_id == organization_id,
        DocumentSourceModel.is_active == True,  # noqa: E712
    )
    sources = (await session.execute(stmt)).scalars().all()

    total = {"sources": len(sources), "urls_found": 0, "files_processed": 0, "chunks_indexed": 0, "errors": []}
    for source in sources:
        result = await ingest_source(source, session)
        total["urls_found"] += result["urls_found"]
        total["files_processed"] += result["files_processed"]
        total["chunks_indexed"] += result["chunks_indexed"]
        total["errors"].extend(result["errors"])

    return total


def _extract_year(text: str) -> int | None:
    """Extract a plausible report year (2000-2040) from a string."""
    if not text:
        return None
    matches = re.findall(r"\b(20[0-3]\d)\b", text)
    if matches:
        return int(matches[-1])
    return None
