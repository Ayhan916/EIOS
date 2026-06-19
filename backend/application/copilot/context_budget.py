"""Context Budget Management — M33.2.

Tracks what data was included or omitted during context assembly, allowing
the Copilot to explain when sources were dropped due to size constraints.
Pure function — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .retrieval.base import RetrievalResult


@dataclass
class ContextBudget:
    max_chars: int
    used_chars: int = 0
    truncated: bool = False
    retrievers_included: list[str] = field(default_factory=list)
    retrievers_omitted: list[str] = field(default_factory=list)
    retrievers_empty: list[str] = field(default_factory=list)


def format_budget_note(budget: ContextBudget) -> str:
    """Return a system-prompt note when sources were omitted, empty string otherwise."""
    if not budget.truncated or not budget.retrievers_omitted:
        return ""
    labels = [r.replace("_retriever", "").replace("_", " ") for r in budget.retrievers_omitted]
    return (
        "CONTEXT LIMIT NOTE: The following data sources were omitted due to context size limits: "
        + ", ".join(labels)
        + ". Acknowledge this limitation if the omitted sources are relevant to the question."
    )


def budget_dict(budget: ContextBudget) -> dict:
    """Serialisable budget report for persistence."""
    return {
        "max_chars": budget.max_chars,
        "used_chars": budget.used_chars,
        "truncated": budget.truncated,
        "retrievers_included": budget.retrievers_included,
        "retrievers_omitted": budget.retrievers_omitted,
        "retrievers_empty": budget.retrievers_empty,
    }
