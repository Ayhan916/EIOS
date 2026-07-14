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

    hits = [
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

    # ADR-009: for child chunks, load and attach parent context
    return await _attach_parent_context(hits, session)


async def _attach_parent_context(hits: list[dict], session: AsyncSession) -> list[dict]:
    """For child-level chunks, replace content with parent context + child excerpt.

    Child chunks produced by parent-child chunking carry a parent_chunk_id.
    Sending the full parent to the LLM ensures table values and labels
    are never split across chunk boundaries.
    """
    child_ids = [h["id"] for h in hits]
    if not child_ids:
        return hits

    # Fetch chunk_level and parent_chunk_id for all hits in one query
    meta_sql = text("""
        SELECT id, chunk_level, parent_chunk_id
        FROM rag_documents
        WHERE id = ANY(:ids)
    """)
    meta_rows = {
        r["id"]: r
        for r in (await session.execute(meta_sql, {"ids": child_ids})).mappings().all()
    }

    parent_ids = [
        r["parent_chunk_id"]
        for r in meta_rows.values()
        if r.get("chunk_level") == "child" and r.get("parent_chunk_id")
    ]

    if not parent_ids:
        return hits

    # Load parent content in one query
    parent_sql = text("""
        SELECT id, content FROM rag_documents WHERE id = ANY(:ids)
    """)
    parent_map = {
        r["id"]: r["content"]
        for r in (await session.execute(parent_sql, {"ids": parent_ids})).mappings().all()
    }

    enriched = []
    for hit in hits:
        meta = meta_rows.get(hit["id"], {})
        if meta.get("chunk_level") == "child" and meta.get("parent_chunk_id"):
            parent_content = parent_map.get(meta["parent_chunk_id"])
            if parent_content:
                hit = {
                    **hit,
                    "parent_content": parent_content,
                    # Replace content sent to LLM with the full parent window
                    "content": parent_content,
                    "child_excerpt": hit["content"],
                }
        enriched.append(hit)

    return enriched
