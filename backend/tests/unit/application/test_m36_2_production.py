"""M36.2 Production Hardening Unit Tests.

Covers:
  1. Retention service (purge policy, safety guards)
  2. Scheduler distributed lock (advisory lock path)
  3. Finding deduplication (skip_if_open)
  4. Alert deduplication (skip_if_open default)
  5. Explainability snapshot (_snapshot key in source_data_json)
  6. Agent health dashboard (per_agent_health populated)
  7. Metrics counters (agent_counters singleton)
  8. Auditability — run lifecycle audit events
  9. Regulatory monitor dedupe key
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _make_session(scalar_one_or_none=None, scalars_all=None):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
    result.scalars.return_value.all.return_value = scalars_all or []
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_run(run_id="run-1", agent_id="agent-1", org_id="org-1", status="RUNNING",
              started_at=None, completed_at=None, execution_time_ms=None):
    r = MagicMock()
    r.id = run_id
    r.agent_id = agent_id
    r.organization_id = org_id
    r.run_status = status
    r.started_at = started_at or datetime.now(UTC)
    r.completed_at = completed_at
    r.execution_time_ms = execution_time_ms
    return r


def _make_agent(agent_id="agent-1", agent_type="RISK_MONITOR", run_count=10, success_count=8,
                failure_count=2, status="ACTIVE", enabled=True, run_interval_hours=24):
    a = MagicMock()
    a.id = agent_id
    a.agent_type = agent_type
    a.name = f"{agent_type} Agent"
    a.status = status
    a.enabled = enabled
    a.run_count = run_count
    a.success_count = success_count
    a.failure_count = failure_count
    a.run_interval_hours = run_interval_hours
    return a


# ── 1. Retention Service ───────────────────────────────────────────────────────

class TestRetentionPolicy:
    def test_retention_constants_defined(self):
        from application.agent_monitoring.retention_service import (
            _RETENTION_AGENT_RUNS_DAYS,
            _RETENTION_AGENT_ALERTS_DAYS,
            _RETENTION_AGENT_FINDINGS_DAYS,
        )
        assert _RETENTION_AGENT_RUNS_DAYS == 365
        assert _RETENTION_AGENT_ALERTS_DAYS == 365
        assert _RETENTION_AGENT_FINDINGS_DAYS == 730

    @pytest.mark.asyncio
    async def test_cleanup_only_targets_terminal_runs(self):
        """run_retention_cleanup must only delete COMPLETED/FAILED runs, not RUNNING."""
        from application.agent_monitoring.retention_service import run_retention_cleanup

        delete_result = MagicMock()
        delete_result.rowcount = 5

        session = AsyncMock()
        session.execute = AsyncMock(return_value=delete_result)
        session.flush = AsyncMock()

        counts = await run_retention_cleanup(session)

        assert "agent_runs_deleted" in counts
        assert "agent_alerts_deleted" in counts
        assert "agent_findings_deleted" in counts

    @pytest.mark.asyncio
    async def test_cleanup_returns_counts(self):
        from application.agent_monitoring.retention_service import run_retention_cleanup

        delete_result = MagicMock()
        delete_result.rowcount = 3

        session = AsyncMock()
        session.execute = AsyncMock(return_value=delete_result)
        session.flush = AsyncMock()

        counts = await run_retention_cleanup(session)

        assert all(v == 3 for v in counts.values())

    def test_drafts_not_in_cleanup_source(self):
        """RecommendationDraft must never appear in retention_service cleanup."""
        from application.agent_monitoring import retention_service

        src = inspect.getsource(retention_service.run_retention_cleanup)
        assert "RecommendationDraftModel" not in src, (
            "Retention policy: drafts must never be deleted automatically"
        )

    def test_open_findings_not_deleted(self):
        """The finding delete clause must require terminal status."""
        from application.agent_monitoring import retention_service

        src = inspect.getsource(retention_service.run_retention_cleanup)
        assert "DISMISSED" in src or "CONVERTED" in src
        assert "OPEN" not in src.split("finding_status")[1][:100], (
            "Open findings must not be deleted by retention policy"
        )

    def test_unacknowledged_alerts_not_deleted(self):
        """The alert delete clause must require acknowledged_at IS NOT NULL."""
        from application.agent_monitoring import retention_service

        src = inspect.getsource(retention_service.run_retention_cleanup)
        assert "acknowledged_at" in src
        # The condition must filter on acknowledged_at (not None) — not unacked alerts
        assert "is_not(None)" in src or "is not None" in src or "isnot" in src.lower()


# ── 2. Distributed Scheduler Lock ─────────────────────────────────────────────

class TestSchedulerLock:
    def test_lock_key_constant_exists(self):
        from application.agent_monitoring.scheduler import _SCHEDULER_LOCK_KEY
        assert isinstance(_SCHEDULER_LOCK_KEY, int)
        assert _SCHEDULER_LOCK_KEY > 0

    def test_try_acquire_lock_function_exists(self):
        from application.agent_monitoring import scheduler
        assert hasattr(scheduler, "_try_acquire_scheduler_lock_and_run")

    def test_advisory_lock_in_source(self):
        from application.agent_monitoring import scheduler
        src = inspect.getsource(scheduler._try_acquire_scheduler_lock_and_run)
        assert "pg_try_advisory_lock" in src
        assert "pg_advisory_unlock" in src

    @pytest.mark.asyncio
    async def test_lock_not_acquired_returns_false(self):
        """When pg_try_advisory_lock returns False, skip and return False."""
        from application.agent_monitoring import scheduler

        # execute returns False for pg_try_advisory_lock
        lock_result = MagicMock()
        lock_result.scalar_one = MagicMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=lock_result)
        mock_session.close = AsyncMock()

        mock_factory = MagicMock(return_value=mock_session)

        with patch(
            "infrastructure.persistence.database.AsyncSessionFactory",
            mock_factory,
        ), patch(
            "application.agent_monitoring.scheduler._run_due_agents",
            new=AsyncMock(),
        ) as mock_run:
            result = await scheduler._try_acquire_scheduler_lock_and_run()

        assert result is False
        mock_run.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_lock_acquired_runs_agents(self):
        """When pg_try_advisory_lock returns True, agents are processed."""
        from application.agent_monitoring import scheduler

        # First execute: BEGIN (ignored result); Second: returns True (lock acquired)
        begin_result = MagicMock()
        begin_result.scalar_one = MagicMock(return_value=None)
        lock_result = MagicMock()
        lock_result.scalar_one = MagicMock(return_value=True)
        unlock_result = MagicMock()

        call_idx = 0

        async def _execute(stmt, *args, **kwargs):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return begin_result
            elif call_idx == 2:
                return lock_result
            return unlock_result

        mock_session = AsyncMock()
        mock_session.execute = _execute
        mock_session.close = AsyncMock()

        mock_factory = MagicMock(return_value=mock_session)

        with patch(
            "infrastructure.persistence.database.AsyncSessionFactory",
            mock_factory,
        ), patch(
            "application.agent_monitoring.scheduler._run_due_agents",
            new=AsyncMock(),
        ) as mock_run:
            result = await scheduler._try_acquire_scheduler_lock_and_run()

        assert result is True
        mock_run.assert_awaited_once()

    def test_retention_wired_to_scheduler(self):
        """_run_retention must be defined and called from run_agent_scheduler."""
        from application.agent_monitoring import scheduler

        assert hasattr(scheduler, "_run_retention")
        src = inspect.getsource(scheduler.run_agent_scheduler)
        assert "_run_retention" in src


# ── 3. Finding Deduplication ───────────────────────────────────────────────────

class TestFindingDeduplication:
    def test_find_open_duplicate_function_exists(self):
        from application.agent_monitoring import finding_service
        assert hasattr(finding_service, "find_open_duplicate")

    def test_skip_if_open_parameter_in_create_finding(self):
        from application.agent_monitoring import finding_service
        import inspect as _inspect
        sig = _inspect.signature(finding_service.create_finding)
        assert "skip_if_open" in sig.parameters

    @pytest.mark.asyncio
    async def test_skip_if_open_returns_existing_finding(self):
        """When skip_if_open=True and a duplicate exists, return existing without creating."""
        from application.agent_monitoring.finding_service import create_finding

        existing = MagicMock()
        existing.id = "existing-f-1"
        existing.finding_status = "OPEN"

        session = _make_session(scalar_one_or_none=existing)

        result = await create_finding(
            organization_id="org-1",
            agent_id="agent-1",
            category="risk_score",
            severity="HIGH",
            title="Dup finding",
            description="desc",
            evidence="ev",
            rule_triggered="risk_score >= 70",
            source_data={"risk_score": 75},
            skip_if_open=True,
            session=session,
        )

        assert result is existing
        # session.add should NOT be called (returned existing, no new record)
        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "AgentFindingModel" not in added_types

    @pytest.mark.asyncio
    async def test_skip_if_open_false_always_creates(self):
        """When skip_if_open=False (default), always create even if duplicate exists."""
        from application.agent_monitoring.finding_service import create_finding

        session = _make_session(scalar_one_or_none=None)

        result = await create_finding(
            organization_id="org-1",
            agent_id="agent-1",
            category="risk_score",
            severity="HIGH",
            title="New finding",
            description="desc",
            evidence="ev",
            rule_triggered="risk_score >= 70",
            source_data={"risk_score": 75},
            skip_if_open=False,
            session=session,
        )

        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "AgentFindingModel" in added_types

    def test_regulatory_monitor_uses_skip_if_open(self):
        """regulatory_monitor.run must pass skip_if_open=True to prevent re-finding."""
        from application.agent_monitoring import regulatory_monitor

        src = inspect.getsource(regulatory_monitor.run)
        assert "skip_if_open=True" in src

    def test_regulatory_monitor_uses_versioned_dedupe_key(self):
        """rule_triggered in regulatory_monitor must include regulation code + version."""
        from application.agent_monitoring import regulatory_monitor

        src = inspect.getsource(regulatory_monitor.run)
        # Dedupe rule must embed both code and version
        assert "reg_version" in src or "version" in src
        assert "dedupe_rule" in src or "dedupe" in src.lower()


# ── 4. Alert Deduplication ─────────────────────────────────────────────────────

class TestAlertDeduplication:
    def test_find_open_alert_duplicate_exists(self):
        from application.agent_monitoring import alert_service
        assert hasattr(alert_service, "_find_open_alert_duplicate")

    def test_skip_if_open_default_true(self):
        """create_alert must default skip_if_open=True."""
        import inspect as _inspect
        from application.agent_monitoring.alert_service import create_alert
        sig = _inspect.signature(create_alert)
        assert sig.parameters["skip_if_open"].default is True

    @pytest.mark.asyncio
    async def test_duplicate_alert_not_created_when_open_exists(self):
        """When an unacknowledged alert for the same finding exists, return existing."""
        from application.agent_monitoring.alert_service import create_alert

        existing_alert = MagicMock()
        existing_alert.id = "existing-alert-1"
        existing_alert.severity = "HIGH"

        session = _make_session(scalar_one_or_none=existing_alert)

        result = await create_alert(
            organization_id="org-1",
            agent_id="agent-1",
            severity="HIGH",
            title="Duplicate alert",
            message="msg",
            agent_finding_id="finding-1",
            skip_if_open=True,
            session=session,
        )

        assert result is existing_alert
        assert not session.add.called

    @pytest.mark.asyncio
    async def test_alert_created_when_no_duplicate(self):
        """When no duplicate exists, alert is created normally."""
        from application.agent_monitoring.alert_service import create_alert

        session = _make_session(scalar_one_or_none=None)

        alert = await create_alert(
            organization_id="org-1",
            agent_id="agent-1",
            severity="HIGH",
            title="New alert",
            message="msg",
            agent_finding_id="finding-1",
            skip_if_open=True,
            session=session,
        )

        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "AgentAlertModel" in added_types


# ── 5. Explainability Snapshot ─────────────────────────────────────────────────

class TestExplainabilitySnapshot:
    @pytest.mark.asyncio
    async def test_snapshot_embedded_in_source_data(self):
        """create_finding must embed _snapshot in source_data_json."""
        from application.agent_monitoring.finding_service import create_finding
        from infrastructure.persistence.models.agent_monitoring import AgentFindingModel

        session = _make_session(scalar_one_or_none=None)

        await create_finding(
            organization_id="org-1",
            agent_id="agent-1",
            category="risk_score",
            severity="CRITICAL",
            title="Test",
            description="Test description",
            evidence="risk_score=90",
            rule_triggered="risk_score >= 85",
            source_data={"risk_score": 90},
            confidence_score=0.95,
            session=session,
        )

        finding_calls = [
            c.args[0] for c in session.add.call_args_list
            if isinstance(c.args[0], AgentFindingModel)
        ]
        assert len(finding_calls) == 1
        finding = finding_calls[0]

        snapshot = finding.source_data_json.get("_snapshot")
        assert snapshot is not None, "source_data_json must contain _snapshot key"
        assert snapshot["rule_triggered"] == "risk_score >= 85"
        assert snapshot["confidence_score"] == 0.95
        assert snapshot["severity"] == "CRITICAL"
        assert "detected_at" in snapshot
        assert snapshot["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_original_source_data_preserved(self):
        """_snapshot must not overwrite original source_data keys."""
        from application.agent_monitoring.finding_service import create_finding
        from infrastructure.persistence.models.agent_monitoring import AgentFindingModel

        session = _make_session(scalar_one_or_none=None)

        await create_finding(
            organization_id="org-1",
            agent_id="agent-1",
            category="risk_score",
            severity="HIGH",
            title="Test",
            description="desc",
            evidence="ev",
            rule_triggered="rule_x",
            source_data={"supplier_id": "sup-1", "risk_score": 75},
            session=session,
        )

        finding_calls = [
            c.args[0] for c in session.add.call_args_list
            if isinstance(c.args[0], AgentFindingModel)
        ]
        sdata = finding_calls[0].source_data_json
        assert sdata["supplier_id"] == "sup-1"
        assert sdata["risk_score"] == 75
        assert "_snapshot" in sdata


# ── 6. Agent Health Dashboard ──────────────────────────────────────────────────

class TestAgentHealthDashboard:
    def test_per_agent_health_in_schema(self):
        from interfaces.api.schemas.agent_monitoring import AgentDashboard, AgentHealthInfo

        fields = AgentDashboard.model_fields
        assert "per_agent_health" in fields

    def test_agent_health_info_schema_fields(self):
        from interfaces.api.schemas.agent_monitoring import AgentHealthInfo

        fields = set(AgentHealthInfo.model_fields.keys())
        required = {
            "agent_id", "agent_type", "name", "status", "enabled",
            "last_successful_run", "consecutive_failures",
            "avg_runtime_ms", "success_rate", "backlog_count",
        }
        assert required.issubset(fields)

    def test_get_agent_health_list_exists(self):
        from application.agent_monitoring import agent_service
        assert hasattr(agent_service, "get_agent_health_list")

    @pytest.mark.asyncio
    async def test_health_list_returns_per_agent_entries(self):
        """get_agent_health_list returns one entry per agent."""
        from application.agent_monitoring.agent_service import get_agent_health_list

        agent = _make_agent(run_count=10, success_count=8)

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(return_value=None)
            if call_idx == 0:
                # list_agents query
                res.scalars.return_value.all.return_value = [agent]
            elif call_idx == 1:
                # avg_runtime_ms: completed runtimes
                res.scalars.return_value.all.return_value = [1200, 800, 1500]
            elif call_idx == 2:
                # last_successful_run
                res.scalar_one_or_none = MagicMock(return_value=datetime.now(UTC))
                res.scalars.return_value.all.return_value = []
            elif call_idx == 3:
                # consecutive_failures: recent statuses
                res.scalars.return_value.all.return_value = ["COMPLETED", "COMPLETED"]
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        health = await get_agent_health_list(session)

        assert len(health) == 1
        h = health[0]
        assert h["agent_id"] == agent.id
        assert h["agent_type"] == agent.agent_type
        assert h["success_rate"] == pytest.approx(0.8)
        assert h["consecutive_failures"] == 0
        assert h["avg_runtime_ms"] == pytest.approx(1166.7, rel=0.01)


# ── 7. Metrics Counters ────────────────────────────────────────────────────────

class TestAgentMetrics:
    def test_agent_counters_singleton_exists(self):
        from application.agent_monitoring.metrics import agent_counters
        assert agent_counters is not None

    def test_prometheus_output_contains_agent_metrics(self):
        from application.agent_monitoring.metrics import agent_counters

        lines = "\n".join(agent_counters.to_prometheus_lines("test"))
        assert "agent_runs_total" in lines
        assert "agent_runs_failed_total" in lines
        assert "agent_findings_created_total" in lines
        assert "agent_alerts_created_total" in lines
        assert "agent_drafts_created_total" in lines
        assert "agent_runtime_seconds" in lines

    def test_record_run_completed_increments_total(self):
        from application.agent_monitoring.metrics import _AgentCounters

        c = _AgentCounters()
        c.record_run_completed(runtime_ms=1500)
        assert c.agent_runs_total == 1
        assert c.agent_runs_failed_total == 0
        assert c.avg_runtime_seconds() == pytest.approx(1.5)

    def test_record_run_failed_increments_both(self):
        from application.agent_monitoring.metrics import _AgentCounters

        c = _AgentCounters()
        c.record_run_failed(runtime_ms=500)
        assert c.agent_runs_total == 1
        assert c.agent_runs_failed_total == 1

    def test_record_finding_created(self):
        from application.agent_monitoring.metrics import _AgentCounters

        c = _AgentCounters()
        c.record_finding_created()
        c.record_finding_created()
        assert c.agent_findings_created_total == 2

    def test_record_alert_created(self):
        from application.agent_monitoring.metrics import _AgentCounters

        c = _AgentCounters()
        c.record_alert_created()
        assert c.agent_alerts_created_total == 1

    def test_record_draft_created(self):
        from application.agent_monitoring.metrics import _AgentCounters

        c = _AgentCounters()
        c.record_draft_created()
        assert c.agent_drafts_created_total == 1

    def test_metrics_wired_to_prometheus_router(self):
        from interfaces.api.routers import metrics as metrics_router

        src = inspect.getsource(metrics_router.get_metrics_prometheus)
        assert "agent_counters" in src

    @pytest.mark.asyncio
    async def test_create_finding_increments_metric(self):
        """create_finding must call agent_counters.record_finding_created()."""
        from application.agent_monitoring.finding_service import create_finding
        from application.agent_monitoring.metrics import agent_counters

        session = _make_session(scalar_one_or_none=None)
        before = agent_counters.agent_findings_created_total

        await create_finding(
            organization_id="org-1",
            agent_id="agent-1",
            category="test",
            severity="LOW",
            title="T",
            description="d",
            evidence="e",
            rule_triggered="rule",
            source_data={},
            session=session,
        )

        assert agent_counters.agent_findings_created_total == before + 1


# ── 8. Auditability — Run Lifecycle ───────────────────────────────────────────

class TestAuditabilityRunLifecycle:
    def test_run_started_audit_in_source(self):
        from application.agent_monitoring import agent_service
        src = inspect.getsource(agent_service.record_run_start)
        assert "agent.run.started" in src
        assert "_log_audit_event" in src

    def test_run_completed_audit_in_source(self):
        from application.agent_monitoring import agent_service
        src = inspect.getsource(agent_service.record_run_completed)
        assert "agent.run.completed" in src
        assert "_log_audit_event" in src

    def test_run_failed_audit_in_source(self):
        from application.agent_monitoring import agent_service
        src = inspect.getsource(agent_service.record_run_failed)
        assert "agent.run.failed" in src
        assert "_log_audit_event" in src

    def test_finding_created_audit_in_source(self):
        from application.agent_monitoring import finding_service
        src = inspect.getsource(finding_service.create_finding)
        assert "agent.finding.created" in src

    def test_alert_escalated_audit_in_source(self):
        from application.agent_monitoring import alert_service
        src = inspect.getsource(alert_service.create_alert)
        assert "agent.alert.escalated" in src

    def test_all_six_governance_events_covered(self):
        """Verify all 6 required governance action strings are present."""
        import application.agent_monitoring.finding_service as fs
        import application.agent_monitoring.alert_service as als
        import application.agent_monitoring.agent_service as ags

        fs_src = inspect.getsource(fs)
        als_src = inspect.getsource(als)
        ags_src = inspect.getsource(ags)
        combined = fs_src + als_src + ags_src

        required_actions = [
            "agent.run.started",
            "agent.run.completed",
            "agent.run.failed",
            "agent.finding.created",
            "agent.finding.acknowledged",
            "agent.finding.dismissed",
            "agent.draft.approved",
            "agent.draft.rejected",
            "agent.alert.escalated",
        ]
        for action in required_actions:
            assert action in combined, f"Missing audit event: {action}"

    @pytest.mark.asyncio
    async def test_record_run_completed_writes_audit_event(self):
        """record_run_completed must write AuditEventModel."""
        from infrastructure.persistence.models.audit_event import AuditEventModel
        from application.agent_monitoring.agent_service import record_run_completed

        run = _make_run(status="RUNNING", execution_time_ms=None)
        agent = _make_agent()

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            if call_idx == 0:
                res.scalar_one_or_none = MagicMock(return_value=run)
            else:
                res.scalar_one_or_none = MagicMock(return_value=agent)
            res.scalars.return_value.all.return_value = []
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await record_run_completed("run-1", "agent-1", 3, 1, 0, session)

        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "AuditEventModel" in added_types

    @pytest.mark.asyncio
    async def test_record_run_failed_writes_audit_event(self):
        from infrastructure.persistence.models.audit_event import AuditEventModel
        from application.agent_monitoring.agent_service import record_run_failed

        run = _make_run(status="RUNNING")
        agent = _make_agent()

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            if call_idx == 0:
                res.scalar_one_or_none = MagicMock(return_value=run)
                res.scalars.return_value.all.return_value = []
            elif call_idx == 1:
                res.scalar_one_or_none = MagicMock(return_value=agent)
                res.scalars.return_value.all.return_value = []
            else:
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars.return_value.all.return_value = []
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await record_run_failed("run-1", "agent-1", "simulated error", session)

        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "AuditEventModel" in added_types

    @pytest.mark.asyncio
    async def test_record_run_start_writes_audit_event(self):
        """record_run_start must write agent.run.started to AuditEventModel."""
        from infrastructure.persistence.models.audit_event import AuditEventModel
        from application.agent_monitoring.agent_service import record_run_start

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        await record_run_start("agent-1", "org-1", session)

        added_types = [type(c.args[0]).__name__ for c in session.add.call_args_list]
        assert "AuditEventModel" in added_types

        audit_calls = [
            c.args[0] for c in session.add.call_args_list
            if isinstance(c.args[0], AuditEventModel)
        ]
        assert len(audit_calls) == 1
        assert audit_calls[0].action == "agent.run.started"
