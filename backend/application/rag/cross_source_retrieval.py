"""Cross-Source Intelligence Retrieval.

Merges results from all three knowledge sources in a single query pass:
  1. rag_documents  — news articles, intelligence events, document chunks (ESG/annual/audit reports)
  2. historical_knowledge — closed CAPs, resolved findings, past supply-chain events

Each returned chunk is annotated with `source_type`:
  "news"         — doc_type == "news_article"
  "intelligence" — doc_type == "intelligence_event"
  "document"     — doc_type in ESG/annual/audit/csrd/csddd/sector report types
  "historical"   — from historical_knowledge table

Results are merged and re-ranked by cosine similarity, capped at top_k.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .embedder import embed_query

# Doc types that come from the Document Intelligence pipeline
_DOCUMENT_DOC_TYPES = {
    "annual_report",
    "sustainability_report",
    "audit_report",
    "csrd_report",
    "csddd_disclosure",
    "sector_risk",
}


def _classify_source_type(doc_type: str) -> str:
    if doc_type == "news_article":
        return "news"
    if doc_type == "intelligence_event":
        return "intelligence"
    if doc_type in _DOCUMENT_DOC_TYPES:
        return "document"
    return "document"  # safe default for unknown future doc_types


async def _retrieve_rag_documents(
    vec_str: str,
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None,
    top_k: int,
    min_similarity: float,
) -> list[dict]:
    filters = ["organization_id = :org_id"]
    params: dict = {"org_id": organization_id, "top_k": top_k, "min_sim": min_similarity}

    if supplier_id:
        filters.append("supplier_id = :supplier_id")
        params["supplier_id"] = supplier_id

    where = " AND ".join(filters)

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
            1 - (embedding <=> CAST('{vec_str}' AS vector)) AS similarity
        FROM rag_documents
        WHERE {where}
          AND embedding IS NOT NULL
          AND 1 - (embedding <=> CAST('{vec_str}' AS vector)) >= :min_sim
        ORDER BY embedding <=> CAST('{vec_str}' AS vector)
        LIMIT :top_k
    """)

    result = await session.execute(sql, params)
    rows = result.fetchall()

    return [
        {
            "id": r[0],
            "supplier_id": r[1],
            "doc_type": r[2],
            "source_type": _classify_source_type(r[2]),
            "source_id": r[3],
            "content": r[4],
            "signal_type": r[5],
            "severity": r[6],
            "source_name": r[7],
            "published_at": r[8].isoformat() if r[8] else None,
            "similarity": round(float(r[9]), 4),
            # historical fields absent
            "event_type": None,
            "outcome_category": None,
            "csddd_right": None,
        }
        for r in rows
    ]


async def _retrieve_historical(
    vec_str: str,
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None,
    top_k: int,
    min_similarity: float,
) -> list[dict]:
    filters = ["organization_id = :org"]
    params: dict = {"org": organization_id, "top_k": top_k, "min_sim": min_similarity}

    if supplier_id:
        # include both supplier-specific AND org-wide (supplier_id IS NULL)
        filters.append("(supplier_id = :sid OR supplier_id IS NULL)")
        params["sid"] = supplier_id

    where = " AND ".join(filters)

    sql = text(f"""
        SELECT
            id,
            supplier_id,
            event_description,
            event_type,
            event_severity,
            countermeasure_description,
            outcome_description,
            outcome_category,
            csddd_right,
            content_text,
            reference_date,
            1 - (embedding <=> CAST('{vec_str}' AS vector)) AS similarity
        FROM historical_knowledge
        WHERE {where}
          AND embedding IS NOT NULL
          AND 1 - (embedding <=> CAST('{vec_str}' AS vector)) >= :min_sim
        ORDER BY embedding <=> CAST('{vec_str}' AS vector)
        LIMIT :top_k
    """)

    result = await session.execute(sql, params)
    rows = result.fetchall()

    return [
        {
            "id": r[0],
            "supplier_id": r[1],
            "doc_type": "historical",
            "source_type": "historical",
            "source_id": None,
            "content": _format_historical_content(r),
            "signal_type": r[3],  # event_type as signal_type
            "severity": r[4],     # event_severity
            "source_name": "Historisches Wissen",
            "published_at": r[10].isoformat()[:10] if r[10] else None,
            "similarity": round(float(r[11]), 4),
            "event_type": r[3],
            "outcome_category": r[7],
            "csddd_right": r[8],
        }
        for r in rows
    ]


def _format_historical_content(row) -> str:
    parts = [row[2]]  # event_description
    if row[5]:
        parts.append(f"Gegenmaßnahme: {row[5]}")
    if row[6]:
        parts.append(f"Ergebnis: {row[6]}")
    if row[7]:
        parts.append(f"Kategorie: {row[7]}")
    return " | ".join(parts)


async def retrieve_cross_source(
    query: str,
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
    top_k: int = 8,
    min_similarity: float = 0.25,
    max_historical: int = 3,
) -> list[dict]:
    """Query all knowledge sources and return a merged, re-ranked result list.

    Caps historical results at `max_historical` to avoid them dominating the
    context when many document chunks are available.  Final list is sorted by
    similarity descending, capped at `top_k`.
    """
    query_vec = embed_query(query)
    vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"

    rag_k = top_k  # fetch full quota from each; dedup after merge
    hist_k = max(max_historical, top_k // 3)

    # Sequential execution — share the same async session safely
    rag_chunks = await _retrieve_rag_documents(
        vec_str, organization_id, session, supplier_id, rag_k, min_similarity
    )
    hist_chunks = await _retrieve_historical(
        vec_str, organization_id, session, supplier_id, hist_k, min_similarity
    )

    # Cap historical results and merge
    hist_chunks = hist_chunks[:max_historical]
    merged = rag_chunks + hist_chunks

    # Re-rank by similarity, take top_k
    merged.sort(key=lambda c: c["similarity"], reverse=True)
    return merged[:top_k]
