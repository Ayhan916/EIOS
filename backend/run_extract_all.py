"""Retroaktive Extraktion company_metrics + company_signals für alle 'done' Dokumente.

ADR-007: Claude Haiku (claude-haiku-4-5-20251001) statt Groq 8B für Produktion.
ADR-009: annual_report + financial_statement → Parent-Chunks (1500 Wörter, volle Tabellen).
         Alle anderen Typen → Flat-Chunks (800 Wörter, bisheriges Verhalten).
"""
import asyncio
import sys
import os

# Backend-Root im Python-Path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.models.document_pipeline import DocumentFileModel
from infrastructure.persistence.models.rag_documents import RagDocumentModel
from infrastructure.persistence.models.organization import OrganizationModel
from infrastructure.llm.deps import init_extraction_llm_provider
from application.rag.metric_extractor import extract_and_store_intelligence
from application.rag.document_classifier import get_doc_class
from application.rag.parent_child_chunker import PARENT_CHILD_DOC_TYPES
from shared.config import settings

provider = init_extraction_llm_provider()
print(f"LLM (extraction): {provider.provider_name()} / {provider.model_name()} (ADR-007)")

# Ziel-Org: EIOS (hat die 24 BMW-Dokumente)
TARGET_ORG_NAME = "EIOS"


async def main():
    # Organisation ermitteln
    async with AsyncSessionFactory() as db:
        org = (await db.execute(
            select(OrganizationModel).where(OrganizationModel.name == TARGET_ORG_NAME).limit(1)
        )).scalar_one_or_none()
        if not org:
            # Fallback: erste Org mit Dokumenten
            org = (await db.execute(select(OrganizationModel).limit(1))).scalar_one_or_none()
        if not org:
            print("❌  Keine Organisation gefunden.")
            return
        org_id = str(org.id)
        print(f"✅  Organisation: {org.name} ({org_id[:8]}…)")

    # Alle fertigen Dokumente laden
    async with AsyncSessionFactory() as db:
        from infrastructure.persistence.models.company_intelligence import CompanyMetricModel
        all_docs = (await db.execute(
            select(DocumentFileModel).where(
                DocumentFileModel.organization_id == org_id,
                DocumentFileModel.status == "done",
            ).order_by(DocumentFileModel.report_year.asc())
        )).scalars().all()

        # Ermittle welche Dokumente bereits Metriken haben
        from sqlalchemy import func
        rows_with_metrics = (await db.execute(
            select(CompanyMetricModel.source_doc_id, func.count().label("cnt"))
            .group_by(CompanyMetricModel.source_doc_id)
        )).all()
        has_metrics = {str(r[0]): r[1] for r in rows_with_metrics}

    # Alle Dokumente re-extrahieren — erweiterter Pool (alle Chunks, nicht nur erste 60)
    doc_files = all_docs
    docs_with = sum(1 for d in all_docs if str(d.id) in has_metrics)
    print(f"📄  {len(all_docs)} Dokumente gesamt ({docs_with} bereits mit Metriken, alle werden re-extrahiert).\n")

    results = []
    for i, doc in enumerate(doc_files):
        label = f"[{i+1}/{len(doc_files)}] {doc.company_name or '?'} {doc.report_year or ''} ({doc.doc_type})"

        if not doc.company_name:
            print(f"⏭️  {label} — übersprungen (kein company_name)")
            results.append({"id": str(doc.id), "skipped": True, "reason": "no_company_name"})
            continue

        # ADR-009: Parent-Chunks für tabellenreiche Typen, Flat für alle anderen
        chunk_level = "parent" if doc.doc_type in PARENT_CHILD_DOC_TYPES else "flat"

        # Chunks laden
        async with AsyncSessionFactory() as db:
            chunk_rows = (await db.execute(
                select(RagDocumentModel.content)
                .where(
                    RagDocumentModel.document_file_id == doc.id,
                    RagDocumentModel.chunk_level == chunk_level,
                )
                .order_by(RagDocumentModel.source_id.asc())
            )).scalars().all()

            # Fallback: wenn noch keine Parent-Chunks vorhanden → Flat nehmen
            if not chunk_rows and chunk_level == "parent":
                chunk_rows = (await db.execute(
                    select(RagDocumentModel.content)
                    .where(
                        RagDocumentModel.document_file_id == doc.id,
                        RagDocumentModel.chunk_level == "flat",
                    )
                    .order_by(RagDocumentModel.source_id.asc())
                )).scalars().all()
                chunk_level = "flat (fallback)"

        if not chunk_rows:
            print(f"⏭️  {label} — übersprungen (keine Chunks)")
            results.append({"id": str(doc.id), "skipped": True, "reason": "no_chunks"})
            continue

        print(f"🔍  {label} — extrahiere ({len(chunk_rows)} {chunk_level}-Chunks)…", end=" ", flush=True)
        try:
            async with AsyncSessionFactory() as session:
                async with session.begin():
                    intel = await extract_and_store_intelligence(
                        organization_id=org_id,
                        doc_file_id=str(doc.id),
                        doc_class=get_doc_class(doc.doc_type),
                        company_name=doc.company_name,
                        supplier_id=str(doc.supplier_id) if doc.supplier_id else None,
                        report_year=doc.report_year,
                        chunks=list(chunk_rows),
                        session=session,
                    )
            m = intel.get("metrics", 0)
            s = intel.get("signals", 0)
            print(f"✅  {m} Metriken, {s} Signale")
            results.append({"id": str(doc.id), "year": doc.report_year, "metrics": m, "signals": s})
        except Exception as exc:
            print(f"❌  Fehler: {str(exc)[:120]}")
            results.append({"id": str(doc.id), "error": str(exc)[:200]})

        # Groq-Rate-Limit schonen
        if i < len(doc_files) - 1:
            await asyncio.sleep(2.5)

    # Zusammenfassung
    total_m = sum(r.get("metrics", 0) for r in results)
    total_s = sum(r.get("signals", 0) for r in results)
    skipped = sum(1 for r in results if r.get("skipped"))
    errors  = sum(1 for r in results if r.get("error"))

    print(f"\n{'='*60}")
    print(f"✅  Fertig: {len(doc_files)} Dokumente")
    print(f"   Übersprungen: {skipped}")
    print(f"   Fehler: {errors}")
    print(f"   Metriken gespeichert: {total_m}")
    print(f"   Signale gespeichert:  {total_s}")


if __name__ == "__main__":
    asyncio.run(main())
