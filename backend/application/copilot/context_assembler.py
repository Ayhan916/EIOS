"""Context assembler — compresses retrieval results into an LLM-ready context string.

Pure function, no I/O. Enforces a max character budget to avoid prompt bloat.
"""

from __future__ import annotations

import json

from .context_budget import ContextBudget
from .retrieval.base import RetrievalResult

_MAX_CHARS = 8_000
_SECTION_SEPARATOR = "\n---\n"
NO_CONTEXT_MSG = "No relevant data was retrieved for this question."


def _build_section(result: RetrievalResult) -> str:
    header = f"[{result.retriever.upper()}] {result.provenance}"
    try:
        serialized = json.dumps(result.data, default=str, ensure_ascii=False, indent=None)
    except (TypeError, ValueError):
        serialized = str(result.data)
    return f"{header}\n{serialized}"


def assemble_context_with_budget(
    results: list[RetrievalResult],
    max_chars: int = _MAX_CHARS,
) -> tuple[str, ContextBudget]:
    """Build context string and a budget report tracking what was included or omitted.

    Sections are added whole — a section is either fully included or fully
    skipped. This guarantees the context never contains garbled partial data.
    """
    budget = ContextBudget(max_chars=max_chars)

    if not results:
        return NO_CONTEXT_MSG, budget

    sections: list[str] = []
    chars_used = 0

    for result in results:
        if not result.data:
            budget.retrievers_empty.append(result.retriever)
            continue

        section = _build_section(result)
        sep_cost = len(_SECTION_SEPARATOR) if sections else 0
        addition = sep_cost + len(section)

        if chars_used + addition > max_chars:
            budget.truncated = True
            budget.retrievers_omitted.append(result.retriever)
            continue

        sections.append(section)
        budget.retrievers_included.append(result.retriever)
        chars_used += addition

    if not sections:
        return NO_CONTEXT_MSG, budget

    context = _SECTION_SEPARATOR.join(sections)
    budget.used_chars = len(context)
    return context, budget


def assemble_context(results: list[RetrievalResult], max_chars: int = _MAX_CHARS) -> str:
    """Build a compact context string from retrieval results (backward-compatible).

    Each section is prefixed with its provenance description.
    """
    context, _ = assemble_context_with_budget(results, max_chars)
    return context


def build_citation_map(results: list[RetrievalResult]) -> dict[str, str]:
    """Build a map of source_id → citation_type for citation extraction."""
    mapping: dict[str, str] = {}
    for result in results:
        for sid in result.source_ids:
            mapping[sid] = result.citation_type
    return mapping
