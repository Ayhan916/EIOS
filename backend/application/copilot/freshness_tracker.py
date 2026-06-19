"""Data Freshness Layer — M33.2.

Analyses the age of retrieved objects and produces human-readable freshness
reports that are injected into the system prompt and persisted with each answer.
Pure function — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .retrieval.base import RetrievalResult

# Days thresholds per retriever before data is considered stale
_STALE_THRESHOLDS: dict[str, int] = {
    "supplier_retriever": 7,
    "compliance_retriever": 30,
    "disclosure_retriever": 14,
    "due_diligence_retriever": 60,
    "executive_retriever": 30,
}
_DEFAULT_STALE_DAYS = 30


@dataclass
class FreshnessReport:
    oldest_age_days: float = 0.0
    newest_age_days: float = 0.0
    average_age_days: float = 0.0
    stale_retrievers: list[str] = field(default_factory=list)
    freshness_by_retriever: dict[str, float] = field(default_factory=dict)
    has_stale_data: bool = False
    freshness_warning: str = ""


def _age_days(updated_at_iso: str | None, retrieved_at_iso: str) -> float:
    if not updated_at_iso:
        return 0.0
    try:
        updated = datetime.fromisoformat(updated_at_iso.replace("Z", "+00:00"))
        retrieved = datetime.fromisoformat(retrieved_at_iso.replace("Z", "+00:00"))
        diff = retrieved - updated
        return max(0.0, diff.total_seconds() / 86400)
    except (ValueError, TypeError):
        return 0.0


def analyze_freshness(results: list[RetrievalResult]) -> FreshnessReport:
    """Compute a freshness report from all retrieval results."""
    all_ages: list[float] = []
    stale_retrievers: list[str] = []
    freshness_by_retriever: dict[str, float] = {}

    for result in results:
        if not result.freshness_metadata:
            continue
        ages = [
            _age_days(obj.get("updated_at"), obj.get("retrieved_at", ""))
            for obj in result.freshness_metadata
        ]
        if not ages:
            continue
        avg_age = sum(ages) / len(ages)
        freshness_by_retriever[result.retriever] = avg_age
        all_ages.extend(ages)

        threshold = _STALE_THRESHOLDS.get(result.retriever, _DEFAULT_STALE_DAYS)
        if avg_age > threshold:
            stale_retrievers.append(result.retriever)

    if not all_ages:
        return FreshnessReport()

    report = FreshnessReport(
        oldest_age_days=max(all_ages),
        newest_age_days=min(all_ages),
        average_age_days=sum(all_ages) / len(all_ages),
        stale_retrievers=stale_retrievers,
        freshness_by_retriever=freshness_by_retriever,
        has_stale_data=len(stale_retrievers) > 0,
    )

    if report.has_stale_data:
        stale_descriptions = []
        for r in stale_retrievers:
            age = freshness_by_retriever.get(r, 0)
            label = r.replace("_retriever", "").replace("_", " ")
            stale_descriptions.append(f"{label} data ({age:.0f} days old)")
        report.freshness_warning = (
            "STALE DATA WARNING: The following sources have not been updated recently: "
            + ", ".join(stale_descriptions)
            + ". Treat time-sensitive conclusions with caution."
        )

    return report


def format_freshness_for_prompt(report: FreshnessReport) -> str:
    """Return a prompt hint for stale data, empty string if all data is fresh."""
    return report.freshness_warning


def freshness_summary_dict(report: FreshnessReport) -> dict:
    """Serialisable summary for persistence on CopilotMessage."""
    return {
        "oldest_age_days": round(report.oldest_age_days, 1),
        "newest_age_days": round(report.newest_age_days, 1),
        "average_age_days": round(report.average_age_days, 1),
        "has_stale_data": report.has_stale_data,
        "stale_retrievers": report.stale_retrievers,
        "freshness_by_retriever": {
            k: round(v, 1) for k, v in report.freshness_by_retriever.items()
        },
    }
