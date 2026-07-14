"""Tests for application/intelligence/entity_linker_service.py — E2-F3.

Uses an async in-memory mock session to verify that:
  - load_candidates returns correct EntityCandidate list
  - link_signals updates supplier_id on matching signals
  - link_signals skips signals below min_confidence
  - link_signals with no suppliers returns early
  - link_metrics mirrors the same logic for metrics
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from domain.entity_match import EntityCandidate, EntityMatch

pytestmark = pytest.mark.unit


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_supplier(supplier_id: str, name: str, legal_name: str | None = None):
    m = MagicMock()
    m.id = supplier_id
    m.name = name
    m.legal_name = legal_name
    m.organization_id = "org-1"
    return m


def _make_signal(signal_id: str, company_name: str, supplier_id: str | None = None):
    m = MagicMock()
    m.id = signal_id
    m.company_name = company_name
    m.supplier_id = supplier_id
    return m


def _make_alias(supplier_id: str, alias: str):
    m = MagicMock()
    m.supplier_id = supplier_id
    m.alias = alias
    return m


def _mock_session(supplier_rows=None, alias_rows=None, signal_rows=None, metric_rows=None):
    """Return an AsyncSession mock with controllable execute results."""
    session = AsyncMock()
    session.add = MagicMock()

    async def execute_side_effect(stmt):
        result = MagicMock()
        # Determine which query is being run by checking the model class
        stmt_str = str(stmt).lower() if hasattr(stmt, "__str__") else ""
        # Return appropriate rows based on call order
        execute_side_effect._call_count = getattr(execute_side_effect, "_call_count", 0) + 1
        count = execute_side_effect._call_count

        # call 1: suppliers, call 2: aliases, call 3: signals/metrics
        if count == 1:
            rows = supplier_rows or []
        elif count == 2:
            rows = alias_rows or []
        else:
            rows = signal_rows or metric_rows or []

        scalars = MagicMock()
        scalars.all.return_value = rows
        result.scalars.return_value = scalars
        return result

    session.execute = execute_side_effect
    session.begin_nested = MagicMock()
    return session


# ── load_candidates ───────────────────────────────────────────────────────────

class TestLoadCandidates:
    @pytest.mark.asyncio
    async def test_empty_suppliers_returns_empty(self) -> None:
        from application.intelligence.entity_linker_service import load_candidates
        session = _mock_session(supplier_rows=[])
        result = await load_candidates("org-1", session)
        assert result == []

    @pytest.mark.asyncio
    async def test_single_supplier_no_aliases(self) -> None:
        from application.intelligence.entity_linker_service import load_candidates
        suppliers = [_make_supplier("s1", "BMW AG", "Bayerische Motoren Werke AG")]
        session = _mock_session(supplier_rows=suppliers, alias_rows=[])
        result = await load_candidates("org-1", session)
        assert len(result) == 1
        assert result[0].supplier_id == "s1"
        assert result[0].canonical_name == "BMW AG"
        assert result[0].legal_name == "Bayerische Motoren Werke AG"
        assert result[0].aliases == ()

    @pytest.mark.asyncio
    async def test_supplier_with_aliases(self) -> None:
        from application.intelligence.entity_linker_service import load_candidates
        suppliers = [_make_supplier("s1", "BMW AG")]
        aliases = [_make_alias("s1", "BMW Group"), _make_alias("s1", "BMW")]
        session = _mock_session(supplier_rows=suppliers, alias_rows=aliases)
        result = await load_candidates("org-1", session)
        assert len(result) == 1
        assert "BMW Group" in result[0].aliases
        assert "BMW" in result[0].aliases


# ── link_signals ──────────────────────────────────────────────────────────────

class TestLinkSignals:
    @pytest.mark.asyncio
    async def test_links_alias_match(self) -> None:
        """Signal 'BMW Group' → BMW AG supplier_id (alias match, confidence 0.9)."""
        from application.intelligence.entity_linker_service import link_signals

        suppliers = [_make_supplier("s1", "BMW AG")]
        aliases = [_make_alias("s1", "BMW Group")]
        signal = _make_signal("sig-1", "BMW Group")

        session = _mock_session(
            supplier_rows=suppliers,
            alias_rows=aliases,
            signal_rows=[signal],
        )

        result = await link_signals("org-1", session, min_confidence=0.7)
        assert result["linked"] == 1
        assert result["skipped"] == 0
        assert signal.supplier_id == "s1"

    @pytest.mark.asyncio
    async def test_links_exact_match(self) -> None:
        """Signal 'BMW AG' → supplier_id via exact match (confidence 1.0)."""
        from application.intelligence.entity_linker_service import link_signals

        suppliers = [_make_supplier("s1", "BMW AG")]
        signal = _make_signal("sig-2", "BMW AG")

        session = _mock_session(
            supplier_rows=suppliers, alias_rows=[], signal_rows=[signal]
        )
        result = await link_signals("org-1", session, min_confidence=0.9)
        assert result["linked"] == 1
        assert signal.supplier_id == "s1"

    @pytest.mark.asyncio
    async def test_skips_unknown_company(self) -> None:
        """Completely unknown company → no link, supplier_id stays None."""
        from application.intelligence.entity_linker_service import link_signals

        suppliers = [_make_supplier("s1", "BMW AG")]
        signal = _make_signal("sig-3", "Completely Unknown Corp XYZ")

        session = _mock_session(
            supplier_rows=suppliers, alias_rows=[], signal_rows=[signal]
        )
        result = await link_signals("org-1", session, min_confidence=0.7)
        assert result["linked"] == 0
        assert result["skipped"] == 1
        assert signal.supplier_id is None

    @pytest.mark.asyncio
    async def test_no_suppliers_returns_early(self) -> None:
        from application.intelligence.entity_linker_service import link_signals

        session = _mock_session(supplier_rows=[])
        result = await link_signals("org-1", session)
        assert result["linked"] == 0
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_min_confidence_filters_fuzzy(self) -> None:
        """With min_confidence=1.0, fuzzy and alias matches are rejected."""
        from application.intelligence.entity_linker_service import link_signals

        suppliers = [_make_supplier("s1", "BMW AG")]
        aliases = [_make_alias("s1", "BMW Group")]
        signal = _make_signal("sig-4", "BMW Group")  # alias → 0.9 < 1.0

        session = _mock_session(
            supplier_rows=suppliers, alias_rows=aliases, signal_rows=[signal]
        )
        result = await link_signals("org-1", session, min_confidence=1.0)
        assert result["linked"] == 0
        assert result["skipped"] == 1


# ── link_metrics ──────────────────────────────────────────────────────────────

class TestLinkMetrics:
    @pytest.mark.asyncio
    async def test_links_metric_by_company_name(self) -> None:
        from application.intelligence.entity_linker_service import link_metrics

        suppliers = [_make_supplier("s1", "BMW AG")]
        metric = _make_signal("met-1", "BMW AG")  # reuse signal mock, same fields

        session = _mock_session(
            supplier_rows=suppliers, alias_rows=[], metric_rows=[metric]
        )
        result = await link_metrics("org-1", session)
        assert result["linked"] == 1
        assert metric.supplier_id == "s1"
