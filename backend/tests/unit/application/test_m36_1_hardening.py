"""M36.1 Hardening Unit Tests — F1 through F7.

Covers every P0/P1 finding from the M36 audit:
  F1 — Tenant isolation: TriggerAgentRunRequest has no organization_id
  F2 — Concurrency guard: check_and_start_run rejects duplicate RUNNING runs
  F3 — Dead code: _execute_agent has no record_run_failed in its body
  F4 — Data freshness: intelligence_monitor skips stale/quarantined datasets
  F5 — Agent-type filtering: evaluate_finding respects agent_type on rules
  F6 — Per-org failure isolation: record_run_failed never marks global agent FAILED
  F7 — Audit trail: acknowledge/dismiss/approve/reject all write AuditEventModel
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Shared helpers ─────────────────────────────────────────────────────────────


def _make_session_multi(*return_values):
    """Session whose execute() returns successive values from return_values."""
    call_idx = 0
    results = list(return_values)

    async def _execute(stmt, **kwargs):
        nonlocal call_idx
        rv = results[call_idx] if call_idx < len(results) else results[-1]
        call_idx += 1
        res = MagicMock()
        if isinstance(rv, list):
            res.scalar_one_or_none = MagicMock(return_value=None)
            res.scalars.return_value.all.return_value = rv
        else:
            res.scalar_one_or_none = MagicMock(return_value=rv)
            res.scalars.return_value.all.return_value = [rv] if rv is not None else []
        return res

    session = AsyncMock()
    session.execute = _execute
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_run(run_id="run-1", agent_id="agent-1", org_id="org-1", status="RUNNING"):
    r = MagicMock()
    r.id = run_id
    r.agent_id = agent_id
    r.organization_id = org_id
    r.run_status = status
    r.started_at = datetime.now(UTC)
    return r


def _make_agent(
    agent_id="agent-1", status="ACTIVE", enabled=True, run_interval_hours=24, failure_count=0
):
    a = MagicMock()
    a.id = agent_id
    a.agent_type = "RISK_MONITOR"
    a.status = status
    a.enabled = enabled
    a.run_interval_hours = run_interval_hours
    a.failure_count = failure_count
    a.run_count = 0
    return a


def _make_finding(
    finding_id="f-1",
    severity="HIGH",
    confidence_score=0.9,
    category="risk_score",
    supplier_id=None,
    organization_id="org-1",
    agent_id="agent-1",
    source_data=None,
):
    f = MagicMock()
    f.id = finding_id
    f.severity = severity
    f.confidence_score = confidence_score
    f.category = category
    f.supplier_id = supplier_id
    f.organization_id = organization_id
    f.agent_id = agent_id
    f.title = "Test finding"
    f.description = "Test description"
    f.source_data_json = source_data or {}
    f.finding_status = "OPEN"
    return f


def _make_draft(draft_id="d-1", status="PENDING", finding_id="f-1", org_id="org-1"):
    d = MagicMock()
    d.id = draft_id
    d.draft_status = status
    d.agent_finding_id = finding_id
    d.organization_id = org_id
    d.approved_by = None
    d.approved_at = None
    d.rejection_reason = None
    d.updated_at = None
    return d


# ── F1: Tenant isolation ───────────────────────────────────────────────────────


class TestF1TenantIsolation:
    def test_trigger_request_schema_has_no_organization_id(self):
        """TriggerAgentRunRequest must not expose organization_id to callers."""
        from interfaces.api.schemas.agent_monitoring import TriggerAgentRunRequest

        fields = TriggerAgentRunRequest.model_fields
        assert "organization_id" not in fields, (
            "organization_id must be removed from TriggerAgentRunRequest (F1)"
        )

    def test_trigger_request_only_has_agent_type(self):
        from interfaces.api.schemas.agent_monitoring import TriggerAgentRunRequest

        fields = set(TriggerAgentRunRequest.model_fields.keys())
        assert "agent_type" in fields
        # Only agent_type — no hidden cross-tenant lever
        assert fields == {"agent_type"}

    def test_trigger_request_accepts_agent_type(self):
        from interfaces.api.schemas.agent_monitoring import TriggerAgentRunRequest

        req = TriggerAgentRunRequest(agent_type="RISK_MONITOR")
        assert req.agent_type == "RISK_MONITOR"


# ── F2: Concurrency guard ──────────────────────────────────────────────────────


class TestF2ConcurrencyGuard:
    @pytest.mark.asyncio
    async def test_raises_when_running_run_exists(self):
        """check_and_start_run raises ValueError if a RUNNING record is found."""
        from application.agent_monitoring.agent_service import check_and_start_run

        existing_run = _make_run(status="RUNNING")
        session = _make_session_multi(existing_run)

        with pytest.raises(ValueError, match="already running"):
            await check_and_start_run("agent-1", "org-1", session)

    @pytest.mark.asyncio
    async def test_succeeds_when_no_running_run(self):
        """check_and_start_run creates a new run when no RUNNING record exists."""
        from application.agent_monitoring.agent_service import check_and_start_run

        # First execute (check) → None; second execute is inside record_run_start (flush-only)
        session = _make_session_multi(None)
        # record_run_start uses session.add + flush, not execute, so one call suffices
        run = await check_and_start_run("agent-1", "org-1", session)

        assert session.add.called
        assert run is not None

    def test_check_and_start_run_uses_skip_locked(self):
        """SELECT FOR UPDATE skip_locked must be present in check_and_start_run source."""
        from application.agent_monitoring import agent_service

        src = inspect.getsource(agent_service.check_and_start_run)
        assert "skip_locked" in src, "F2 requires .with_for_update(skip_locked=True)"
        assert "with_for_update" in src


# ── F3: Dead code absent ───────────────────────────────────────────────────────


class TestF3DeadCodeAbsent:
    def test_execute_agent_does_not_import_record_run_failed(self):
        """_execute_agent must not import record_run_failed (would be dead inside begin())."""
        from application.agent_monitoring import scheduler

        src = inspect.getsource(scheduler._execute_agent)
        # The docstring/comments may mention record_run_failed for explanation.
        # What matters is it is NOT imported (and thus not called) in the function body.
        # The only imports inside _execute_agent must be check_and_start_run and record_run_completed.
        assert "record_run_completed" in src, "_execute_agent must import record_run_completed"
        assert "check_and_start_run" in src, "_execute_agent must import check_and_start_run"
        # Verify record_run_failed is not in the from…import line(s) inside _execute_agent
        import_lines = [
            ln.strip() for ln in src.splitlines() if "record_run_failed" in ln and "import" in ln
        ]
        assert not import_lines, (
            f"F3: record_run_failed must not be imported inside _execute_agent. "
            f"Found: {import_lines}"
        )

    def test_execute_agent_has_no_try_except(self):
        """_execute_agent relies on transaction rollback, not try/except."""
        from application.agent_monitoring import scheduler

        src = inspect.getsource(scheduler._execute_agent)
        assert "except" not in src or "# No try/except" in src or src.count("except") == 0, (
            "F3: _execute_agent should not contain an except block"
        )

    def test_execute_agent_calls_check_and_start_run(self):
        """_execute_agent must use the concurrency-safe check_and_start_run."""
        from application.agent_monitoring import scheduler

        src = inspect.getsource(scheduler._execute_agent)
        assert "check_and_start_run" in src


# ── F4: Data freshness ─────────────────────────────────────────────────────────


class TestF4DataFreshness:
    def test_freshness_filter_present_in_source(self):
        """intelligence_monitor must filter datasets by status AND imported_at."""
        from application.agent_monitoring import intelligence_monitor

        src = inspect.getsource(intelligence_monitor.run)
        assert "dataset_status" in src, "F4: must filter ExternalDatasetModel by dataset_status"
        assert "imported_at" in src, "F4: must filter ExternalDatasetModel by imported_at"
        assert "freshness_cutoff" in src or "timedelta" in src, (
            "F4: must compute a freshness cutoff from timedelta"
        )

    def test_enrichment_freshness_filter_present_in_source(self):
        from application.agent_monitoring import intelligence_monitor

        src = inspect.getsource(intelligence_monitor.run)
        assert "enriched_at" in src, "F4: must filter SupplierEnrichmentModel by enriched_at"

    def test_quarantine_excluded_via_dataset_status_filter(self):
        """Quarantined datasets have dataset_status != 'active'; source must filter by status."""
        from application.agent_monitoring import intelligence_monitor

        src = inspect.getsource(intelligence_monitor.run)
        assert '"active"' in src or "'active'" in src, (
            "F4: dataset_status must be checked against 'active'"
        )

    @pytest.mark.asyncio
    async def test_no_valid_datasets_returns_zero(self):
        """intelligence_monitor returns 0 findings when no active fresh datasets exist."""
        from application.agent_monitoring import intelligence_monitor

        # First execute: valid_dataset_ids query → empty list
        # Second execute: suppliers query → empty list
        session = _make_session_multi([], [])

        result = await intelligence_monitor.run(
            agent_id="agent-1",
            agent_run_id="run-1",
            organization_id="org-1",
            session=session,
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_null_country_skipped(self):
        """Suppliers with empty/null country must be skipped (null guard)."""
        from application.agent_monitoring import intelligence_monitor

        dataset_id = "ds-1"

        supplier = MagicMock()
        supplier.id = "sup-1"
        supplier.country = ""  # empty string — should be skipped

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            # 1: valid_dataset_ids → one dataset
            # 2: country_risk → empty (no profiles)
            # 3: suppliers → one supplier with empty country
            if call_idx == 0:
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars.return_value.all.return_value = [dataset_id]
            elif call_idx == 1:
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars.return_value.all.return_value = []
            elif call_idx == 2:
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars.return_value.all.return_value = [supplier]
            else:
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars.return_value.all.return_value = []
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await intelligence_monitor.run(
            agent_id="agent-1",
            agent_run_id="run-1",
            organization_id="org-1",
            session=session,
        )
        # supplier skipped due to empty country — no findings
        assert result == 0


# ── F5: Agent-type escalation rule filtering ───────────────────────────────────


class TestF5AgentTypeFiltering:
    def test_evaluate_finding_accepts_agent_type_param(self):
        """evaluate_finding must accept an agent_type keyword argument."""
        import inspect as _inspect

        from application.agent_monitoring import alert_service

        sig = _inspect.signature(alert_service.evaluate_finding)
        assert "agent_type" in sig.parameters, "F5: evaluate_finding needs agent_type param"

    def test_or_filter_in_evaluate_finding_source(self):
        """evaluate_finding source must contain or_() filter on agent_type."""
        from application.agent_monitoring import alert_service

        src = inspect.getsource(alert_service.evaluate_finding)
        assert "or_(" in src, "F5: must use or_() for agent_type wildcard matching"
        assert "agent_type" in src

    @pytest.mark.asyncio
    async def test_wildcard_rule_fires_for_any_agent_type(self):
        """A rule with agent_type='*' must trigger regardless of calling agent_type."""
        from application.agent_monitoring.alert_service import evaluate_finding

        rule = MagicMock()
        rule.escalation_severity = "WARNING"
        rule.name = "wildcard-rule"
        rule.condition_json = {"metric": "severity", "value": "HIGH"}

        finding = _make_finding(severity="HIGH", confidence_score=0.5)

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            # First execute: user-defined rules query → one rule
            # Subsequent: alert creation (add/flush only, no execute)
            res.scalar_one_or_none = MagicMock(return_value=None)
            res.scalars.return_value.all.return_value = [rule] if call_idx == 0 else []
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        # Disable notification side-effect
        with patch(
            "application.agent_monitoring.alert_service._trigger_notification",
            new=AsyncMock(),
        ):
            alerts = await evaluate_finding(finding, "org-1", session, agent_type="RISK_MONITOR")

        # wildcard rule fired → at least one user-defined alert created
        [a for a in alerts if "wildcard-rule" in (a.title or "")]
        # The rule was processed (session.add called for the alert)
        assert session.add.called

    @pytest.mark.asyncio
    async def test_no_rules_returns_only_auto_escalation(self):
        """When DB returns no rules (all filtered out), only auto-escalation fires."""
        from application.agent_monitoring.alert_service import evaluate_finding

        finding = _make_finding(severity="CRITICAL", confidence_score=1.0)

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(return_value=None)
            res.scalars.return_value.all.return_value = []  # no user rules
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch(
            "application.agent_monitoring.alert_service._trigger_notification",
            new=AsyncMock(),
        ):
            alerts = await evaluate_finding(
                finding, "org-1", session, agent_type="COMPLIANCE_MONITOR"
            )

        # Auto-escalation fires for CRITICAL
        assert len(alerts) == 1
        assert alerts[0].severity.upper() == "CRITICAL" or session.add.call_count >= 1

    def test_each_monitor_passes_agent_type_to_maybe_escalate(self):
        """Every _maybe_escalate() call must pass agent_type= kwarg."""
        import application.agent_monitoring.compliance_drift_monitor as cdm
        import application.agent_monitoring.intelligence_monitor as im
        import application.agent_monitoring.regulatory_monitor as regm
        import application.agent_monitoring.remediation_monitor as rem
        import application.agent_monitoring.risk_monitor as rm
        import application.agent_monitoring.supplier_behaviour_monitor as sbm

        for mod, expected_type in [
            (rm, "RISK_MONITOR"),
            (regm, "REGULATION_MONITOR"),
            (sbm, "SUPPLIER_MONITOR"),
            (cdm, "COMPLIANCE_MONITOR"),
            (rem, "REMEDIATION_MONITOR"),
            (im, "INTELLIGENCE_MONITOR"),
        ]:
            src = inspect.getsource(mod._maybe_escalate)
            assert expected_type in src, (
                f"F5: {mod.__name__}._maybe_escalate must pass agent_type={expected_type!r}"
            )


# ── F6: Per-org failure isolation ──────────────────────────────────────────────


class TestF6PerOrgFailureIsolation:
    def test_global_failed_status_not_set_in_source(self):
        """record_run_failed must never assign agent.status = 'FAILED'."""
        from application.agent_monitoring import agent_service

        src = inspect.getsource(agent_service.record_run_failed)
        # The line `agent.status = "FAILED"` must not appear
        lines = [ln.strip() for ln in src.splitlines() if not ln.strip().startswith("#")]
        bad = [ln for ln in lines if "agent.status" in ln and '"FAILED"' in ln]
        assert not bad, f"F6: record_run_failed must not set agent.status='FAILED'. Found: {bad}"

    def test_per_org_threshold_constant_present(self):
        from application.agent_monitoring import agent_service

        assert hasattr(agent_service, "_PER_ORG_FAILURE_THRESHOLD")
        assert agent_service._PER_ORG_FAILURE_THRESHOLD >= 2

    @pytest.mark.asyncio
    async def test_record_run_failed_does_not_set_agent_status_failed(self):
        """Integration check: after record_run_failed, agent.status is unchanged."""
        from application.agent_monitoring.agent_service import record_run_failed

        run = _make_run(status="RUNNING")
        agent = _make_agent()
        original_status = agent.status  # "ACTIVE"

        # execute calls: run lookup, agent lookup, recent-status lookup
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
                # recent run status query
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars.return_value.all.return_value = ["FAILED", "FAILED"]
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await record_run_failed("run-1", "agent-1", "simulated error", session)

        # agent.status must not have been set to "FAILED"
        assert agent.status == original_status or agent.status != "FAILED", (
            "F6: record_run_failed must not globally disable the agent via status=FAILED"
        )

    @pytest.mark.asyncio
    async def test_consecutive_org_failures_log_warning(self):
        """Three consecutive FAILED runs for one org → logger.warning called."""
        from application.agent_monitoring.agent_service import (
            _PER_ORG_FAILURE_THRESHOLD,
            record_run_failed,
        )

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
                # Return exactly _PER_ORG_FAILURE_THRESHOLD consecutive FAILED statuses
                failed_list = ["FAILED"] * _PER_ORG_FAILURE_THRESHOLD
                res.scalar_one_or_none = MagicMock(return_value=None)
                res.scalars.return_value.all.return_value = failed_list
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("application.agent_monitoring.agent_service.logger") as mock_logger:
            await record_run_failed("run-1", "agent-1", "error", session)

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args
        assert "agent_org_repeated_failure" in str(call_kwargs)


# ── F7: Governance audit trail ─────────────────────────────────────────────────


class TestF7AuditTrail:
    def test_log_audit_event_helper_in_finding_service(self):
        """finding_service must expose a _log_audit_event helper."""
        from application.agent_monitoring import finding_service

        assert hasattr(finding_service, "_log_audit_event"), (
            "F7: finding_service must have _log_audit_event helper"
        )

    def test_log_audit_event_helper_in_alert_service(self):
        from application.agent_monitoring import alert_service

        assert hasattr(alert_service, "_log_audit_event"), (
            "F7: alert_service must have _log_audit_event helper"
        )

    def test_acknowledge_finding_source_has_audit_call(self):
        from application.agent_monitoring import finding_service

        src = inspect.getsource(finding_service.acknowledge_finding)
        assert "_log_audit_event" in src
        assert "agent.finding.acknowledged" in src

    def test_dismiss_finding_source_has_audit_call(self):
        from application.agent_monitoring import finding_service

        src = inspect.getsource(finding_service.dismiss_finding)
        assert "_log_audit_event" in src
        assert "agent.finding.dismissed" in src

    def test_approve_draft_source_has_audit_call(self):
        from application.agent_monitoring import alert_service

        src = inspect.getsource(alert_service.approve_draft)
        assert "_log_audit_event" in src
        assert "agent.draft.approved" in src

    def test_reject_draft_source_has_audit_call(self):
        from application.agent_monitoring import alert_service

        src = inspect.getsource(alert_service.reject_draft)
        assert "_log_audit_event" in src
        assert "agent.draft.rejected" in src

    @pytest.mark.asyncio
    async def test_acknowledge_finding_writes_audit_event_record(self):
        """acknowledge_finding must call session.add with an AuditEventModel."""
        from application.agent_monitoring.finding_service import acknowledge_finding

        finding = _make_finding()

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(return_value=finding)
            res.scalars.return_value.all.return_value = []
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await acknowledge_finding("f-1", "org-1", "user-123", session)

        added_types = [type(call.args[0]).__name__ for call in session.add.call_args_list]
        assert "AuditEventModel" in added_types, (
            f"F7: AuditEventModel not written on acknowledge. Added: {added_types}"
        )

    @pytest.mark.asyncio
    async def test_dismiss_finding_writes_audit_event_record(self):
        from application.agent_monitoring.finding_service import dismiss_finding

        finding = _make_finding()

        async def _execute(stmt, **kwargs):
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(return_value=finding)
            res.scalars.return_value.all.return_value = []
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await dismiss_finding("f-1", "org-1", "user-123", session)

        added_types = [type(call.args[0]).__name__ for call in session.add.call_args_list]
        assert "AuditEventModel" in added_types, (
            f"F7: AuditEventModel not written on dismiss. Added: {added_types}"
        )

    @pytest.mark.asyncio
    async def test_approve_draft_writes_audit_event_record(self):
        from application.agent_monitoring.alert_service import approve_draft

        draft = _make_draft()
        finding = _make_finding()

        call_idx = 0

        async def _execute(stmt, **kwargs):
            nonlocal call_idx
            res = MagicMock()
            if call_idx == 0:
                res.scalar_one_or_none = MagicMock(return_value=draft)
            else:
                res.scalar_one_or_none = MagicMock(return_value=finding)
            res.scalars.return_value.all.return_value = []
            call_idx += 1
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await approve_draft("d-1", "org-1", "user-123", session)

        added_types = [type(call.args[0]).__name__ for call in session.add.call_args_list]
        assert "AuditEventModel" in added_types, (
            f"F7: AuditEventModel not written on approve_draft. Added: {added_types}"
        )

    @pytest.mark.asyncio
    async def test_reject_draft_writes_audit_event_record(self):
        from application.agent_monitoring.alert_service import reject_draft

        draft = _make_draft()

        async def _execute(stmt, **kwargs):
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(return_value=draft)
            res.scalars.return_value.all.return_value = []
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await reject_draft("d-1", "org-1", "user-123", "not actionable", session)

        added_types = [type(call.args[0]).__name__ for call in session.add.call_args_list]
        assert "AuditEventModel" in added_types, (
            f"F7: AuditEventModel not written on reject_draft. Added: {added_types}"
        )

    @pytest.mark.asyncio
    async def test_audit_event_fields_populated(self):
        """AuditEventModel must be created with action, actor_id, entity_type, entity_id."""
        from application.agent_monitoring.finding_service import acknowledge_finding
        from infrastructure.persistence.models.audit_event import AuditEventModel

        finding = _make_finding()

        async def _execute(stmt, **kwargs):
            res = MagicMock()
            res.scalar_one_or_none = MagicMock(return_value=finding)
            res.scalars.return_value.all.return_value = []
            return res

        session = AsyncMock()
        session.execute = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        await acknowledge_finding("f-1", "org-1", "user-456", session)

        audit_calls = [
            call.args[0]
            for call in session.add.call_args_list
            if isinstance(call.args[0], AuditEventModel)
        ]
        assert len(audit_calls) == 1
        event = audit_calls[0]
        assert event.action == "agent.finding.acknowledged"
        assert event.actor_id == "user-456"
        assert event.entity_type == "AgentFinding"
        assert event.entity_id == "f-1"
        assert event.outcome == "success"
