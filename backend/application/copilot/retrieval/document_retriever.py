"""Document Retriever — semantic search over rag_documents with metadata filters.

Allows the Copilot to restrict its knowledge base to specific companies,
years, or document classes (financial, esg, regulatory, statement, signal).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from application.rag.embedder import embed_query
from infrastructure.persistence.models.rag_documents import RagDocumentModel

from .base import RetrievalResult

_TOP_K = 10
_MIN_SIM = 0.25
_MAX_CHUNK_CHARS = 1800


async def retrieve_document_context(
    question: str,
    org_id: str,
    session: AsyncSession,
    *,
    company_name: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    doc_class: str | None = None,
    top_k: int = _TOP_K,
) -> RetrievalResult:
    """Semantic search over rag_documents with optional metadata filters."""
    query_vec = embed_query(question)
    retrieved_at = datetime.now(UTC).isoformat()

    # Only search uploaded document chunks, not news articles / intelligence events
    # excluded_from_index and copilot_hidden chunks/docs are skipped
    filters = [
        "r.organization_id = :org_id",
        "r.embedding IS NOT NULL",
        "r.document_file_id IS NOT NULL",
        "r.excluded_from_index = false",
        "COALESCE(df.copilot_hidden, false) = false",
    ]
    params: dict = {"org_id": org_id, "top_k": top_k, "min_sim": _MIN_SIM,
                    "query_vec": str(query_vec)}

    if company_name:
        filters.append("LOWER(company_name) = LOWER(:company_name)")
        params["company_name"] = company_name

    if year_from is not None:
        filters.append("report_year >= :year_from")
        params["year_from"] = year_from

    if year_to is not None:
        filters.append("report_year <= :year_to")
        params["year_to"] = year_to

    if doc_class:
        filters.append("doc_class = :doc_class")
        params["doc_class"] = doc_class

    # Fix column refs after adding JOIN alias
    where_clause = " AND ".join(filters).replace(
        "LOWER(company_name)", "LOWER(r.company_name)"
    ).replace("report_year", "r.report_year").replace("doc_class", "r.doc_class")

    sql = text(f"""
        SELECT
            r.id, r.supplier_id, r.doc_type, r.doc_class, r.source_id,
            r.company_name, r.report_year, r.content, r.signal_type, r.severity,
            1 - (r.embedding <=> CAST(:query_vec AS vector)) AS similarity
        FROM rag_documents r
        LEFT JOIN document_files df ON df.id = r.document_file_id
        WHERE {where_clause}
            AND 1 - (r.embedding <=> CAST(:query_vec AS vector)) >= :min_sim
        ORDER BY r.embedding <=> CAST(:query_vec AS vector)
        LIMIT :top_k
    """)

    result = await session.execute(sql, params)
    rows = result.mappings().all()

    data: list[dict] = []
    source_ids: list[str] = []
    freshness_metadata: list[dict] = []

    for r in rows:
        data.append({
            "id": r["id"],
            "company_name": r["company_name"],
            "report_year": r["report_year"],
            "doc_type": r["doc_type"],
            "doc_class": r["doc_class"],
            "source_id": r["source_id"],
            "content": r["content"][:_MAX_CHUNK_CHARS],
            "signal_type": r["signal_type"],
            "severity": r["severity"],
            "similarity": round(float(r["similarity"]), 4),
        })
        source_ids.append(r["id"])
        freshness_metadata.append({
            "object_id": r["id"],
            "object_type": "RagDocument",
            "updated_at": None,
            "retrieved_at": retrieved_at,
        })

    filter_parts = []
    if company_name:
        filter_parts.append(f"company={company_name}")
    if year_from or year_to:
        filter_parts.append(f"year={year_from or ''}–{year_to or ''}")
    if doc_class:
        filter_parts.append(f"class={doc_class}")
    filter_str = ", ".join(filter_parts) if filter_parts else "no filters"

    provenance = (
        f"Document Knowledge Base: {len(data)} chunk(s) [{filter_str}]"
    )

    # Format as readable text instead of dense JSON so the LLM can extract facts
    text_sections = []
    for d in data:
        header = f"[Document:{d['id']}] {d['company_name'] or ''} {d['report_year'] or ''} ({d['doc_type']})"
        text_sections.append(f"{header}\n{d['content']}")
    context_text = "\n\n".join(text_sections)

    return RetrievalResult(
        retriever="document_retriever",
        provenance=provenance,
        data=data,
        source_ids=source_ids,
        citation_type="Document",
        freshness_metadata=freshness_metadata,
        context_text=context_text,
    )


async def get_rag_filter_options(
    org_id: str,
    session: AsyncSession,
) -> dict:
    """Return distinct company names, doc classes, and years available for this org."""
    from sqlalchemy import distinct, func

    companies_stmt = (
        select(distinct(RagDocumentModel.company_name))
        .where(
            RagDocumentModel.organization_id == org_id,
            RagDocumentModel.company_name.isnot(None),
            RagDocumentModel.document_file_id.isnot(None),
        )
        .order_by(RagDocumentModel.company_name)
    )
    companies = [r[0] for r in (await session.execute(companies_stmt)).all() if r[0]]

    classes_stmt = (
        select(distinct(RagDocumentModel.doc_class))
        .where(
            RagDocumentModel.organization_id == org_id,
            RagDocumentModel.doc_class.isnot(None),
            RagDocumentModel.document_file_id.isnot(None),
        )
        .order_by(RagDocumentModel.doc_class)
    )
    doc_classes = [r[0] for r in (await session.execute(classes_stmt)).all() if r[0]]

    years_stmt = (
        select(distinct(RagDocumentModel.report_year))
        .where(
            RagDocumentModel.organization_id == org_id,
            RagDocumentModel.report_year.isnot(None),
            RagDocumentModel.document_file_id.isnot(None),
        )
        .order_by(RagDocumentModel.report_year)
    )
    years = [r[0] for r in (await session.execute(years_stmt)).all() if r[0]]

    return {
        "companies": companies,
        "doc_classes": doc_classes,
        "years": years,
    }
