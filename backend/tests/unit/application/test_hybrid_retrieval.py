"""Tests for application/rag/hybrid_retrieval.py — ADR-008.

Unit tests mock the DB session and the embed_query function to verify:
  - SQL contains RRF formula with correct k=60 constant
  - SQL contains all three CTEs (bm25_ranked, vector_ranked, rrf_fused)
  - Filters (supplier_id, doc_types) are injected into params
  - Results are correctly shaped (rrf_score, content, metadata fields)
  - Empty DB result returns empty list
  - default k=60 is used (ADR-008 mandate)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.rag.hybrid_retrieval import _DEFAULT_K, hybrid_retrieve

pytestmark = pytest.mark.unit

# ── helpers ───────────────────────────────────────────────────────────────────

_ORG = "org-test-123"
_QUERY = "CSDDD Sorgfaltspflicht"

_FAKE_EMBEDDING = [0.1] * 1024


def _make_session(rows: list[dict] | None = None) -> AsyncMock:
    session = AsyncMock()
    mapping_list = []
    if rows:
        for row in rows:
            m = MagicMock()
            m.__getitem__ = lambda self, k, _row=row: _row[k]
            mapping_list.append(m)
    result = MagicMock()
    result.mappings.return_value.all.return_value = mapping_list
    session.execute = AsyncMock(return_value=result)
    return session


def _fake_row(
    id: str = "doc-1",
    rrf_score: float = 0.031,
    published_at: datetime | None = None,
) -> dict:
    return {
        "id": id,
        "supplier_id": "sup-1",
        "doc_type": "esg_report",
        "source_id": "src-1",
        "content": "Sorgfaltspflicht entlang der Lieferkette",
        "signal_type": None,
        "severity": None,
        "source_name": "BMW AG",
        "published_at": published_at,
        "rrf_score": rrf_score,
    }


# ── SQL structure ─────────────────────────────────────────────────────────────


class TestSQLStructure:
    @pytest.mark.asyncio
    async def test_sql_contains_bm25_cte(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session)

        call_args = session.execute.call_args
        sql_str = str(call_args[0][0])
        assert "bm25_ranked" in sql_str

    @pytest.mark.asyncio
    async def test_sql_contains_vector_cte(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session)

        sql_str = str(session.execute.call_args[0][0])
        assert "vector_ranked" in sql_str

    @pytest.mark.asyncio
    async def test_sql_contains_rrf_fusion_cte(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session)

        sql_str = str(session.execute.call_args[0][0])
        assert "rrf_fused" in sql_str

    @pytest.mark.asyncio
    async def test_sql_contains_full_outer_join(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session)

        sql_str = str(session.execute.call_args[0][0])
        assert "FULL OUTER JOIN" in sql_str

    @pytest.mark.asyncio
    async def test_sql_contains_rrf_formula(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session)

        sql_str = str(session.execute.call_args[0][0])
        # RRF formula: 1.0 / (:k + rank)
        assert "1.0 / (:k +" in sql_str


# ── default parameters (ADR-008) ──────────────────────────────────────────────


class TestDefaultParameters:
    def test_default_k_is_60(self) -> None:
        assert _DEFAULT_K == 60

    @pytest.mark.asyncio
    async def test_k_param_defaults_to_60(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session)

        params = session.execute.call_args[0][1]
        assert params["k"] == 60

    @pytest.mark.asyncio
    async def test_custom_k_overrides_default(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session, k=30)

        params = session.execute.call_args[0][1]
        assert params["k"] == 30


# ── filters ───────────────────────────────────────────────────────────────────


class TestFilters:
    @pytest.mark.asyncio
    async def test_supplier_id_added_to_params(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session, supplier_id="sup-99")

        params = session.execute.call_args[0][1]
        assert params["supplier_id"] == "sup-99"

    @pytest.mark.asyncio
    async def test_supplier_id_filter_in_sql(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session, supplier_id="sup-99")

        sql_str = str(session.execute.call_args[0][0])
        assert "supplier_id" in sql_str

    @pytest.mark.asyncio
    async def test_doc_types_filter_in_params(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session, doc_types=["esg_report", "annual_report"])

        params = session.execute.call_args[0][1]
        assert params["dt0"] == "esg_report"
        assert params["dt1"] == "annual_report"

    @pytest.mark.asyncio
    async def test_org_id_always_in_params(self) -> None:
        session = _make_session()
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session)

        params = session.execute.call_args[0][1]
        assert params["org_id"] == _ORG


# ── result shape ──────────────────────────────────────────────────────────────


class TestResultShape:
    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_list(self) -> None:
        session = _make_session(rows=[])
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            results = await hybrid_retrieve(_QUERY, _ORG, session)

        assert results == []

    @pytest.mark.asyncio
    async def test_result_has_rrf_score(self) -> None:
        session = _make_session(rows=[_fake_row(rrf_score=0.031)])
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            results = await hybrid_retrieve(_QUERY, _ORG, session)

        assert len(results) == 1
        assert "rrf_score" in results[0]
        assert isinstance(results[0]["rrf_score"], float)

    @pytest.mark.asyncio
    async def test_result_has_required_fields(self) -> None:
        session = _make_session(rows=[_fake_row()])
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            results = await hybrid_retrieve(_QUERY, _ORG, session)

        required = {"id", "supplier_id", "doc_type", "source_id", "content",
                    "signal_type", "severity", "source_name", "published_at", "rrf_score"}
        assert required <= set(results[0].keys())

    @pytest.mark.asyncio
    async def test_published_at_none_serialises_as_none(self) -> None:
        session = _make_session(rows=[_fake_row(published_at=None)])
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            results = await hybrid_retrieve(_QUERY, _ORG, session)

        assert results[0]["published_at"] is None

    @pytest.mark.asyncio
    async def test_published_at_datetime_serialised_as_isoformat(self) -> None:
        dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        session = _make_session(rows=[_fake_row(published_at=dt)])
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            results = await hybrid_retrieve(_QUERY, _ORG, session)

        assert results[0]["published_at"] == dt.isoformat()

    @pytest.mark.asyncio
    async def test_multiple_results_ordered_by_rrf_score(self) -> None:
        rows = [
            _fake_row(id="doc-1", rrf_score=0.031),
            _fake_row(id="doc-2", rrf_score=0.025),
            _fake_row(id="doc-3", rrf_score=0.018),
        ]
        session = _make_session(rows=rows)
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            results = await hybrid_retrieve(_QUERY, _ORG, session, top_k=3)

        # DB returns in order — we preserve it
        assert results[0]["id"] == "doc-1"
        assert results[1]["id"] == "doc-2"
        assert results[2]["id"] == "doc-3"

    @pytest.mark.asyncio
    async def test_top_k_param_passed_to_query(self) -> None:
        session = _make_session(rows=[])
        with patch("application.rag.hybrid_retrieval.embed_query", return_value=_FAKE_EMBEDDING):
            await hybrid_retrieve(_QUERY, _ORG, session, top_k=5)

        params = session.execute.call_args[0][1]
        assert params["top_k"] == 5
