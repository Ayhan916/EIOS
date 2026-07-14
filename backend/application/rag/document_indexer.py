"""Document Indexer Agent — speichert Chunks als Embeddings in rag_documents.

Jeder Chunk wird als eigener Eintrag gespeichert mit vollständigen Metadaten:
  company_name, report_year, document_file_id, doc_class,
  signal_dimension, signal_direction

ADR-009: Parent-Child Chunking via index_document_chunks_parent_child().
  Parent chunks: chunk_level="parent", no embedding, parent_chunk_id=None
  Child chunks:  chunk_level="child",  embedding,    parent_chunk_id=<parent id>
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.chunking import ParentChunk
from infrastructure.persistence.models.rag_documents import RagDocumentModel

from .embedder import embed_passages_batch

logger = structlog.get_logger(__name__)


async def index_document_chunks(
    organization_id: str,
    document_file_id: str,
    supplier_id: str | None,
    doc_type: str,
    company_name: str | None,
    report_year: int | None,
    language: str,
    chunks: list[str],
    session: AsyncSession,
    doc_class: str = "signal",
    signal_dimension: str | None = None,
    signal_direction: str | None = None,
    chunk_pages: list[int] | None = None,
) -> int:
    """Embed and store document chunks into rag_documents. Returns count stored."""
    if not chunks:
        return 0

    source_ids = [f"{document_file_id}:chunk:{i}" for i in range(len(chunks))]

    existing_stmt = select(RagDocumentModel.source_id).where(
        RagDocumentModel.organization_id == organization_id,
        RagDocumentModel.source_id.in_(source_ids),
    )
    existing = set((await session.execute(existing_stmt)).scalars().all())
    new_indices = [i for i, sid in enumerate(source_ids) if sid not in existing]

    if not new_indices:
        logger.info("doc_indexer.all_exist", doc_id=document_file_id)
        return 0

    new_chunks = [chunks[i] for i in new_indices]
    embeddings = embed_passages_batch(new_chunks)

    now = datetime.now(UTC)
    year_suffix = f" ({report_year})" if report_year else ""
    company_suffix = f" — {company_name}" if company_name else ""
    signal_type = f"{doc_type}{company_suffix}{year_suffix}"[:256]

    count = 0
    new_embeddings = iter(embeddings)
    for idx in new_indices:
        chunk = chunks[idx]
        embedding = next(new_embeddings)
        page_no = chunk_pages[idx] if chunk_pages and idx < len(chunk_pages) else None
        doc = RagDocumentModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            supplier_id=supplier_id,
            doc_type=doc_type,
            doc_class=doc_class,
            source_id=source_ids[idx],
            document_file_id=document_file_id,
            company_name=company_name,
            report_year=report_year,
            content=chunk,
            embedding=embedding,
            language=language,
            signal_type=signal_type,
            signal_dimension=signal_dimension,
            signal_direction=signal_direction,
            severity=None,
            source_name=company_name,
            published_at=datetime(report_year, 1, 1, tzinfo=UTC) if report_year else None,
            created_at=now,
            page_number=page_no,
        )
        session.add(doc)
        count += 1

    logger.info(
        "doc_indexer.done",
        doc_id=document_file_id,
        chunks=count,
        doc_class=doc_class,
        company=company_name,
        year=report_year,
    )
    return count


async def index_document_chunks_parent_child(
    organization_id: str,
    document_file_id: str,
    supplier_id: str | None,
    doc_type: str,
    company_name: str | None,
    report_year: int | None,
    language: str,
    parent_chunks: list[ParentChunk],
    session: AsyncSession,
    doc_class: str = "financial",
    signal_dimension: str | None = None,
) -> int:
    """Store Parent-Child chunks into rag_documents (ADR-009).

    Parents: chunk_level="parent", no embedding — provide table context to LLM.
    Children: chunk_level="child", embedded — actual retrieval units.

    Returns total number of child rows stored (embeddings created).
    """
    if not parent_chunks:
        return 0

    now = datetime.now(UTC)
    year_suffix = f" ({report_year})" if report_year else ""
    company_suffix = f" — {company_name}" if company_name else ""
    signal_type = f"{doc_type}{company_suffix}{year_suffix}"[:256]
    published_at = datetime(report_year, 1, 1, tzinfo=UTC) if report_year else None

    # Base metadata shared by all rows in this document
    base_meta = dict(
        organization_id=organization_id,
        supplier_id=supplier_id,
        doc_type=doc_type,
        doc_class=doc_class,
        document_file_id=document_file_id,
        company_name=company_name,
        report_year=report_year,
        language=language,
        signal_type=signal_type,
        signal_dimension=signal_dimension,
        signal_direction=None,
        severity=None,
        source_name=company_name,
        published_at=published_at,
        created_at=now,
    )

    child_count = 0

    for parent in parent_chunks:
        parent_source_id = f"{document_file_id}:parent:{parent.parent_index}"

        # Check if parent already stored (idempotency)
        existing = (
            await session.execute(
                select(RagDocumentModel.id).where(
                    RagDocumentModel.organization_id == organization_id,
                    RagDocumentModel.source_id == parent_source_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            parent_db_id = existing
        else:
            parent_db_id = str(uuid.uuid4())
            session.add(RagDocumentModel(
                id=parent_db_id,
                source_id=parent_source_id,
                content=parent.text,
                embedding=None,          # parents are NOT embedded
                chunk_level="parent",
                parent_chunk_id=None,
                **base_meta,
            ))

        # Collect children that need embedding
        child_texts = [c.text for c in parent.children]
        child_source_ids = [
            f"{document_file_id}:child:{parent.parent_index}:{c.child_index}"
            for c in parent.children
        ]

        existing_children = set(
            (
                await session.execute(
                    select(RagDocumentModel.source_id).where(
                        RagDocumentModel.organization_id == organization_id,
                        RagDocumentModel.source_id.in_(child_source_ids),
                    )
                )
            ).scalars().all()
        )

        new_children = [
            (c, child_source_ids[i])
            for i, c in enumerate(parent.children)
            if child_source_ids[i] not in existing_children
        ]

        if not new_children:
            continue

        embeddings = embed_passages_batch([c.text for c, _ in new_children])

        for (child, source_id), embedding in zip(new_children, embeddings):
            session.add(RagDocumentModel(
                id=str(uuid.uuid4()),
                source_id=source_id,
                content=child.text,
                embedding=embedding,
                chunk_level="child",
                parent_chunk_id=parent_db_id,
                **base_meta,
            ))
            child_count += 1

    logger.info(
        "doc_indexer.parent_child_done",
        doc_id=document_file_id,
        parents=len(parent_chunks),
        children=child_count,
        company=company_name,
        year=report_year,
    )
    return child_count
