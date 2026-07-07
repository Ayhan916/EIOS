"""Phase 4 — semantische Suche in historical_knowledge."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .embedder import embed_query


async def retrieve_history(
    query: str,
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
    csddd_right: str | None = None,
    top_k: int = 6,
    min_similarity: float = 0.25,
) -> list[dict]:
    """Semantische Suche in historical_knowledge.

    Gibt Liste von Lerneinträgen zurück, sortiert nach Relevanz.
    """
    query_vec = embed_query(query)
    vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"

    filters = ["organization_id = :org"]
    params: dict = {"org": organization_id, "top_k": top_k, "min_sim": min_similarity}

    if supplier_id:
        filters.append("(supplier_id = :sid OR supplier_id IS NULL)")
        params["sid"] = supplier_id
    if csddd_right:
        filters.append("csddd_right = :right")
        params["right"] = csddd_right

    where = " AND ".join(filters)

    sql = text(f"""
        SELECT
            id,
            supplier_id,
            event_description,
            event_type,
            event_severity,
            countermeasure_description,
            countermeasure_type,
            outcome_description,
            outcome_category,
            health_delta,
            csddd_right,
            twin_dimension,
            content_text,
            source_event_id,
            source_finding_id,
            source_cap_id,
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
            "id":                        r[0],
            "supplier_id":               r[1],
            "event_description":         r[2],
            "event_type":                r[3],
            "event_severity":            r[4],
            "countermeasure_description": r[5],
            "countermeasure_type":       r[6],
            "outcome_description":       r[7],
            "outcome_category":          r[8],
            "health_delta":              r[9],
            "csddd_right":               r[10],
            "twin_dimension":            r[11],
            "content_text":              r[12],
            "source_event_id":           r[13],
            "source_finding_id":         r[14],
            "source_cap_id":             r[15],
            "reference_date":            r[16].isoformat() if r[16] else None,
            "similarity":                float(r[17]),
        }
        for r in rows
    ]
