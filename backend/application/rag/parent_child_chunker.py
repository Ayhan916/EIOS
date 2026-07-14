"""Parent-Child Chunking Strategy — E1-F3 (ADR-009).

Produces a two-level chunk hierarchy from raw text:
  Parent: 1500-word windows (section context, stored but not embedded)
  Child:  250-word windows with 50-word overlap (retrieval units, embedded)

Use for doc_types that have dense tables across chunk boundaries:
  annual_report, financial_statement

Flat chunking (existing _chunk_text) stays unchanged for all other types.

Public API:
  chunk_parent_child(text) -> list[ParentChunk]
"""

from __future__ import annotations

from domain.chunking import ChildChunk, ParentChunk

# ADR-009: sizes chosen to keep full financial table rows inside one parent
_PARENT_SIZE = 1500   # words per parent window
_CHILD_SIZE = 250     # words per child window
_CHILD_OVERLAP = 50   # overlap between adjacent children

# Doc types that benefit from parent-child chunking
PARENT_CHILD_DOC_TYPES: frozenset[str] = frozenset(
    {"annual_report", "financial_statement"}
)


def chunk_parent_child(text: str) -> list[ParentChunk]:
    """Split text into parent windows, each sub-divided into child chunks.

    Returns an empty list for empty input.
    """
    words = text.split()
    if not words:
        return []

    parents: list[ParentChunk] = []
    parent_start = 0
    parent_index = 0

    while parent_start < len(words):
        parent_words = words[parent_start: parent_start + _PARENT_SIZE]
        parent_text = " ".join(parent_words)

        children = _make_children(parent_words, parent_index)
        parents.append(
            ParentChunk(
                text=parent_text,
                parent_index=parent_index,
                children=tuple(children),
            )
        )
        parent_start += _PARENT_SIZE
        parent_index += 1

    return parents


# ── private helpers ────────────────────────────────────────────────────────────


def _make_children(parent_words: list[str], parent_index: int) -> list[ChildChunk]:
    """Produce overlapping child windows within one parent's word list."""
    children: list[ChildChunk] = []
    child_index = 0
    start = 0

    while start < len(parent_words):
        child_words = parent_words[start: start + _CHILD_SIZE]
        children.append(
            ChildChunk(
                text=" ".join(child_words),
                parent_index=parent_index,
                child_index=child_index,
            )
        )
        start += _CHILD_SIZE - _CHILD_OVERLAP
        child_index += 1

    return children
