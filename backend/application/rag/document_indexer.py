"""Document Indexer Agent — speichert Chunks als Embeddings in rag_documents.

Nutzt den bestehenden embedder.py (multilingual-e5-large).
Jeder Chunk wird als eigener Eintrag in rag_documents gespeichert mit:
  - doc_type = document file's doc_type
  - source_id = "{document_file_id}:chunk:{index}"
  - content = chunk text
  - embedding = vector(1024)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
) -> int:
    """Embed and store document chunks into rag_documents. Returns count stored."""
    if not chunks:
        return 0

    # Build source_ids for dedup check
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
    signal_type = f"{doc_type}{company_suffix}{year_suffix}"

    count = 0
    for idx, chunk, embedding in zip(new_indices, new_chunks, embeddings):
        doc = RagDocumentModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            supplier_id=supplier_id,
            doc_type=doc_type,
            source_id=source_ids[idx],
            content=chunk,
            embedding=embedding,
            language=language,
            signal_type=signal_type,
            severity=None,
            source_name=company_name,
            published_at=datetime(report_year, 1, 1, tzinfo=UTC) if report_year else None,
            created_at=now,
        )
        session.add(doc)
        count += 1

    logger.info("doc_indexer.done", doc_id=document_file_id, chunks=count)
    return count
