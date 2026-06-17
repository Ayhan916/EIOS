"""Unit tests for M20 LLM Budget Tracker."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import patch

import pytest

from application.budget.tracker import BudgetExceededError, LLMBudgetTracker


class TestBudgetTrackerUnlimited:
    def test_no_limit_by_default(self) -> None:
        tracker = LLMBudgetTracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 0
            # Must not raise regardless of tokens requested
            tracker.check_and_record("org-1", 10_000_000)

    def test_record_noop_when_unlimited(self) -> None:
        tracker = LLMBudgetTracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 0
            tracker.record("org-1", 5000)
            # No state tracked when unlimited
            assert "org-1" not in tracker._usage


class TestBudgetTrackerEnforced:
    def _tracker(self, budget: int = 10_000) -> LLMBudgetTracker:
        return LLMBudgetTracker()

    def test_check_and_record_within_budget(self) -> None:
        tracker = self._tracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 10_000
            tracker.check_and_record("org-1", 5000)
            assert tracker._usage["org-1"].tokens_used == 5000

    def test_check_and_record_at_exact_limit(self) -> None:
        tracker = self._tracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 10_000
            tracker.check_and_record("org-1", 10_000)
            assert tracker._usage["org-1"].tokens_used == 10_000

    def test_check_and_record_exceeds_budget(self) -> None:
        tracker = self._tracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 1000
            tracker.check_and_record("org-1", 900)
            with pytest.raises(BudgetExceededError) as exc_info:
                tracker.check_and_record("org-1", 200)
            err = exc_info.value
            assert err.org_id == "org-1"
            assert err.used == 900
            assert err.budget == 1000

    def test_multiple_orgs_isolated(self) -> None:
        tracker = self._tracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 1000
            tracker.check_and_record("org-a", 800)
            tracker.check_and_record("org-b", 800)  # different org, must not raise
            assert tracker._usage["org-a"].tokens_used == 800
            assert tracker._usage["org-b"].tokens_used == 800

    def test_reset_clears_usage(self) -> None:
        tracker = self._tracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 1000
            tracker.check_and_record("org-1", 900)
            tracker.reset("org-1")
            tracker.check_and_record("org-1", 900)  # must not raise after reset

    def test_usage_summary_structure(self) -> None:
        tracker = self._tracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 5000
            tracker.check_and_record("org-x", 1200)
            summary = tracker.usage_summary("org-x")
            assert summary["org_id"] == "org-x"
            assert summary["tokens_used"] == 1200
            assert summary["monthly_budget"] == 5000
            assert summary["remaining"] == 3800

    def test_usage_summary_unlimited(self) -> None:
        tracker = self._tracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 0
            summary = tracker.usage_summary("org-y")
            assert summary["remaining"] == -1  # sentinel for unlimited

    def test_calendar_month_reset(self) -> None:
        from datetime import datetime

        tracker = LLMBudgetTracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 1000
            tracker.check_and_record("org-1", 900)
            assert tracker._usage["org-1"].tokens_used == 900

            # Simulate time advancing to next month
            next_month = datetime(2026, 7, 1, tzinfo=UTC)
            with patch("application.budget.tracker.datetime") as mock_dt:
                mock_dt.now.return_value = next_month
                # _get_usage should reset the counter
                usage = tracker._get_usage("org-1")
                assert usage.tokens_used == 0

    def test_budget_exceeded_error_message(self) -> None:
        err = BudgetExceededError("org-1", 9500, 10000)
        assert "org-1" in str(err)
        assert "9,500" in str(err)
        assert "10,000" in str(err)


class TestBudgetTrackerRecord:
    def test_record_accumulates_without_limit_check(self) -> None:
        tracker = LLMBudgetTracker()
        with patch("application.budget.tracker.settings") as mock_settings:
            mock_settings.llm_monthly_token_budget = 100
            # Record only (post-call accounting), can exceed limit
            tracker.record("org-1", 50)
            tracker.record("org-1", 80)  # 130 total — no BudgetExceededError
            assert tracker._usage["org-1"].tokens_used == 130
