"""Chunking domain value objects — E1-F3 (ADR-009).

ParentChunk  — section-level context window, NOT embedded, not retrieved directly.
ChildChunk   — retrieval unit, embedded and searched; carries parent reference.

Sizes follow ADR-009:
  Parent: 1500 words  (section boundary, provides full table context)
  Child:  250 words   (retrieval unit, small enough for LLM to use precisely)
  Child overlap: 50 words (avoids cross-chunk fragmentation of values/labels)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChildChunk:
    """One retrieval unit inside a parent window.

    Attributes:
        text:         The child text (250 words target).
        parent_index: Index of the parent window this child belongs to.
        child_index:  Position of this child within its parent.
    """

    text: str
    parent_index: int
    child_index: int


@dataclass(frozen=True)
class ParentChunk:
    """One section-level window containing multiple child chunks.

    Attributes:
        text:         Full section text (1500 words target).
        parent_index: Sequential index of this parent in the document.
        children:     Child retrieval units derived from this parent.
    """

    text: str
    parent_index: int
    children: tuple[ChildChunk, ...]
