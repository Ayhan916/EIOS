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
from .document_classifier import get_doc_class, get_signal_dimension
from .document_indexer import index_document_chunks, index_document_chunks_parent_child
from .document_parser import parse_html, parse_pdf, parse_text
from .download_agent import download
from .metric_extractor import extract_and_store_intelligence
from .parent_child_chunker import PARENT_CHILD_DOC_TYPES, chunk_parent_child

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

        # Update source status — error if no files were produced despite having errors
        source.last_fetched_at = datetime.now(UTC)
        if stats["files_processed"] == 0 and stats["errors"]:
            source.last_status = "error"
            source.last_error = "; ".join(stats["errors"][:3])
        else:
            source.last_status = "ok"
            source.last_error = None
        await session.flush()

    except Exception as exc:
        source.last_fetched_at = datetime.now(UTC)
        source.last_status = "error"
        source.last_error = str(exc)
        await session.flush()
        stats["errors"].append(str(exc))

    logger.info("doc_ingest.done", source_id=source.id, **stats)
    return stats


async def _process_url(
    url: str,
    source: DocumentSourceModel,
    session: AsyncSession,
) -> int:
    """Download, parse, analyze and index one URL. Returns chunk count."""
    dl = await download(url)
    if not dl.ok:
        raise RuntimeError(f"Download failed: {dl.error}")
    return await _process_content(dl.content, dl.content_type, url, source, session)


async def _process_content(
    content: bytes,
    content_type: str,
    url: str,
    source: DocumentSourceModel,
    session: AsyncSession,
    report_year_override: int | None = None,
    title_override: str | None = None,
) -> int:
    """Parse, analyze and index raw content. Returns chunk count."""

    # ── Step 3: Parse ────────────────────────────────────────────────────────
    if content_type == "pdf":
        parse_result = parse_pdf(content)
    elif content_type == "html":
        parse_result = parse_html(content, url=url)
    else:
        text = content.decode("utf-8", errors="replace") if content else ""
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

    report_year = report_year_override or _extract_year(url) or _extract_year(doc.title or "")
    if title_override:
        doc.title = title_override

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
        parse_layout=doc.parse_layout if doc.parse_layout else None,
        status="analyzing",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(doc_file)
    await session.flush()

    # ── Step 4: Analyze ──────────────────────────────────────────────────────
    analysis = await analyze_document(
        chunks=doc.chunks,
        doc_type=source.doc_type,
        company_name=source.company_name,
        report_year=report_year,
        language=doc.language,
        total_pages=doc.pages or 1,
        sections=doc.sections or [],
    )

    doc_file.summary = analysis.get("summary")
    doc_file.extracted_risks = analysis.get("risks", [])
    doc_file.extracted_targets = analysis.get("targets", [])
    doc_file.extracted_commitments = analysis.get("commitments", [])
    doc_file.extracted_kpis = analysis.get("kpis", {})
    doc_file.status = "indexing"
    doc_file.updated_at = datetime.now(UTC)

    doc_class = get_doc_class(source.doc_type)
    signal_dimension = analysis.get("signal_dimension") or get_signal_dimension(doc_class)
    signal_direction = analysis.get("signal_direction") or "neutral"

    # ── Step 5: Index ────────────────────────────────────────────────────────
    # ADR-009: use parent-child chunking for dense tabular documents
    if source.doc_type in PARENT_CHILD_DOC_TYPES:
        full_text = " ".join(doc.chunks)   # re-join to apply new strategy
        parent_chunks = chunk_parent_child(full_text)
        chunks_added = await index_document_chunks_parent_child(
            organization_id=source.organization_id,
            document_file_id=doc_file.id,
            supplier_id=source.supplier_id,
            doc_type=source.doc_type,
            company_name=source.company_name,
            report_year=report_year,
            language=doc.language,
            parent_chunks=parent_chunks,
            session=session,
            doc_class=doc_class,
            signal_dimension=signal_dimension,
        )
    else:
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
            doc_class=doc_class,
            signal_dimension=signal_dimension,
            signal_direction=signal_direction,
            chunk_pages=doc.chunk_pages if doc.chunk_pages else None,
        )

    doc_file.chunks_count = chunks_added
    doc_file.status = "done"
    doc_file.updated_at = datetime.now(UTC)

    return chunks_added


async def ingest_uploaded_file(
    source: DocumentSourceModel,
    content: bytes,
    content_type: str,
    filename: str,
    session: AsyncSession,
    report_year: int | None = None,
    title_override: str | None = None,
) -> dict:
    """Process an uploaded PDF/HTML file through the pipeline (skips crawl + download)."""
    stats = {"urls_found": 1, "files_processed": 0, "chunks_indexed": 0, "errors": []}
    url = f"upload://{filename}"
    try:
        chunks_added = await _process_content(
            content, content_type, url, source, session,
            report_year_override=report_year,
            title_override=title_override,
        )
        stats["files_processed"] = 1
        stats["chunks_indexed"] = chunks_added
        source.last_fetched_at = datetime.now(UTC)
        source.last_status = "ok"
        source.last_error = None
        await session.flush()
    except Exception as exc:
        stats["errors"].append(str(exc))
        source.last_fetched_at = datetime.now(UTC)
        source.last_status = "error"
        source.last_error = str(exc)
        await session.flush()
    logger.info("doc_ingest.upload_done", source_id=source.id, **stats)
    return stats


async def ingest_uploaded_file_fast(
    source: DocumentSourceModel,
    content: bytes,
    content_type: str,
    filename: str,
    session: AsyncSession,
    report_year: int | None = None,
    title_override: str | None = None,
) -> dict:
    """
    Truly fast upload path: save file → dedup check → create DB record → return in <1s.

    Heavy work (Docling parsing, LLM analysis, embedding) runs in process_document_background().
    """
    import hashlib
    import os
    from shared.config import settings

    stats: dict = {"urls_found": 1, "files_processed": 0, "chunks_indexed": 0, "errors": [], "doc_file_id": None}

    try:
        # 1. Compute raw file hash for dedup (no parsing needed)
        file_hash = hashlib.sha256(content).hexdigest()

        # 2. Dedup check against raw hash
        existing_stmt = select(DocumentFileModel).where(
            DocumentFileModel.organization_id == source.organization_id,
            DocumentFileModel.file_hash == file_hash,
        )
        if (await session.execute(existing_stmt)).scalar_one_or_none():
            logger.info("doc_ingest.duplicate_skipped", hash=file_hash[:16])
            stats["files_processed"] = 0
            return stats

        # 3. Persist raw file to disk
        storage_dir = os.path.join(settings.upload_storage_path, source.organization_id)
        os.makedirs(storage_dir, exist_ok=True)
        stored_path = os.path.join(storage_dir, f"{file_hash[:16]}_{filename}")
        if not os.path.exists(stored_path):
            with open(stored_path, "wb") as fh:
                fh.write(content)
        logger.info("doc_ingest.file_stored", path=stored_path, bytes=len(content))

        # 4. Extract year from filename / title override (no LLM, no parse)
        title = title_override or filename.removesuffix(".pdf").replace("_", " ")
        year = report_year or _extract_year(filename) or _extract_year(title)

        # 5. Create DB record immediately — parsing happens in background
        doc_file = DocumentFileModel(
            id=str(uuid.uuid4()),
            organization_id=source.organization_id,
            source_id=source.id,
            supplier_id=source.supplier_id,
            doc_type=source.doc_type,
            title=title,
            company_name=source.company_name,
            report_year=year,
            language=None,
            file_url=stored_path,
            file_hash=file_hash,
            pages=None,
            status="pending",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(doc_file)
        source.last_fetched_at = datetime.now(UTC)
        source.last_status = "ok"
        source.last_error = None
        await session.flush()

        stats["files_processed"] = 1
        stats["doc_file_id"] = doc_file.id
        stats["background_args"] = {
            "doc_file_id": doc_file.id,
            "file_path": stored_path,
            "content_type": content_type,
            "org_id": source.organization_id,
            "supplier_id": source.supplier_id,
            "doc_type": source.doc_type,
            "company_name": source.company_name,
            "report_year": year,
        }

        logger.info("doc_ingest.queued", source_id=source.id, doc_file_id=doc_file.id)

    except Exception as exc:
        stats["errors"].append(str(exc))
        source.last_fetched_at = datetime.now(UTC)
        source.last_status = "error"
        source.last_error = str(exc)
        await session.flush()

    return stats


async def process_document_background(
    doc_file_id: str,
    org_id: str,
    supplier_id: str | None,
    doc_type: str,
    company_name: str | None,
    report_year: int | None,
    # New path: parse from file on disk
    file_path: str | None = None,
    content_type: str = "pdf",
    # Legacy path: pre-parsed chunks passed in directly
    language: str = "de",
    total_pages: int = 1,
    sections: list[str] | None = None,
    chunks: list[str] | None = None,
) -> None:
    """Background task: parse (if needed) → Groq analysis + embedding + index."""
    import asyncio
    from infrastructure.persistence.database import AsyncSessionFactory

    sections = sections or []
    chunks = chunks or []

    logger.info("doc_ingest.bg_start", doc_file_id=doc_file_id, file_path=file_path, pre_chunks=len(chunks))

    async def _set_status(status: str, error: str | None = None) -> None:
        try:
            async with AsyncSessionFactory() as s:
                async with s.begin():
                    f = (await s.execute(
                        select(DocumentFileModel).where(DocumentFileModel.id == doc_file_id)
                    )).scalar_one_or_none()
                    if f:
                        f.status = status
                        if error:
                            f.error_msg = error[:500]
                        f.updated_at = datetime.now(UTC)
        except Exception as exc:
            logger.error("doc_ingest.bg_status_error", error=str(exc))

    try:
        # ── Step 0: Parse file from disk if chunks not pre-supplied ──────────────
        if file_path and not chunks:
            await _set_status("parsing")
            try:
                with open(file_path, "rb") as fh:
                    raw = fh.read()
                loop = asyncio.get_event_loop()
                if content_type == "pdf":
                    parse_result = await loop.run_in_executor(None, parse_pdf, raw)
                elif content_type == "html":
                    parse_result = await loop.run_in_executor(None, parse_html, raw, f"upload://{file_path}")
                else:
                    text = raw.decode("utf-8", errors="replace")
                    parse_result = parse_text(text)

                if not parse_result.ok or not parse_result.document:
                    await _set_status("failed", f"Parse error: {parse_result.error}")
                    return

                doc = parse_result.document
                chunks = doc.chunks
                sections = doc.sections or []
                language = doc.language or "de"
                total_pages = doc.pages or 1

                # Update DB with parsed metadata
                # Try to extract year from doc title / first chunk if still unknown
                if not report_year:
                    report_year = (
                        _extract_year(doc.title or "")
                        or _extract_year(chunks[0] if chunks else "")
                    )
                async with AsyncSessionFactory() as s:
                    async with s.begin():
                        f = (await s.execute(
                            select(DocumentFileModel).where(DocumentFileModel.id == doc_file_id)
                        )).scalar_one_or_none()
                        if f:
                            f.pages = total_pages
                            f.language = language
                            if doc.title and not f.title:
                                f.title = doc.title
                            if report_year and not f.report_year:
                                f.report_year = report_year
                            # Store full parsed text for QA review (truncate at 2MB)
                            f.parsed_text = "\n\n".join(chunks)[:2_000_000]
                            f.updated_at = datetime.now(UTC)

                logger.info("doc_ingest.bg_parsed", doc_file_id=doc_file_id, chunks=len(chunks), pages=total_pages)
            except Exception as exc:
                await _set_status("failed", f"Parse exception: {exc}")
                logger.error("doc_ingest.bg_parse_error", doc_file_id=doc_file_id, error=str(exc))
                return

        await _set_status("analyzing")

        from infrastructure.llm.deps import get_org_job_llm_provider, get_org_pipeline_settings
        async with AsyncSessionFactory() as _s:
            async with _s.begin():
                _analysis_llm = await get_org_job_llm_provider(org_id, "analysis", _s)
                _pipe_settings = await get_org_pipeline_settings(org_id, _s)

        # Re-chunk from stored parsed_text using org chunk settings if available
        _org_chunk_size = _pipe_settings.get("chunk_size", 800)
        _org_chunk_overlap = _pipe_settings.get("chunk_overlap", 80)
        if chunks and (_org_chunk_size != 800 or _org_chunk_overlap != 80):
            _words = " ".join(chunks).split()
            _rechunked: list[str] = []
            _start = 0
            while _start < len(_words):
                _end = min(_start + _org_chunk_size, len(_words))
                _chunk = " ".join(_words[_start:_end])
                if len(_chunk.strip()) > 50:
                    _rechunked.append(_chunk.strip())
                if _end >= len(_words):
                    break
                _start = _end - _org_chunk_overlap
            if _rechunked:
                chunks = _rechunked
            logger.info(
                "doc_ingest.bg_rechunked",
                doc_file_id=doc_file_id,
                chunk_size=_org_chunk_size,
                chunk_overlap=_org_chunk_overlap,
                chunks=len(chunks),
            )

        analysis = await analyze_document(
            chunks=chunks,
            doc_type=doc_type,
            company_name=company_name,
            report_year=report_year,
            language=language,
            total_pages=total_pages,
            sections=sections,
            llm_provider=_analysis_llm,
        )

        async with AsyncSessionFactory() as session:
            async with session.begin():
                f = (await session.execute(
                    select(DocumentFileModel).where(DocumentFileModel.id == doc_file_id)
                )).scalar_one_or_none()
                if not f:
                    logger.warning("doc_ingest.bg_doc_gone", doc_file_id=doc_file_id)
                    return

                f.summary = analysis.get("summary")
                f.extracted_risks = analysis.get("risks", [])
                f.extracted_targets = analysis.get("targets", [])
                f.extracted_commitments = analysis.get("commitments", [])
                f.extracted_kpis = analysis.get("kpis", {})
                f.status = "indexing"
                f.updated_at = datetime.now(UTC)
                await session.flush()

                doc_class = get_doc_class(doc_type)
                signal_dimension = analysis.get("signal_dimension") or get_signal_dimension(doc_class)
                signal_direction = analysis.get("signal_direction") or "neutral"

                chunks_added = await index_document_chunks(
                    organization_id=org_id,
                    document_file_id=doc_file_id,
                    supplier_id=supplier_id,
                    doc_type=doc_type,
                    company_name=company_name,
                    report_year=report_year,
                    language=language,
                    chunks=chunks,
                    session=session,
                    doc_class=doc_class,
                    signal_dimension=signal_dimension,
                    signal_direction=signal_direction,
                )

                f.chunks_count = chunks_added
                f.status = "done"
                f.updated_at = datetime.now(UTC)

        # ── Step 6: Extract structured metrics + signals ──────────────────────
        async with AsyncSessionFactory() as session:
            async with session.begin():
                _extraction_llm = await get_org_job_llm_provider(org_id, "extraction", session)
                intel = await extract_and_store_intelligence(
                    organization_id=org_id,
                    doc_file_id=doc_file_id,
                    doc_class=get_doc_class(doc_type),
                    company_name=company_name,
                    supplier_id=supplier_id,
                    report_year=report_year,
                    chunks=chunks,
                    session=session,
                    llm_provider=_extraction_llm,
                )

        logger.info("doc_ingest.bg_done", doc_file_id=doc_file_id, chunks_added=chunks_added, **intel)

        # ── Step 6b: Year-over-Year comparison ────────────────────────────────
        if intel.get("metrics", 0) > 0 and company_name and report_year:
            try:
                from application.intelligence.yoy_comparator import generate_yoy_comparison
                async with AsyncSessionFactory() as session:
                    async with session.begin():
                        yoy = await generate_yoy_comparison(
                            organization_id=org_id,
                            company_name=company_name,
                            supplier_id=supplier_id,
                            report_year=report_year,
                            source_doc_id=doc_file_id,
                            session=session,
                        )
                logger.info("doc_ingest.yoy_done", doc_file_id=doc_file_id, **yoy)
            except Exception as exc:
                logger.warning("doc_ingest.yoy_error", doc_file_id=doc_file_id, error=str(exc))

        # ── Step 7: Notify webhook subscribers if supplier is known ───────────
        if supplier_id and (intel.get("metrics", 0) > 0 or intel.get("signals", 0) > 0):
            try:
                from interfaces.api.routers.api_platform import dispatch_webhook_event  # noqa: PLC0415
                await dispatch_webhook_event(
                    org_id,
                    "supplier.intelligence_updated",
                    {
                        "supplier_id": supplier_id,
                        "doc_file_id": doc_file_id,
                        "doc_type": doc_type,
                        "report_year": report_year,
                        "metrics_extracted": intel.get("metrics", 0),
                        "signals_extracted": intel.get("signals", 0),
                    },
                )
            except Exception:
                pass  # webhook failure must never break the pipeline

    except Exception as exc:
        logger.error("doc_ingest.bg_error", doc_file_id=doc_file_id, error=str(exc))
        await _set_status("error", str(exc))


async def reclassify_document(
    doc_file_id: str,
    org_id: str,
    session: AsyncSession,
    model: str | None = None,
) -> dict:
    """Re-classify an existing document using stored chunk text. Updates document_files + rag_documents."""
    import asyncio
    from sqlalchemy import update as sql_update
    from .document_classifier import classify_with_groq, get_doc_class, get_signal_dimension, DOC_TYPES
    from infrastructure.persistence.models.rag_documents import RagDocumentModel

    doc_file = (await session.execute(
        select(DocumentFileModel).where(
            DocumentFileModel.id == doc_file_id,
            DocumentFileModel.organization_id == org_id,
        )
    )).scalar_one_or_none()
    if not doc_file:
        return {"error": "not_found", "doc_file_id": doc_file_id}

    # Use first 15 chunks as text input for the classifier
    chunk_rows = (await session.execute(
        select(RagDocumentModel.content)
        .where(RagDocumentModel.document_file_id == doc_file_id)
        .order_by(RagDocumentModel.created_at.asc())
        .limit(15)
    )).scalars().all()

    if not chunk_rows:
        return {"error": "no_chunks", "doc_file_id": doc_file_id}

    text_excerpt = " ".join(chunk_rows)
    filename = (doc_file.file_url or "").replace("upload://", "") or doc_file.title or "unknown.pdf"

    from infrastructure.llm.deps import get_org_job_llm_provider, build_provider_for_model
    llm_provider = build_provider_for_model(model) if model else await get_org_job_llm_provider(org_id, "classification", session)
    groq_result = await classify_with_groq(text_excerpt, filename, llm=llm_provider)
    if not groq_result:
        return {"error": "classifier_failed", "doc_file_id": doc_file_id}

    old_doc_type = doc_file.doc_type

    new_doc_type = (
        groq_result.get("doc_type") if groq_result.get("doc_type") in DOC_TYPES else doc_file.doc_type
    )
    new_company_name = groq_result.get("company_name") or doc_file.company_name
    new_report_year = groq_result.get("report_year") or doc_file.report_year
    new_language = groq_result.get("language") or doc_file.language or "de"
    new_title = groq_result.get("title") or doc_file.title
    new_doc_class = get_doc_class(new_doc_type)
    new_signal_dimension = get_signal_dimension(new_doc_class)

    # Update document_files
    doc_file.doc_type = new_doc_type
    doc_file.company_name = new_company_name
    doc_file.report_year = new_report_year
    doc_file.language = new_language
    if new_title:
        doc_file.title = new_title
    if "confidence" in groq_result:
        doc_file.classification_confidence = float(groq_result["confidence"])
    if "alternatives" in groq_result:
        doc_file.classification_alternatives = groq_result["alternatives"]
    if "evidence_passages" in groq_result:
        doc_file.classification_evidence = groq_result["evidence_passages"]
    doc_file.updated_at = datetime.now(UTC)

    # Update all rag_documents for this file
    year_suffix = f" ({new_report_year})" if new_report_year else ""
    company_suffix = f" — {new_company_name}" if new_company_name else ""
    new_signal_type = f"{new_doc_type}{company_suffix}{year_suffix}"[:256]

    await session.execute(
        sql_update(RagDocumentModel)
        .where(RagDocumentModel.document_file_id == doc_file_id)
        .values(
            doc_type=new_doc_type,
            doc_class=new_doc_class,
            company_name=new_company_name,
            report_year=new_report_year,
            signal_type=new_signal_type,
            signal_dimension=new_signal_dimension,
        )
    )

    await session.flush()

    logger.info(
        "doc_ingest.reclassified",
        doc_file_id=doc_file_id,
        old_type=old_doc_type,
        new_type=new_doc_type,
        company=new_company_name,
        year=new_report_year,
    )

    return {
        "doc_file_id": doc_file_id,
        "old_doc_type": old_doc_type,
        "new_doc_type": new_doc_type,
        "new_doc_class": new_doc_class,
        "new_company_name": new_company_name,
        "new_report_year": new_report_year,
        "changed": old_doc_type != new_doc_type,
        "confidence": groq_result.get("confidence"),
        "alternatives": groq_result.get("alternatives", []),
        "evidence_passages": groq_result.get("evidence_passages", []),
    }


async def reclassify_all_documents(
    org_id: str,
    session: AsyncSession,
) -> dict:
    """Re-classify all 'done' documents sequentially (avoids rate limit). Returns summary."""
    import asyncio

    stmt = select(DocumentFileModel).where(
        DocumentFileModel.organization_id == org_id,
        DocumentFileModel.status == "done",
    ).order_by(DocumentFileModel.created_at.asc())
    doc_files = (await session.execute(stmt)).scalars().all()

    results = []
    for i, doc_file in enumerate(doc_files):
        result = await reclassify_document(doc_file.id, org_id, session)
        results.append(result)
        # Small pause between calls to respect rate limits
        if i < len(doc_files) - 1:
            await asyncio.sleep(1.5)

    changed = [r for r in results if r.get("changed")]
    errors = [r for r in results if "error" in r]

    logger.info("doc_ingest.reclassify_all_done", total=len(results), changed=len(changed), errors=len(errors))
    return {
        "total": len(results),
        "changed": len(changed),
        "errors": len(errors),
        "details": results,
    }


async def reanalyze_document(
    doc_file_id: str,
    org_id: str,
    session: AsyncSession,
    model: str | None = None,
    extra_context: str | None = None,
) -> dict:
    """Re-run LLM analysis (KPI/risk/summary extraction) for an existing document using stored chunks."""
    from infrastructure.persistence.models.rag_documents import RagDocumentModel

    doc_file = (await session.execute(
        select(DocumentFileModel).where(
            DocumentFileModel.id == doc_file_id,
            DocumentFileModel.organization_id == org_id,
        )
    )).scalar_one_or_none()
    if not doc_file:
        return {"error": "not_found"}

    chunk_rows = (await session.execute(
        select(RagDocumentModel.content)
        .where(RagDocumentModel.document_file_id == doc_file_id)
        .order_by(RagDocumentModel.created_at.asc())
        .limit(60)
    )).scalars().all()

    if not chunk_rows:
        return {"error": "no_chunks"}

    from infrastructure.llm.deps import get_org_job_llm_provider, build_provider_for_model
    llm_provider = build_provider_for_model(model) if model else await get_org_job_llm_provider(org_id, "analysis", session)
    doc_type = doc_file.doc_type or "sustainability_report"
    analysis = await analyze_document(
        chunks=list(chunk_rows),
        doc_type=doc_type,
        company_name=doc_file.company_name,
        report_year=doc_file.report_year,
        language=doc_file.language or "de",
        total_pages=doc_file.pages or 1,
        llm_provider=llm_provider,
        extra_context=extra_context,
    )

    doc_file.summary = analysis.get("summary")
    doc_file.extracted_risks = analysis.get("risks", [])
    doc_file.extracted_targets = analysis.get("targets", [])
    doc_file.extracted_commitments = analysis.get("commitments", [])
    doc_file.extracted_kpis = analysis.get("kpis", {})
    doc_file.updated_at = datetime.now(UTC)
    await session.flush()

    logger.info("doc_ingest.reanalyzed", doc_id=doc_file_id, doc_type=doc_type, has_summary=bool(doc_file.summary))
    return {
        "doc_file_id": doc_file_id,
        "doc_type": doc_type,
        "has_summary": bool(doc_file.summary),
        "kpi_count": len([v for v in (doc_file.extracted_kpis or {}).values() if v is not None]),
    }


async def reparse_document(
    doc_file_id: str,
    org_id: str,
    session: AsyncSession,
    parse_engine: str = "docling",
    ocr_enabled: bool = True,
    extract_tables: bool = True,
    describe_pictures: bool = False,
) -> dict:
    """Re-parse the stored PDF with configurable engine and options."""
    import asyncio
    from application.rag.document_parser import parse_pdf, parse_html

    doc_file = (await session.execute(
        select(DocumentFileModel).where(
            DocumentFileModel.id == doc_file_id,
            DocumentFileModel.organization_id == org_id,
        )
    )).scalar_one_or_none()
    if not doc_file:
        return {"error": "not_found"}

    file_url = doc_file.file_url or ""
    file_path = file_url.replace("upload://", "") if file_url.startswith("upload://") else file_url
    if not file_path or not __import__("os").path.isfile(file_path):
        return {"error": "no_file"}

    doc_file.status = "parsing"
    doc_file.updated_at = datetime.now(UTC)
    await session.flush()

    try:
        loop = asyncio.get_event_loop()
        with open(file_path, "rb") as fh:
            raw = fh.read()
        is_html = file_path.endswith(".html")
        if is_html:
            parse_fn = lambda b: parse_html(b)
        else:
            import functools
            parse_fn = functools.partial(
                parse_pdf,
                parse_engine=parse_engine,
                ocr_enabled=ocr_enabled,
                extract_tables=extract_tables,
                describe_pictures=describe_pictures,
            )
        parse_result = await loop.run_in_executor(None, parse_fn, raw)

        doc = parse_result.document if parse_result.ok else None
        doc_file.parsed_text = "\n\n".join(doc.chunks if doc else [])
        doc_file.pages = doc.pages if doc else doc_file.pages
        if doc and getattr(doc, "parse_layout", None):
            doc_file.parse_layout = doc.parse_layout
        doc_file.status = "done"
        doc_file.updated_at = datetime.now(UTC)
        await session.flush()

        return {"doc_file_id": doc_file_id, "pages": doc_file.pages, "chars": len(doc_file.parsed_text or "")}
    except Exception as exc:
        doc_file.status = "failed"
        doc_file.error_msg = str(exc)[:500]
        await session.flush()
        return {"error": str(exc)}


async def rechunk_document(
    doc_file_id: str,
    org_id: str,
    session: AsyncSession,
    chunk_size: int = 800,
    chunk_overlap: int = 80,
    chunk_strategy: str = "sliding_window",
) -> dict:
    """Delete existing chunks and re-chunk + re-embed + re-index from stored parsed_text.

    chunk_strategy:
      sliding_window — word-based overlapping windows (default)
      semantic / by_section — section-aware chunking using Markdown headings
    """
    from infrastructure.persistence.models.rag_documents import RagDocumentModel
    from application.rag.document_parser import _chunk_text, _chunk_markdown
    from sqlalchemy import delete as sql_delete

    doc_file = (await session.execute(
        select(DocumentFileModel).where(
            DocumentFileModel.id == doc_file_id,
            DocumentFileModel.organization_id == org_id,
        )
    )).scalar_one_or_none()
    if not doc_file:
        return {"error": "not_found"}
    if not doc_file.parsed_text:
        return {"error": "no_parsed_text"}

    doc_file.status = "indexing"
    doc_file.updated_at = datetime.now(UTC)
    await session.flush()

    # Delete existing chunks
    await session.execute(
        sql_delete(RagDocumentModel).where(RagDocumentModel.document_file_id == doc_file_id)
    )
    await session.flush()

    # Re-chunk according to strategy
    if chunk_strategy in ("semantic", "by_section"):
        # Section-aware: split on Markdown headings, merge/split by _CHUNK_SIZE
        chunks = _chunk_markdown(doc_file.parsed_text)
        # If the stored text has no headings, fall back to sliding window
        if not chunks:
            chunks = _chunk_text(doc_file.parsed_text)
    else:
        # Sliding window with configurable size/overlap
        words = doc_file.parsed_text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            if len(chunk.strip()) > 50:
                chunks.append(chunk.strip())
            if end >= len(words):
                break
            start = end - chunk_overlap

    from application.rag.document_indexer import index_document_chunks

    doc_class = get_doc_class(doc_file.doc_type or "sustainability_report")
    chunks_added = await index_document_chunks(
        organization_id=org_id,
        document_file_id=doc_file_id,
        supplier_id=doc_file.supplier_id,
        doc_type=doc_file.doc_type or "sustainability_report",
        company_name=doc_file.company_name,
        report_year=doc_file.report_year,
        language=doc_file.language or "de",
        chunks=chunks,
        session=session,
        doc_class=doc_class,
        signal_dimension=get_signal_dimension(doc_class),
    )

    doc_file.chunks_count = chunks_added
    doc_file.status = "done"
    doc_file.updated_at = datetime.now(UTC)
    await session.flush()

    return {"doc_file_id": doc_file_id, "chunks_added": chunks_added}


async def reextract_metrics(
    doc_file_id: str,
    org_id: str,
    session: AsyncSession,
    model: str | None = None,
) -> dict:
    """Re-run metric extractor (ESG + financial) for an existing document."""
    from infrastructure.persistence.models.rag_documents import RagDocumentModel
    from application.rag.metric_extractor import extract_and_store_intelligence

    doc_file = (await session.execute(
        select(DocumentFileModel).where(
            DocumentFileModel.id == doc_file_id,
            DocumentFileModel.organization_id == org_id,
        )
    )).scalar_one_or_none()
    if not doc_file:
        return {"error": "not_found"}

    chunk_rows = (await session.execute(
        select(RagDocumentModel.content)
        .where(RagDocumentModel.document_file_id == doc_file_id)
        .order_by(RagDocumentModel.created_at.asc())
        .limit(60)
    )).scalars().all()

    if not chunk_rows:
        return {"error": "no_chunks"}

    from infrastructure.llm.deps import get_org_job_llm_provider, build_provider_for_model
    llm_provider = build_provider_for_model(model) if model else await get_org_job_llm_provider(org_id, "extraction", session)
    doc_class = get_doc_class(doc_file.doc_type or "sustainability_report")
    result = await extract_and_store_intelligence(
        organization_id=org_id,
        doc_file_id=doc_file_id,
        doc_class=doc_class,
        company_name=doc_file.company_name or "",
        supplier_id=doc_file.supplier_id,
        report_year=doc_file.report_year,
        chunks=list(chunk_rows),
        session=session,
        llm_provider=llm_provider,
    )

    return {"doc_file_id": doc_file_id, **result}


async def ingest_all_active_sources(
    organization_id: str,
    session: AsyncSession,
) -> dict:
    """Ingest all active document sources for an organization."""
    stmt = select(DocumentSourceModel).where(
        DocumentSourceModel.organization_id == organization_id,
        DocumentSourceModel.is_active == True,  # noqa: E712
        ~DocumentSourceModel.source_url.startswith("upload://"),
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
