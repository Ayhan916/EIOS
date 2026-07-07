"""M36 Unit Tests — Agent Framework (agent_service, finding_service, run lifecycle)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

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
    status="ACTIVE",
    enabled=True,
    run_interval_hours=24,
    failure_count=0,
):
    agent = MagicMock()
    agent.id = agent_id
    agent.agent_type = agent_type
    agent.status = status
    agent.enabled = enabled
    agent.run_interval_hours = run_interval_hours
    agent.failure_count = failure_count
    agent.run_count = 0
    agent.success_count = 0
    agent.last_run_at = None
    agent.next_run_at = None
    agent.updated_at = None
    return agent


def _make_run(run_id="run-1", agent_id="agent-1", started_at=None):
    run = MagicMock()
    run.id = run_id
    run.agent_id = agent_id
    run.started_at = started_at or datetime.now(UTC)
    run.run_status = "RUNNING"
    run.completed_at = None
    run.findings_generated = 0
    run.alerts_generated = 0
    run.actions_recommended = 0
    run.error_message = None
    run.execution_time_ms = None
    run.updated_at = None
    return run


# ── seed_monitoring_agents ─────────────────────────────────────────────────────


class TestSeedMonitoringAgents:
    async def test_seeds_all_builtin_agents_when_none_exist(self) -> None:
        from application.agent_monitoring.agent_service import seed_monitoring_agents
        from domain.agent_monitoring import BUILTIN_AGENTS

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=result)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seed_monitoring_agents(session)

        assert session.add.call_count == len(BUILTIN_AGENTS)

    async def test_skips_existing_agents(self) -> None:
        from application.agent_monitoring.agent_service import seed_monitoring_agents

        existing = MagicMock()
        session = _make_session(scalar_one_or_none=existing)

        await seed_monitoring_agents(session)

        session.add.assert_not_called()

    async def test_seed_is_idempotent_partial(self) -> None:
        """Seeds only missing agents when some already exist."""
        from application.agent_monitoring.agent_service import seed_monitoring_agents
        from domain.agent_monitoring import BUILTIN_AGENTS

        total = len(BUILTIN_AGENTS)
        call_count = 0

        async def _side_effect(_stmt):
            nonlocal call_count
            result = MagicMock()
            # Return existing for first 3, None for remaining
            result.scalar_one_or_none = MagicMock(
                return_value=MagicMock() if call_count < 3 else None
            )
            call_count += 1
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_side_effect)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await seed_monitoring_agents(session)

        assert session.add.call_count == total - 3


# ── get_agent / list_agents ────────────────────────────────────────────────────


class TestAgentQueries:
    async def test_get_agent_returns_none_when_missing(self) -> None:
        from application.agent_monitoring.agent_service import get_agent

        session = _make_session(scalar_one_or_none=None)
        result = await get_agent("nonexistent", session)
        assert result is None

    async def test_get_agent_returns_model_when_found(self) -> None:
        from application.agent_monitoring.agent_service import get_agent

        agent = _make_agent()
        session = _make_session(scalar_one_or_none=agent)
        result = await get_agent("agent-1", session)
        assert result is agent

    async def test_get_agent_by_type(self) -> None:
        from application.agent_monitoring.agent_service import get_agent_by_type

        agent = _make_agent(agent_type="COMPLIANCE_MONITOR")
        session = _make_session(scalar_one_or_none=agent)
        result = await get_agent_by_type("COMPLIANCE_MONITOR", session)
        assert result.agent_type == "COMPLIANCE_MONITOR"

    async def test_list_agents_returns_all(self) -> None:
        from application.agent_monitoring.agent_service import list_agents

        agents = [_make_agent(agent_id=f"a{i}") for i in range(6)]
        session = _make_session(scalars_all=agents)
        result = await list_agents(session)
        assert len(result) == 6


# ── set_agent_enabled ──────────────────────────────────────────────────────────


class TestSetAgentEnabled:
    async def test_enable_sets_active(self) -> None:
        from application.agent_monitoring.agent_service import set_agent_enabled

        agent = _make_agent(enabled=False, status="PAUSED")
        session = _make_session(scalar_one_or_none=agent)

        await set_agent_enabled("agent-1", True, session)

        assert agent.enabled is True
        assert agent.status == "ACTIVE"

    async def test_disable_sets_paused(self) -> None:
        from application.agent_monitoring.agent_service import set_agent_enabled

        agent = _make_agent(enabled=True, status="ACTIVE")
        session = _make_session(scalar_one_or_none=agent)

        await set_agent_enabled("agent-1", False, session)

        assert agent.enabled is False
        assert agent.status == "PAUSED"

    async def test_returns_none_when_agent_not_found(self) -> None:
        from application.agent_monitoring.agent_service import set_agent_enabled

        session = _make_session(scalar_one_or_none=None)
        result = await set_agent_enabled("missing", True, session)
        assert result is None


# ── get_due_agents ─────────────────────────────────────────────────────────────


class TestGetDueAgents:
    async def test_returns_due_agents(self) -> None:
        from application.agent_monitoring.agent_service import get_due_agents

        due = [_make_agent()]
        session = _make_session(scalars_all=due)
        result = await get_due_agents(session)
        assert len(result) == 1

    async def test_returns_empty_when_none_due(self) -> None:
        from application.agent_monitoring.agent_service import get_due_agents

        session = _make_session(scalars_all=[])
        result = await get_due_agents(session)
        assert result == []


# ── record_run_start ───────────────────────────────────────────────────────────


class TestRecordRunStart:
    async def test_creates_run_record(self) -> None:
        from application.agent_monitoring.agent_service import record_run_start

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        run = await record_run_start("agent-1", "org-1", session)

        # add called ≥1: MonitoringAgentRunModel + AuditEventModel for agent.run.started
        assert session.add.call_count >= 1
        assert run.run_status == "RUNNING"
        assert run.agent_id == "agent-1"
        assert run.organization_id == "org-1"

    async def test_run_id_is_uuid(self) -> None:
        import re

        from application.agent_monitoring.agent_service import record_run_start

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        run = await record_run_start("agent-1", "org-1", session)
        assert re.match(r"[0-9a-f-]{36}", run.id)


# ── record_run_completed ───────────────────────────────────────────────────────


class TestRecordRunCompleted:
    async def test_marks_completed_and_updates_agent(self) -> None:
        from application.agent_monitoring.agent_service import record_run_completed

        run = _make_run()
        agent = _make_agent()

        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=run)
            else:
                result.scalar_one_or_none = MagicMock(return_value=agent)
            call_count += 1
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        await record_run_completed("run-1", "agent-1", 3, 2, 1, session)

        assert run.run_status == "COMPLETED"
        assert run.findings_generated == 3
        assert run.alerts_generated == 2
        assert run.actions_recommended == 1
        assert agent.run_count == 1
        assert agent.success_count == 1


# ── record_run_failed ──────────────────────────────────────────────────────────


class TestRecordRunFailed:
    async def test_marks_failed_and_increments_counter(self) -> None:
        from application.agent_monitoring.agent_service import record_run_failed

        run = _make_run()
        agent = _make_agent(failure_count=0)

        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=run)
            else:
                result.scalar_one_or_none = MagicMock(return_value=agent)
            call_count += 1
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        await record_run_failed("run-1", "agent-1", "DB timeout", session)

        assert run.run_status == "FAILED"
        assert run.error_message == "DB timeout"
        assert agent.failure_count == 1

    async def test_does_not_mark_global_agent_failed_after_org_failures(self) -> None:
        """F6: record_run_failed must never set agent.status='FAILED'.

        One org's consecutive failures must not disable monitoring for all orgs.
        Global agent status stays ACTIVE; per-org failures only log a warning.
        """
        from application.agent_monitoring.agent_service import record_run_failed

        run = _make_run()
        agent = _make_agent(failure_count=2)  # 3rd failure for this org
        original_status = agent.status  # "ACTIVE"

        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=run)
                result.scalars.return_value.all.return_value = []
            elif call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=agent)
                result.scalars.return_value.all.return_value = []
            else:
                # recent org run statuses query
                result.scalar_one_or_none = MagicMock(return_value=None)
                result.scalars.return_value.all.return_value = ["FAILED", "FAILED", "FAILED"]
            call_count += 1
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        await record_run_failed("run-1", "agent-1", "timeout", session)

        # F6: global agent status must NOT be set to FAILED
        assert agent.status != "FAILED", (
            "F6: global agent must never be auto-disabled by one org's failures"
        )
        assert agent.status == original_status

    async def test_exponential_backoff_on_failure(self) -> None:
        from application.agent_monitoring.agent_service import record_run_failed

        run = _make_run()
        agent = _make_agent(failure_count=0, run_interval_hours=24)

        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalar_one_or_none = MagicMock(return_value=run)
            else:
                result.scalar_one_or_none = MagicMock(return_value=agent)
            call_count += 1
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=_execute)
        session.flush = AsyncMock()

        before = datetime.now(UTC)
        await record_run_failed("run-1", "agent-1", "timeout", session)

        # next_run_at should be ~48 hours out (24*2), capped at 48h
        expected = before + timedelta(hours=48)
        assert agent.next_run_at is not None
        delta = abs((agent.next_run_at - expected).total_seconds())
        assert delta < 5  # within 5 seconds of expected


# ── Finding Service ────────────────────────────────────────────────────────────


class TestFindingService:
    async def test_create_finding_adds_to_session(self) -> None:
        from application.agent_monitoring.finding_service import create_finding

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        finding = await create_finding(
            organization_id="org-1",
            agent_id="agent-1",
            category="RISK",
            severity="HIGH",
            title="High risk score",
            description="Score exceeded 70",
            evidence="risk_score=78",
            rule_triggered="risk_score_high",
            source_data={"risk_score": 78},
            session=session,
        )

        # session.add called ≥1 times: once for AgentFindingModel + once for AuditEventModel
        assert session.add.call_count >= 1
        assert finding.finding_status == "OPEN"
        assert finding.severity == "HIGH"
        assert finding.organization_id == "org-1"

    async def test_acknowledge_finding_changes_status(self) -> None:
        from application.agent_monitoring.finding_service import acknowledge_finding

        finding = MagicMock()
        finding.id = "f-1"
        finding.finding_status = "OPEN"
        finding.organization_id = "org-1"

        session = _make_session(scalar_one_or_none=finding)

        result = await acknowledge_finding("f-1", "org-1", "user-1", session)

        assert result.finding_status == "ACKNOWLEDGED"
        assert result.acknowledged_by == "user-1"

    async def test_acknowledge_non_open_finding_raises(self) -> None:
        import pytest

        from application.agent_monitoring.finding_service import acknowledge_finding

        finding = MagicMock()
        finding.id = "f-1"
        finding.finding_status = "DISMISSED"
        finding.organization_id = "org-1"

        session = _make_session(scalar_one_or_none=finding)

        with pytest.raises(ValueError, match="Cannot acknowledge"):
            await acknowledge_finding("f-1", "org-1", "user-1", session)

    async def test_dismiss_finding_changes_status(self) -> None:
        from application.agent_monitoring.finding_service import dismiss_finding

        finding = MagicMock()
        finding.id = "f-1"
        finding.finding_status = "OPEN"
        finding.organization_id = "org-1"

        session = _make_session(scalar_one_or_none=finding)

        result = await dismiss_finding("f-1", "org-1", "user-1", session)
        assert result.finding_status == "DISMISSED"

    async def test_mark_converted_sets_status(self) -> None:
        from application.agent_monitoring.finding_service import mark_converted

        finding = MagicMock()
        finding.id = "f-1"
        finding.finding_status = "OPEN"
        finding.organization_id = "org-1"

        session = _make_session(scalar_one_or_none=finding)

        await mark_converted("f-1", "org-1", session)
        assert finding.finding_status == "CONVERTED"

    async def test_mark_converted_noop_when_not_found(self) -> None:
        from application.agent_monitoring.finding_service import mark_converted

        session = _make_session(scalar_one_or_none=None)
        # Should not raise
        await mark_converted("missing", "org-1", session)
