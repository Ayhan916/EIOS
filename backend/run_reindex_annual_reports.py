"""Re-Indexierung von Annual Reports mit Parent-Child Chunking (ADR-009 / E1-F3).

Was dieses Skript tut:
  1. Lädt alle 'annual_report' und 'financial_statement' Dokumente aus document_files
  2. Rekonstruiert den Volltext aus vorhandenen Flat-Chunks (rag_documents)
  3. Erstellt Parent-Child-Hierarchie via chunk_parent_child()
  4. Speichert Parent + Child Chunks in rag_documents (idempotent — skip wenn vorhanden)
  5. Gibt Statistik aus

Was es NICHT tut:
  - Löscht vorhandene Flat-Chunks (bleiben parallel, können danach manuell bereinigt werden)
  - Ruft Metriken-Extrakteur auf (separater Schritt: run_extract_all.py danach)

Voraussetzung: Migration 113 muss eingespielt sein (chunk_level + parent_chunk_id).

Ausführung:
  cd backend && python run_reindex_annual_reports.py [--year 2024] [--dry-run]
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select, text

from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.models.document_pipeline import DocumentFileModel
from infrastructure.persistence.models.rag_documents import RagDocumentModel
from application.rag.parent_child_chunker import chunk_parent_child, PARENT_CHILD_DOC_TYPES
from application.rag.document_indexer import index_document_chunks_parent_child
from application.rag.document_classifier import get_doc_class

DRY_RUN = "--dry-run" in sys.argv
YEAR_FILTER = None
for arg in sys.argv[1:]:
    if arg.startswith("--year="):
        YEAR_FILTER = int(arg.split("=")[1])
    elif arg == "--year" and sys.argv.index(arg) + 1 < len(sys.argv):
        idx = sys.argv.index(arg)
        YEAR_FILTER = int(sys.argv[idx + 1])


async def main() -> None:
    print("=" * 70)
    print("E1-F3 Re-Indexierung — Parent-Child Chunking (ADR-009)")
    print(f"Modus: {'DRY-RUN (kein Schreiben)' if DRY_RUN else 'LIVE'}")
    if YEAR_FILTER:
        print(f"Filter: Nur Jahr {YEAR_FILTER}")
    print("=" * 70)

    async with AsyncSessionFactory() as session:
        # Load target documents
        stmt = select(DocumentFileModel).where(
            DocumentFileModel.doc_type.in_(PARENT_CHILD_DOC_TYPES)
        )
        if YEAR_FILTER:
            stmt = stmt.where(DocumentFileModel.report_year == YEAR_FILTER)
        stmt = stmt.order_by(DocumentFileModel.report_year.desc())

        docs = (await session.execute(stmt)).scalars().all()
        print(f"\n{len(docs)} Dokumente gefunden\n")

        total_parents = 0
        total_children = 0

        for doc in docs:
            print(f"── {doc.doc_type} {doc.report_year or '?'} │ {doc.id[:8]}…")

            # Load existing flat chunks ordered by source_id
            flat_chunks = (
                await session.execute(
                    select(RagDocumentModel)
                    .where(
                        RagDocumentModel.document_file_id == doc.id,
                        RagDocumentModel.chunk_level == "flat",
                    )
                    .order_by(RagDocumentModel.source_id)
                )
            ).scalars().all()

            if not flat_chunks:
                print(f"   ⚠️  Keine Flat-Chunks — übersprungen")
                continue

            print(f"   Flat-Chunks: {len(flat_chunks)}")

            # Reconstruct full text from flat chunks
            full_text = " ".join(c.content for c in flat_chunks)
            word_count = len(full_text.split())
            print(f"   Wörter gesamt: {word_count:,}")

            # Apply parent-child chunking
            parents = chunk_parent_child(full_text)
            child_count = sum(len(p.children) for p in parents)
            print(f"   Eltern: {len(parents)} │ Kinder: {child_count}")

            if DRY_RUN:
                print(f"   [DRY-RUN] Keine Änderungen geschrieben\n")
                continue

            # Check if parent-child already exists for this doc
            existing_pc = (
                await session.execute(
                    select(RagDocumentModel.id)
                    .where(
                        RagDocumentModel.document_file_id == doc.id,
                        RagDocumentModel.chunk_level == "parent",
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()

            if existing_pc:
                print(f"   ✅ Bereits re-indexiert — übersprungen\n")
                continue

            # Use metadata from first flat chunk
            first = flat_chunks[0]
            doc_class = get_doc_class(doc.doc_type)

            stored = await index_document_chunks_parent_child(
                organization_id=first.organization_id,
                document_file_id=doc.id,
                supplier_id=first.supplier_id,
                doc_type=doc.doc_type,
                company_name=doc.company_name,
                report_year=doc.report_year,
                language=first.language,
                parent_chunks=parents,
                session=session,
                doc_class=doc_class,
                signal_dimension=first.signal_dimension,
            )

            await session.commit()
            print(f"   ✅ {len(parents)} Eltern + {stored} Kinder gespeichert\n")

            total_parents += len(parents)
            total_children += stored

        print("=" * 70)
        if not DRY_RUN:
            print(f"Gesamt: {total_parents} Eltern-Chunks, {total_children} Kinder-Chunks")
            print("")
            print("Nächster Schritt: python run_extract_all.py")
            print("(extrahiert Metriken aus den neuen Parent-Chunks)")
        else:
            print("DRY-RUN abgeschlossen — keine Änderungen an der DB")


asyncio.run(main())
