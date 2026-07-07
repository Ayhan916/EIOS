"""M36 Unit Tests — Scheduler, dispatch routing, and manual trigger."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_session(scalar_one_or_none=None, scalars_all=None):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
    result.scalars.return_value.all.return_value = scalars_all or []
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_agent(
    agent_id="agent-1",
    agent_type="RISK_MONITOR",
    enabled=True,
    status="ACTIVE",
    run_interval_hours=24,
    failure_count=0,
):
    a = MagicMock()
    a.id = agent_id
    a.agent_type = agent_type
    a.enabled = enabled
    a.status = status
    a.run_interval_hours = run_interval_hours
    a.failure_count = failure_count
    a.run_count = 0
    a.success_count = 0
    return a


def _make_run(run_id="run-1", agent_id="agent-1"):
    r = MagicMock()
    r.id = run_id
    r.agent_id = agent_id
    r.started_at = datetime.now(UTC)
    r.run_status = "RUNNING"
    r.completed_at = None
    r.findings_generated = 0
    r.alerts_generated = 0
    r.actions_recommended = 0
    return r


# ── _dispatch routing ──────────────────────────────────────────────────────────


class TestDispatch:
    async def test_dispatch_risk_monitor(self) -> None:
        from application.agent_monitoring import scheduler

        session = AsyncMock()
        # count queries for alerts/drafts before and after
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        session.execute = AsyncMock(return_value=count_result)

        with patch(
            "application.agent_monitoring.risk_monitor.run",
            new=AsyncMock(return_value=2),
        ):
            findings, alerts, drafts = await scheduler._dispatch(
                "agent-1", "RISK_MONITOR", "run-1", "org-1", session
            )

        assert findings == 2

    async def test_dispatch_regulation_monitor(self) -> None:
        from application.agent_monitoring import scheduler

        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        session.execute = AsyncMock(return_value=count_result)

        with patch(
            "application.agent_monitoring.regulatory_monitor.run",
            new=AsyncMock(return_value=1),
        ):
            findings, _, _ = await scheduler._dispatch(
                "agent-1", "REGULATION_MONITOR", "run-1", "org-1", session
            )

        assert findings == 1

    async def test_dispatch_supplier_monitor(self) -> None:
        from application.agent_monitoring import scheduler

        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        session.execute = AsyncMock(return_value=count_result)

        with patch(
            "application.agent_monitoring.supplier_behaviour_monitor.run",
            new=AsyncMock(return_value=0),
        ):
            findings, _, _ = await scheduler._dispatch(
                "agent-1", "SUPPLIER_MONITOR", "run-1", "org-1", session
            )

        assert findings == 0

    async def test_dispatch_compliance_monitor(self) -> None:
        from application.agent_monitoring import scheduler

        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        session.execute = AsyncMock(return_value=count_result)

        with patch(
            "application.agent_monitoring.compliance_drift_monitor.run",
            new=AsyncMock(return_value=3),
        ):
            findings, _, _ = await scheduler._dispatch(
                "agent-1", "COMPLIANCE_MONITOR", "run-1", "org-1", session
            )

        assert findings == 3

    async def test_dispatch_remediation_monitor(self) -> None:
        from application.agent_monitoring import scheduler

        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        session.execute = AsyncMock(return_value=count_result)

        with patch(
            "application.agent_monitoring.remediation_monitor.run",
            new=AsyncMock(return_value=5),
        ):
            findings, _, _ = await scheduler._dispatch(
                "agent-1", "REMEDIATION_MONITOR", "run-1", "org-1", session
            )

        assert findings == 5

    async def test_dispatch_intelligence_monitor(self) -> None:
        from application.agent_monitoring import scheduler

        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        session.execute = AsyncMock(return_value=count_result)

        with patch(
            "application.agent_monitoring.intelligence_monitor.run",
            new=AsyncMock(return_value=1),
        ):
            findings, _, _ = await scheduler._dispatch(
                "agent-1", "INTELLIGENCE_MONITOR", "run-1", "org-1", session
            )

        assert findings == 1

    async def test_dispatch_unknown_agent_type_returns_zero(self) -> None:
        from application.agent_monitoring import scheduler

        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        session.execute = AsyncMock(return_value=count_result)

        findings, alerts, drafts = await scheduler._dispatch(
            "agent-1", "UNKNOWN_AGENT_XYZ", "run-1", "org-1", session
        )

        assert findings == 0
        assert alerts == 0
        assert drafts == 0


# ── _execute_agent ─────────────────────────────────────────────────────────────


class TestExecuteAgent:
    async def test_execute_records_completed_on_success(self) -> None:
        from application.agent_monitoring import scheduler

        run = _make_run()

        with (
            patch(
                "application.agent_monitoring.agent_service.check_and_start_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "application.agent_monitoring.scheduler._dispatch",
                new=AsyncMock(return_value=(2, 1, 0)),
            ),
            patch(
                "application.agent_monitoring.agent_service.record_run_completed",
                new=AsyncMock(),
            ) as mock_completed,
        ):
            session = AsyncMock()
            await scheduler._execute_agent("agent-1", "RISK_MONITOR", "org-1", session)

        mock_completed.assert_awaited_once()

    async def test_execute_propagates_exception_without_recording_failed(self) -> None:
        """F3: _execute_agent must not call record_run_failed — the outer
        session.begin() rolls back everything; _mark_agent_failed() records it."""
        from application.agent_monitoring import scheduler

        run = _make_run()

        with (
            patch(
                "application.agent_monitoring.agent_service.check_and_start_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "application.agent_monitoring.scheduler._dispatch",
                new=AsyncMock(side_effect=RuntimeError("DB error")),
            ),
            patch(
                "application.agent_monitoring.agent_service.record_run_failed",
                new=AsyncMock(),
            ) as mock_failed,
        ):
            session = AsyncMock()
            with pytest.raises(RuntimeError, match="DB error"):
                await scheduler._execute_agent("agent-1", "RISK_MONITOR", "org-1", session)

        # F3: record_run_failed must NOT be called inside _execute_agent
        mock_failed.assert_not_awaited()


# ── trigger_agent_run ──────────────────────────────────────────────────────────


class TestTriggerAgentRun:
    async def test_trigger_known_enabled_agent(self) -> None:
        from application.agent_monitoring import scheduler

        agent = _make_agent()
        run = _make_run()

        session = _make_session(scalar_one_or_none=agent)
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)

        with (
            patch(
                "application.agent_monitoring.agent_service.get_agent_by_type",
                new=AsyncMock(return_value=agent),
            ),
            patch(
                "application.agent_monitoring.agent_service.check_and_start_run",
                new=AsyncMock(return_value=run),
            ),
            patch(
                "application.agent_monitoring.scheduler._dispatch",
                new=AsyncMock(return_value=(1, 0, 0)),
            ),
            patch(
                "application.agent_monitoring.agent_service.record_run_completed",
                new=AsyncMock(),
            ),
        ):
            result = await scheduler.trigger_agent_run("RISK_MONITOR", "org-1", session)

        assert result is run

    async def test_trigger_unknown_agent_raises(self) -> None:
        from application.agent_monitoring import scheduler

        session = _make_session(scalar_one_or_none=None)

        with patch(
            "application.agent_monitoring.agent_service.get_agent_by_type",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(ValueError, match="Unknown agent type"):
                await scheduler.trigger_agent_run("DOES_NOT_EXIST", "org-1", session)

    async def test_trigger_disabled_agent_raises(self) -> None:
        from application.agent_monitoring import scheduler

        agent = _make_agent(enabled=False)
        session = _make_session(scalar_one_or_none=agent)

        with patch(
            "application.agent_monitoring.agent_service.get_agent_by_type",
            new=AsyncMock(return_value=agent),
        ):
            with pytest.raises(ValueError, match="disabled"):
                await scheduler.trigger_agent_run("RISK_MONITOR", "org-1", session)


# ── Scheduler constants ────────────────────────────────────────────────────────


class TestSchedulerConstants:
    def test_check_interval_is_one_hour(self) -> None:
        from application.agent_monitoring.scheduler import _CHECK_INTERVAL_SECONDS

        assert _CHECK_INTERVAL_SECONDS == 3600

    def test_startup_delay_is_reasonable(self) -> None:
        from application.agent_monitoring.scheduler import _STARTUP_DELAY_SECONDS

        # Must be positive and less than check interval
        assert 0 < _STARTUP_DELAY_SECONDS < 3600

    def test_all_six_agent_types_in_dispatch(self) -> None:
        """All 6 agent types must be in the dispatch_map — no silent no-ops."""
        import inspect

        from application.agent_monitoring import scheduler

        src = inspect.getsource(scheduler._dispatch)

        expected = [
            "RISK_MONITOR",
            "REGULATION_MONITOR",
            "SUPPLIER_MONITOR",
            "COMPLIANCE_MONITOR",
            "REMEDIATION_MONITOR",
            "INTELLIGENCE_MONITOR",
        ]
        for agent_type in expected:
            assert agent_type in src, f"{agent_type} missing from dispatch_map"
