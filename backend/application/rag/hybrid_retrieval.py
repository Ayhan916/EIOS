"""Hybrid Retrieval: BM25 + pgvector + Reciprocal Rank Fusion (ADR-008).

Formula:
    score_rrf(d) = 1 / (k + rank_bm25(d)) + 1 / (k + rank_vector(d))     [k = 60]

BM25 leg   — PostgreSQL tsvector / ts_rank (GIN-indexed via `ts_content` column).
             Falls back to on-the-fly `to_tsvector` for rows without pre-computed
             ts_content (i.e. before migration 107 is applied).
Vector leg — pgvector cosine similarity (multilingual-e5-large, 1024d).
Fusion     — single SQL query with three CTEs, no Python-side sorting.

No LLM is involved (ADR-001). All inputs are deterministic given the same DB state.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .embedder import embed_query

# RRF constant from ADR-008 — increases this reduce the dominance of top-1 results
_DEFAULT_K: int = 60

# Number of candidates fetched per leg before RRF fusion.
# Higher values improve recall at the cost of more sorting work.
_DEFAULT_CANDIDATE_POOL: int = 100


async def hybrid_retrieve(
    query: str,
    organization_id: str,
    session: AsyncSession,
    *,
    supplier_id: str | None = None,
    doc_types: list[str] | None = None,
    top_k: int = 8,
    k: int = _DEFAULT_K,
    candidate_pool: int = _DEFAULT_CANDIDATE_POOL,
    language: str = "german",
) -> list[dict]:
    """Return the top-k documents fused from BM25 and vector legs via RRF.

    Each result carries `rrf_score` (fusion score) alongside the standard
    content and metadata fields returned by `retrieval.retrieve()`.

    Documents that match only one leg still appear in results — their score
    from the missing leg is treated as 0 (FULL OUTER JOIN / COALESCE pattern).

    Args:
        query:           Natural-language or keyword query string.
        organization_id: Tenant isolation — only documents for this org are searched.
        session:         Async SQLAlchemy session.
        supplier_id:     Optional filter — restrict to a single supplier.
        doc_types:       Optional filter — restrict to specific doc_type values.
        top_k:           Maximum results to return after fusion.
        k:               RRF constant (default 60 per ADR-008).
        candidate_pool:  Candidates fetched per leg before fusion.
        language:        PostgreSQL text-search configuration (e.g. 'german', 'english').
    """
    query_vec = embed_query(query)

    # Build shared WHERE fragment — applied to both BM25 and vector legs
    where_parts = ["d.organization_id = :org_id"]
    params: dict = {
        "org_id": organization_id,
        "query": query,
        "lang": language,
        "query_vec": str(query_vec),
        "k": k,
        "candidate_pool": candidate_pool,
        "top_k": top_k,
    }

    if supplier_id:
        where_parts.append("d.supplier_id = :supplier_id")
        params["supplier_id"] = supplier_id

    if doc_types:
        placeholders = ", ".join(f":dt{i}" for i in range(len(doc_types)))
        where_parts.append(f"d.doc_type IN ({placeholders})")
        for i, dt in enumerate(doc_types):
            params[f"dt{i}"] = dt

    where_clause = " AND ".join(where_parts)

    sql = text(f"""
        WITH
        -- ── BM25 leg ─────────────────────────────────────────────────────────
        -- Uses pre-computed ts_content (GIN-indexed) when available;
        -- falls back to on-the-fly tsvector for rows before migration 107.
        bm25_ranked AS (
            SELECT
                d.id,
                ROW_NUMBER() OVER (
                    ORDER BY ts_rank(
                        COALESCE(d.ts_content, to_tsvector(CAST(:lang AS regconfig), d.content)),
                        plainto_tsquery(CAST(:lang AS regconfig), :query)
                    ) DESC
                ) AS bm25_rank
            FROM rag_documents d
            WHERE {where_clause}
              AND COALESCE(d.ts_content, to_tsvector(CAST(:lang AS regconfig), d.content))
                  @@ plainto_tsquery(CAST(:lang AS regconfig), :query)
            LIMIT :candidate_pool
        ),
        -- ── Vector leg ───────────────────────────────────────────────────────
        vector_ranked AS (
            SELECT
                d.id,
                ROW_NUMBER() OVER (
                    ORDER BY d.embedding <=> CAST(:query_vec AS vector)
                ) AS vec_rank
            FROM rag_documents d
            WHERE {where_clause}
              AND d.embedding IS NOT NULL
            LIMIT :candidate_pool
        ),
        -- ── RRF fusion ───────────────────────────────────────────────────────
        -- Documents absent from one leg contribute 0 from that leg (COALESCE).
        rrf_fused AS (
            SELECT
                COALESCE(b.id, v.id) AS id,
                COALESCE(1.0 / (:k + b.bm25_rank), 0.0)
                    + COALESCE(1.0 / (:k + v.vec_rank), 0.0) AS rrf_score
            FROM bm25_ranked b
            FULL OUTER JOIN vector_ranked v ON b.id = v.id
        )
        SELECT
            d.id,
            d.supplier_id,
            d.doc_type,
            d.source_id,
            d.content,
            d.signal_type,
            d.severity,
            d.source_name,
            d.published_at,
            f.rrf_score
        FROM rrf_fused f
        JOIN rag_documents d ON d.id = f.id
        ORDER BY f.rrf_score DESC
        LIMIT :top_k
    """)

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
            "rrf_score": round(float(r["rrf_score"]), 6),
        }
        for r in rows
    ]
