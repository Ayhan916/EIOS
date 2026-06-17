"""
LLM Token Budget Tracker

In-process per-organisation token usage counter with calendar-month reset.
Intended to guard against runaway LLM spend during pilot deployments.

Design decisions:
  - Single-process only (sufficient for pilot; scale to Redis if multi-worker needed).
  - 0 budget = unlimited (opt-out by default so new installs work without config).
  - Calendar-month window resets automatically on first use after month boundary.
  - Thread/async safe: dict mutations are GIL-protected in CPython; no asyncio
    lock needed for read-then-write on a single coroutine await boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from shared.config import settings


class BudgetExceededError(Exception):
    """Raised when an organisation's monthly LLM token budget is exhausted."""

    def __init__(self, org_id: str, used: int, budget: int) -> None:
        self.org_id = org_id
        self.used = used
        self.budget = budget
        super().__init__(
            f"Organisation {org_id!r} has exhausted its monthly LLM budget "
            f"({used:,}/{budget:,} tokens used). "
            "Contact your administrator to increase the limit."
        )


@dataclass
class _OrgUsage:
    tokens_used: int = 0
    period_month: int = field(default_factory=lambda: datetime.now(UTC).month)
    period_year: int = field(default_factory=lambda: datetime.now(UTC).year)


class LLMBudgetTracker:
    """Per-org monthly token budget with automatic calendar-month reset."""

    def __init__(self) -> None:
        self._usage: dict[str, _OrgUsage] = {}

    def _current_period(self) -> tuple[int, int]:
        now = datetime.now(UTC)
        return now.year, now.month

    def _get_usage(self, org_id: str) -> _OrgUsage:
        usage = self._usage.get(org_id)
        if usage is None:
            usage = _OrgUsage()
            self._usage[org_id] = usage
            return usage
        year, month = self._current_period()
        if usage.period_year != year or usage.period_month != month:
            usage.tokens_used = 0
            usage.period_year = year
            usage.period_month = month
        return usage

    def check_and_record(self, org_id: str, tokens: int) -> None:
        """
        Check whether `org_id` has budget for `tokens`, then record the usage.
        Raises BudgetExceededError if the monthly limit would be exceeded.
        No-op when llm_monthly_token_budget == 0 (unlimited).
        """
        budget = settings.llm_monthly_token_budget
        if budget == 0:
            return
        usage = self._get_usage(org_id)
        if usage.tokens_used + tokens > budget:
            raise BudgetExceededError(org_id, usage.tokens_used, budget)
        usage.tokens_used += tokens

    def record(self, org_id: str, tokens: int) -> None:
        """Record actual token usage after an LLM call completes (no limit check)."""
        if settings.llm_monthly_token_budget == 0:
            return
        self._get_usage(org_id).tokens_used += tokens

    def usage_summary(self, org_id: str) -> dict[str, int | str]:
        """Return current usage for an org (for metrics/admin endpoints)."""
        budget = settings.llm_monthly_token_budget
        usage = self._get_usage(org_id)
        year, month = self._current_period()
        return {
            "org_id": org_id,
            "tokens_used": usage.tokens_used,
            "monthly_budget": budget,
            "remaining": max(0, budget - usage.tokens_used) if budget > 0 else -1,
            "period": f"{year}-{month:02d}",
        }

    def reset(self, org_id: str) -> None:
        """Force-reset an org's usage counter (admin use only)."""
        self._usage.pop(org_id, None)


# Process-level singleton — import this everywhere LLM calls are made
budget_tracker = LLMBudgetTracker()
