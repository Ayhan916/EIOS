"""
Re-index all existing documents with the new Docling parser.

Usage:
    python run_reindex_docling.py [--dry-run] [--doc-file-id <id>]

What it does:
  1. Finds all document_files where file_url points to a stored file on disk
  2. Deletes existing rag_documents for that file
  3. Re-parses with Docling (tables, sections, semantic chunking)
  4. Re-indexes with new chunks
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import structlog

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import delete, select, text

from application.rag.document_indexer import (
    index_document_chunks,
    index_document_chunks_parent_child,
)
from application.rag.document_parser import parse_pdf
from application.rag.document_classifier import get_doc_class, get_signal_dimension
from application.rag.parent_child_chunker import PARENT_CHILD_DOC_TYPES, chunk_parent_child
from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.models.document_pipeline import DocumentFileModel
from infrastructure.persistence.models.rag_documents import RagDocumentModel

logger = structlog.get_logger(__name__)


async def reindex_document(doc_file: DocumentFileModel, session, dry_run: bool) -> dict:
    file_url = doc_file.file_url or ""

    # Only process files that exist on disk
    if not file_url or not os.path.exists(file_url):
        return {"skipped": True, "reason": f"file not on disk: {file_url}"}

    logger.info(
        "reindex.start",
        doc_file_id=doc_file.id,
        company=doc_file.company_name,
        year=doc_file.report_year,
        doc_type=doc_file.doc_type,
        path=file_url,
    )

    if dry_run:
        return {"dry_run": True, "file": file_url}

    # Read file from disk
    with open(file_url, "rb") as fh:
        content = fh.read()

    # Parse with Docling
    parse_result = parse_pdf(content)
    if not parse_result.ok or not parse_result.document:
        return {"error": f"parse failed: {parse_result.error}"}

    doc = parse_result.document

    # Delete old rag_documents for this file
    await session.execute(
        delete(RagDocumentModel).where(
            RagDocumentModel.document_file_id == doc_file.id
        )
    )
    await session.flush()

    doc_class = get_doc_class(doc_file.doc_type)
    signal_dimension = get_signal_dimension(doc_class)

    # Re-index with new chunks
    if doc_file.doc_type in PARENT_CHILD_DOC_TYPES:
        full_text = " ".join(doc.chunks)
        parent_chunks = chunk_parent_child(full_text)
        chunks_added = await index_document_chunks_parent_child(
            organization_id=doc_file.organization_id,
            document_file_id=doc_file.id,
            supplier_id=doc_file.supplier_id,
            doc_type=doc_file.doc_type,
            company_name=doc_file.company_name,
            report_year=doc_file.report_year,
            language=doc.language or doc_file.language or "de",
            parent_chunks=parent_chunks,
            session=session,
            doc_class=doc_class,
            signal_dimension=signal_dimension,
        )
    else:
        chunks_added = await index_document_chunks(
            organization_id=doc_file.organization_id,
            document_file_id=doc_file.id,
            supplier_id=doc_file.supplier_id,
            doc_type=doc_file.doc_type,
            company_name=doc_file.company_name,
            report_year=doc_file.report_year,
            language=doc.language or doc_file.language or "de",
            chunks=doc.chunks,
            session=session,
            doc_class=doc_class,
            signal_dimension=signal_dimension,
        )

    # Update document_files metadata
    from datetime import UTC, datetime
    doc_file.chunks_count = chunks_added
    doc_file.language = doc.language or doc_file.language
    doc_file.pages = doc.pages or doc_file.pages
    if doc.title and not doc_file.title:
        doc_file.title = doc.title
    doc_file.status = "done"
    doc_file.updated_at = datetime.now(UTC)
    await session.flush()

    logger.info(
        "reindex.done",
        doc_file_id=doc_file.id,
        chunks=chunks_added,
        pages=doc.pages,
    )
    return {"chunks_added": chunks_added, "pages": doc.pages}


async def main(dry_run: bool, single_id: str | None):
    async with AsyncSessionFactory() as session:
        if single_id:
            stmt = select(DocumentFileModel).where(DocumentFileModel.id == single_id)
        else:
            stmt = select(DocumentFileModel).order_by(DocumentFileModel.created_at)

        doc_files = (await session.execute(stmt)).scalars().all()

        print(f"\n{'DRY RUN — ' if dry_run else ''}Re-indexing {len(doc_files)} document(s) with Docling\n")

        total_chunks = 0
        skipped = 0
        errors = 0

        for df in doc_files:
            result = await reindex_document(df, session, dry_run)

            if result.get("skipped"):
                print(f"  SKIP  {df.company_name or '?':30} {df.doc_type:25} → {result['reason']}")
                skipped += 1
            elif result.get("error"):
                print(f"  ERROR {df.company_name or '?':30} {df.doc_type:25} → {result['error']}")
                errors += 1
            elif result.get("dry_run"):
                print(f"  DRY   {df.company_name or '?':30} {df.doc_type:25} → {result['file']}")
            else:
                chunks = result.get("chunks_added", 0)
                total_chunks += chunks
                print(f"  OK    {df.company_name or '?':30} {df.doc_type:25} → {chunks} chunks")

        if not dry_run:
            await session.commit()

        print(f"\nDone. Chunks indexed: {total_chunks} | Skipped: {skipped} | Errors: {errors}")
        if skipped > 0:
            print("\nNote: Skipped files were uploaded before file-storage was enabled.")
            print("      Re-upload them via the Documents page to index with Docling.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    parser.add_argument("--doc-file-id", help="Re-index only one specific document_file ID")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, single_id=args.doc_file_id))
