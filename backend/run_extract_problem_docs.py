"""Re-Extraktion der 6 Dokumente mit 0 Metriken — mit erweitertem Chunk-Selektor."""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))

os.environ["LLM_PROVIDER"] = "groq"
os.environ["LLM_MODEL"] = "llama-3.1-8b-instant"

from sqlalchemy import select, delete
from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.models.document_pipeline import DocumentFileModel
from infrastructure.persistence.models.rag_documents import RagDocumentModel
from infrastructure.persistence.models.company_intelligence import CompanyMetricModel, CompanySignalModel
from infrastructure.llm.deps import init_llm_provider
from application.rag.metric_extractor import extract_and_store_intelligence
from application.rag.document_classifier import get_doc_class

init_llm_provider()

# Doc-IDs der 6 Problemdokumente (alle 0 Metriken nach 3 Läufen)
PROBLEM_DOCS = {
    "2018 Annual Report (financial)":     "5cc2b02c-9514-4a4a-aa54-0a510c51a56d",
    "2022 Annual Report (financial)":     "81889f4d-236b-4c79-a3c3-ef3151e5a2f9",
    "2023 Annual Report (financial)":     "5e448295-8428-438b-bf4a-1aa05eff3f62",
    "2025 Annual Report (financial)":     "e8e51cd9-9383-4e46-a158-56a95cbb1dc9",
    "2016 Sustainability (esg)":          "cc3a559d-9188-4439-8288-837ba24504a2",
    "2017 Sustainability (esg)":          "1f7f411a-5b58-46ce-b277-3c79923d0b1d",
}
TARGET_ORG = "684ed2e6-5f76-4b32-81e8-e0e0def2cc3a"  # EIOS org

async def main():
    for label, doc_id in PROBLEM_DOCS.items():
        print(f"\n{'='*60}")
        print(f"📄  {label}")

        async with AsyncSessionFactory() as db:
            doc = (await db.execute(
                select(DocumentFileModel).where(DocumentFileModel.id == doc_id)
            )).scalar_one_or_none()

            if not doc:
                print("  ❌ Dokument nicht gefunden"); continue

            chunks = (await db.execute(
                select(RagDocumentModel.content)
                .where(RagDocumentModel.document_file_id == doc_id)
                .order_by(RagDocumentModel.created_at.asc())
                .limit(100)
            )).scalars().all()

        print(f"  Chunks: {len(chunks)}, Company: {doc.company_name}, Year: {doc.report_year}")

        try:
            async with AsyncSessionFactory() as session:
                async with session.begin():
                    intel = await extract_and_store_intelligence(
                        organization_id=str(doc.organization_id),
                        doc_file_id=doc_id,
                        doc_class=get_doc_class(doc.doc_type),
                        company_name=doc.company_name,
                        supplier_id=str(doc.supplier_id) if doc.supplier_id else None,
                        report_year=doc.report_year,
                        chunks=list(chunks),
                        session=session,
                    )
            print(f"  ✅  {intel.get('metrics', 0)} Metriken, {intel.get('signals', 0)} Signale")
        except Exception as e:
            print(f"  ❌  {str(e)[:200]}")

        if list(PROBLEM_DOCS.keys()).index(label) < len(PROBLEM_DOCS) - 1:
            await asyncio.sleep(3.0)

    print(f"\n{'='*60}")
    print("✅ Fertig")

if __name__ == "__main__":
    asyncio.run(main())
