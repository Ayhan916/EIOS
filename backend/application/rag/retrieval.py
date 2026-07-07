"""RAG Retrieval Service — semantic search over the knowledge base.

Uses cosine similarity (pgvector <=> operator) with optional metadata filters.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.rag_documents import RagDocumentModel

from .embedder import embed_query


async def retrieve(
    query: str,
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
    doc_types: list[str] | None = None,
    top_k: int = 8,
    min_similarity: float = 0.3,
) -> list[dict]:
    """Retrieve the most semantically similar documents for a query.

    Returns a list of dicts with content + metadata, ordered by similarity.
    """
    query_vec = embed_query(query)

    # Build pgvector cosine-distance query
    # <=> = cosine distance (0 = identical, 2 = opposite)
    # similarity = 1 - distance
    filters = ["organization_id = :org_id"]
    params: dict = {"org_id": organization_id, "top_k": top_k}

    if supplier_id:
        filters.append("supplier_id = :supplier_id")
        params["supplier_id"] = supplier_id

    if doc_types:
        placeholders = ", ".join(f":dt{i}" for i in range(len(doc_types)))
        filters.append(f"doc_type IN ({placeholders})")
        for i, dt in enumerate(doc_types):
            params[f"dt{i}"] = dt

    where_clause = " AND ".join(filters)

    sql = text(f"""
        SELECT
            id,
            supplier_id,
            doc_type,
            source_id,
            content,
            signal_type,
            severity,
            source_name,
            published_at,
            1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
        FROM rag_documents
        WHERE {where_clause}
            AND embedding IS NOT NULL
            AND 1 - (embedding <=> CAST(:query_vec AS vector)) >= :min_sim
        ORDER BY embedding <=> CAST(:query_vec AS vector)
        LIMIT :top_k
    """)

    params["query_vec"] = str(query_vec)
    params["min_sim"] = min_similarity

    result = await session.execute(sql, params)
    rows = result.mappings().all()

    return [
        {
            "id": r["id"],
            "supplier_id": r["supplier_id"],
            "doc_type": r["doc_type"],
            "source_id": r["source_id"],
            "content": r["content"],
            "signal_type": r["signal_type"],
            "severity": r["severity"],
            "source_name": r["source_name"],
            "published_at": r["published_at"].isoformat() if r["published_at"] else None,
            "similarity": round(float(r["similarity"]), 4),
        }
        for r in rows
    ]
