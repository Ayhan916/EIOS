"""Tests for application/rag/parent_child_chunker.py — E1-F3 (ADR-009).

Invariants verified:
  - Empty text → empty list
  - Short text (< parent size) → one parent
  - Full text → multiple parents, each with ≥1 child
  - Children cover all parent words (no words dropped)
  - Child overlap: consecutive children share _CHILD_OVERLAP words
  - Parent text == joined words of all children (approximately)
  - Parent-Child VOs are immutable (frozen dataclass)
  - PARENT_CHILD_DOC_TYPES contains annual_report and financial_statement
  - child.parent_index matches parent.parent_index
  - child.child_index is sequential within each parent
"""

from __future__ import annotations

import pytest

from application.rag.parent_child_chunker import (
    PARENT_CHILD_DOC_TYPES,
    _CHILD_OVERLAP,
    _CHILD_SIZE,
    _PARENT_SIZE,
    chunk_parent_child,
)
from domain.chunking import ChildChunk, ParentChunk

pytestmark = pytest.mark.unit


def _words(n: int) -> str:
    """Generate a string of n distinct words."""
    return " ".join(f"w{i}" for i in range(n))


# ── basic structure ───────────────────────────────────────────────────────────


class TestBasicStructure:
    def test_empty_text_returns_empty(self) -> None:
        assert chunk_parent_child("") == []

    def test_whitespace_only_returns_empty(self) -> None:
        assert chunk_parent_child("   \n\t  ") == []

    def test_short_text_yields_one_parent(self) -> None:
        result = chunk_parent_child(_words(100))
        assert len(result) == 1

    def test_returns_list_of_parent_chunks(self) -> None:
        result = chunk_parent_child(_words(200))
        assert all(isinstance(p, ParentChunk) for p in result)

    def test_each_parent_has_children(self) -> None:
        result = chunk_parent_child(_words(500))
        for parent in result:
            assert len(parent.children) >= 1

    def test_children_are_child_chunk_instances(self) -> None:
        result = chunk_parent_child(_words(300))
        for parent in result:
            for child in parent.children:
                assert isinstance(child, ChildChunk)

    def test_parent_is_frozen(self) -> None:
        result = chunk_parent_child(_words(100))
        with pytest.raises((AttributeError, TypeError)):
            result[0].parent_index = 99  # type: ignore[misc]

    def test_child_is_frozen(self) -> None:
        result = chunk_parent_child(_words(300))
        child = result[0].children[0]
        with pytest.raises((AttributeError, TypeError)):
            child.child_index = 99  # type: ignore[misc]


# ── parent sizing ─────────────────────────────────────────────────────────────


class TestParentSizing:
    def test_full_parent_has_parent_size_words(self) -> None:
        # Text exactly 2× parent size → 2 parents, each with _PARENT_SIZE words
        text = _words(_PARENT_SIZE * 2)
        result = chunk_parent_child(text)
        assert len(result) == 2
        assert len(result[0].text.split()) == _PARENT_SIZE

    def test_parent_index_is_sequential(self) -> None:
        text = _words(_PARENT_SIZE * 3)
        result = chunk_parent_child(text)
        for i, parent in enumerate(result):
            assert parent.parent_index == i

    def test_parent_text_non_empty(self) -> None:
        result = chunk_parent_child(_words(200))
        for parent in result:
            assert parent.text.strip()


# ── child sizing and overlap ──────────────────────────────────────────────────


class TestChildSizing:
    def test_child_size_at_most_child_size_words(self) -> None:
        result = chunk_parent_child(_words(_PARENT_SIZE))
        for parent in result:
            for child in parent.children:
                assert len(child.text.split()) <= _CHILD_SIZE

    def test_child_parent_index_matches_parent(self) -> None:
        text = _words(_PARENT_SIZE * 2)
        result = chunk_parent_child(text)
        for parent in result:
            for child in parent.children:
                assert child.parent_index == parent.parent_index

    def test_child_index_sequential(self) -> None:
        result = chunk_parent_child(_words(_PARENT_SIZE))
        parent = result[0]
        for i, child in enumerate(parent.children):
            assert child.child_index == i

    def test_consecutive_children_overlap(self) -> None:
        """Last _CHILD_OVERLAP words of child[i] == first _CHILD_OVERLAP words of child[i+1]."""
        text = _words(_PARENT_SIZE)
        result = chunk_parent_child(text)
        parent = result[0]
        if len(parent.children) < 2:
            pytest.skip("Need at least 2 children to test overlap")

        child_a_words = parent.children[0].text.split()
        child_b_words = parent.children[1].text.split()
        overlap_from_a = child_a_words[-_CHILD_OVERLAP:]
        start_of_b = child_b_words[:_CHILD_OVERLAP]
        assert overlap_from_a == start_of_b

    def test_all_parent_words_covered_by_children(self) -> None:
        """Union of child texts must contain all parent words (no drops)."""
        text = _words(_PARENT_SIZE)
        result = chunk_parent_child(text)
        parent = result[0]
        parent_words = set(parent.text.split())
        child_words: set[str] = set()
        for child in parent.children:
            child_words.update(child.text.split())
        assert parent_words.issubset(child_words)


# ── PARENT_CHILD_DOC_TYPES ────────────────────────────────────────────────────


class TestDocTypes:
    def test_annual_report_in_set(self) -> None:
        assert "annual_report" in PARENT_CHILD_DOC_TYPES

    def test_financial_statement_in_set(self) -> None:
        assert "financial_statement" in PARENT_CHILD_DOC_TYPES

    def test_sustainability_report_not_in_set(self) -> None:
        assert "sustainability_report" not in PARENT_CHILD_DOC_TYPES

    def test_set_is_frozenset(self) -> None:
        assert isinstance(PARENT_CHILD_DOC_TYPES, frozenset)


# ── large document ────────────────────────────────────────────────────────────


class TestLargeDocument:
    def test_ten_parent_document(self) -> None:
        text = _words(_PARENT_SIZE * 10)
        result = chunk_parent_child(text)
        assert len(result) == 10

    def test_total_children_count_reasonable(self) -> None:
        """For 1 parent of 1500 words with child_size=250, overlap=50:
        effective step = 200 → ceil(1500/200) = 8 children (approx)."""
        text = _words(_PARENT_SIZE)
        result = chunk_parent_child(text)
        total_children = sum(len(p.children) for p in result)
        # Should be between 6 and 12 (rough bounds)
        assert 6 <= total_children <= 12
