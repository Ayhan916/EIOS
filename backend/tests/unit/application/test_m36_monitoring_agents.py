"""M36 Unit Tests — Individual Monitoring Agent Detection Logic.

Tests detection rules for risk_monitor and remediation_monitor.
Other agents follow the same pattern and are covered by the same helper infrastructure.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_supplier(supplier_id="s-1", name="Acme Corp", status="Active", org_id="org-1"):
    s = MagicMock()
    s.id = supplier_id
    s.name = name
    s.supplier_status = status
    s.organization_id = org_id
    return s


def _make_score(
    risk_score=50.0,
    esg_score=65.0,
    trend="Stable",
    trend_delta=0.0,
    sector_percentile=50.0,
    risk_band="Medium",
    supplier_id="s-1",
    org_id="org-1",
):
    sc = MagicMock()
    sc.risk_score = risk_score
    sc.esg_score = esg_score
    sc.trend = trend
    sc.trend_delta = trend_delta
    sc.sector_percentile = sector_percentile
    sc.risk_band = risk_band
    sc.supplier_id = supplier_id
    sc.organization_id = org_id
    return sc


def _make_plan(
    plan_id="p-1",
    title="Remediation Plan 1",
    status="open",
    supplier_id="s-1",
    due_date=None,
):
    plan = MagicMock()
    plan.id = plan_id
    plan.title = title
    plan.remediation_status = status
    plan.supplier_id = supplier_id
    plan.due_date = due_date
    return plan


def _session_with_suppliers_and_scores(suppliers, score=None, open_count=0):
    """Build a session that returns suppliers → score → open_findings_count in order."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    call_count = 0

    async def _execute(stmt):
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            # Supplier query
            result.scalars.return_value.all.return_value = suppliers
        elif call_count % 3 == 1:
            # Score query per supplier
            result.scalar_one_or_none = MagicMock(return_value=score)
        else:
            # Open findings count per supplier
            result.scalar_one = MagicMock(return_value=open_count)
        call_count += 1
        return result

    session.execute = AsyncMock(side_effect=_execute)
    return session


# ── Risk Monitor — Detection Rules ────────────────────────────────────────────


class TestRiskMonitorDetection:
    async def test_critical_risk_score_creates_critical_finding(self) -> None:
        from application.agent_monitoring import risk_monitor

        supplier = _make_supplier()
        score = _make_score(risk_score=90.0)
        session = _session_with_suppliers_and_scores([supplier], score=score, open_count=0)

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.description = kwargs["description"]
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.risk_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch(
                "application.agent_monitoring.risk_monitor._maybe_escalate",
                new_callable=lambda: lambda *a, **kw: AsyncMock(return_value=None)(),
            ),
        ):
            count = await risk_monitor.run(
                agent_id="agent-1",
                agent_run_id="run-1",
                organization_id="org-1",
                session=session,
            )

        assert count >= 1
        critical_findings = [f for f in created_findings if f.severity == "CRITICAL"]
        assert len(critical_findings) >= 1

    async def test_high_risk_score_creates_high_finding(self) -> None:
        from application.agent_monitoring import risk_monitor

        supplier = _make_supplier()
        score = _make_score(risk_score=75.0)
        session = _session_with_suppliers_and_scores([supplier], score=score, open_count=0)

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.risk_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch("application.agent_monitoring.risk_monitor._maybe_escalate", new=AsyncMock()),
        ):
            count = await risk_monitor.run("agent-1", "run-1", "org-1", session)

        assert count >= 1
        high_findings = [f for f in created_findings if f.severity == "HIGH"]
        assert len(high_findings) >= 1

    async def test_ok_risk_score_creates_no_finding(self) -> None:
        from application.agent_monitoring import risk_monitor

        supplier = _make_supplier()
        score = _make_score(risk_score=40.0, esg_score=70.0, sector_percentile=60.0)
        session = _session_with_suppliers_and_scores([supplier], score=score, open_count=0)

        with (
            patch("application.agent_monitoring.risk_monitor.create_finding", new=AsyncMock()),
            patch("application.agent_monitoring.risk_monitor._maybe_escalate", new=AsyncMock()),
        ):
            count = await risk_monitor.run("agent-1", "run-1", "org-1", session)

        assert count == 0

    async def test_deteriorating_esg_creates_high_finding(self) -> None:
        from application.agent_monitoring import risk_monitor

        supplier = _make_supplier()
        score = _make_score(
            risk_score=50.0,  # not high enough for risk_score rule
            esg_score=45.0,
            trend="Deteriorating",
            trend_delta=-15.0,
        )
        session = _session_with_suppliers_and_scores([supplier], score=score, open_count=0)

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.source_data_json = kwargs["source_data"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.risk_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch("application.agent_monitoring.risk_monitor._maybe_escalate", new=AsyncMock()),
        ):
            await risk_monitor.run("agent-1", "run-1", "org-1", session)

        esg_findings = [f for f in created_findings if f.category == "esg_deterioration"]
        assert len(esg_findings) >= 1
        assert esg_findings[0].severity == "HIGH"

    async def test_bottom_decile_creates_medium_finding(self) -> None:
        from application.agent_monitoring import risk_monitor

        supplier = _make_supplier()
        score = _make_score(risk_score=50.0, sector_percentile=5.0)  # bottom 10%
        session = _session_with_suppliers_and_scores([supplier], score=score, open_count=0)

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.risk_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch("application.agent_monitoring.risk_monitor._maybe_escalate", new=AsyncMock()),
        ):
            await risk_monitor.run("agent-1", "run-1", "org-1", session)

        perc_findings = [f for f in created_findings if f.category == "benchmark_underperformance"]
        assert len(perc_findings) >= 1
        assert perc_findings[0].severity == "MEDIUM"

    async def test_high_open_findings_creates_medium_finding(self) -> None:
        from application.agent_monitoring import risk_monitor

        supplier = _make_supplier()
        score = _make_score(risk_score=50.0, sector_percentile=50.0)
        session = _session_with_suppliers_and_scores([supplier], score=score, open_count=8)

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.risk_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch("application.agent_monitoring.risk_monitor._maybe_escalate", new=AsyncMock()),
        ):
            await risk_monitor.run("agent-1", "run-1", "org-1", session)

        vol_findings = [f for f in created_findings if f.category == "findings_accumulation"]
        assert len(vol_findings) >= 1
        assert vol_findings[0].severity == "MEDIUM"

    async def test_no_suppliers_returns_zero_findings(self) -> None:
        from application.agent_monitoring import risk_monitor

        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)

        count = await risk_monitor.run("agent-1", "run-1", "org-1", session)
        assert count == 0

    async def test_no_score_skips_supplier(self) -> None:
        from application.agent_monitoring import risk_monitor

        supplier = _make_supplier()
        # score = None for this supplier
        session = _session_with_suppliers_and_scores([supplier], score=None, open_count=0)

        with (
            patch("application.agent_monitoring.risk_monitor.create_finding", new=AsyncMock()),
            patch("application.agent_monitoring.risk_monitor._maybe_escalate", new=AsyncMock()),
        ):
            count = await risk_monitor.run("agent-1", "run-1", "org-1", session)

        assert count == 0


# ── Remediation Monitor — Detection Rules ─────────────────────────────────────


class TestRemediationMonitorDetection:
    def _session_remediation(self, suppliers, plans):
        """Return session that emits suppliers then plans per-supplier."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                result.scalars.return_value.all.return_value = suppliers
            else:
                result.scalars.return_value.all.return_value = plans
            call_count += 1
            return result

        session.execute = AsyncMock(side_effect=_execute)
        return session

    async def test_critical_overdue_creates_critical_finding(self) -> None:
        from application.agent_monitoring import remediation_monitor

        supplier = _make_supplier()
        now = datetime.now(UTC)
        overdue_plan = _make_plan(
            due_date=now - timedelta(days=100),
            status="open",
        )
        session = self._session_remediation([supplier], [overdue_plan])

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.remediation_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._maybe_escalate", new=AsyncMock()
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._create_draft",
                new=AsyncMock(return_value=MagicMock()),
            ),
        ):
            await remediation_monitor.run("agent-1", "run-1", "org-1", session)

        critical = [f for f in created_findings if f.severity == "CRITICAL"]
        assert len(critical) >= 1

    async def test_high_overdue_creates_high_finding(self) -> None:
        from application.agent_monitoring import remediation_monitor

        supplier = _make_supplier()
        now = datetime.now(UTC)
        overdue_plan = _make_plan(
            due_date=now - timedelta(days=45),  # 30-89 days = HIGH
            status="open",
        )
        session = self._session_remediation([supplier], [overdue_plan])

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.remediation_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._maybe_escalate", new=AsyncMock()
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._create_draft",
                new=AsyncMock(return_value=None),
            ),
        ):
            await remediation_monitor.run("agent-1", "run-1", "org-1", session)

        high_findings = [f for f in created_findings if f.severity == "HIGH"]
        assert len(high_findings) >= 1

    async def test_not_overdue_plan_creates_no_finding(self) -> None:
        from application.agent_monitoring import remediation_monitor

        supplier = _make_supplier()
        now = datetime.now(UTC)
        plan = _make_plan(
            due_date=now + timedelta(days=30),  # future date — not overdue
            status="open",
        )
        session = self._session_remediation([supplier], [plan])

        with (
            patch(
                "application.agent_monitoring.remediation_monitor.create_finding", new=AsyncMock()
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._maybe_escalate", new=AsyncMock()
            ),
        ):
            count = await remediation_monitor.run("agent-1", "run-1", "org-1", session)

        # 1 plan is not >= _OPEN_PLANS_HIGH (10), so no volume finding either
        assert count == 0

    async def test_critical_overdue_creates_recommendation_draft(self) -> None:
        """Remediation monitor must create a draft for critically overdue plans."""
        from application.agent_monitoring import remediation_monitor

        supplier = _make_supplier()
        now = datetime.now(UTC)
        overdue_plan = _make_plan(due_date=now - timedelta(days=95), status="open")
        session = self._session_remediation([supplier], [overdue_plan])

        draft_calls = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            return f

        async def _fake_create_draft(**kwargs):
            draft_calls.append(kwargs)
            return MagicMock()

        with (
            patch(
                "application.agent_monitoring.remediation_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._maybe_escalate", new=AsyncMock()
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._create_draft",
                side_effect=_fake_create_draft,
            ),
        ):
            await remediation_monitor.run("agent-1", "run-1", "org-1", session)

        assert len(draft_calls) >= 1

    async def test_high_plan_volume_creates_medium_finding(self) -> None:
        from application.agent_monitoring import remediation_monitor

        supplier = _make_supplier()
        now = datetime.now(UTC)
        # 10 open plans, none overdue
        plans = [
            _make_plan(
                plan_id=f"p-{i}",
                title=f"Plan {i}",
                status="open",
                due_date=now + timedelta(days=30),
            )
            for i in range(10)
        ]
        session = self._session_remediation([supplier], plans)

        created_findings = []

        async def _fake_create_finding(**kwargs):
            f = MagicMock()
            f.id = "f-new"
            f.severity = kwargs["severity"]
            f.category = kwargs["category"]
            f.agent_id = kwargs["agent_id"]
            f.supplier_id = kwargs.get("supplier_id")
            f.source_data_json = kwargs["source_data"]
            f.confidence_score = kwargs["confidence_score"]
            created_findings.append(f)
            return f

        with (
            patch(
                "application.agent_monitoring.remediation_monitor.create_finding",
                side_effect=_fake_create_finding,
            ),
            patch(
                "application.agent_monitoring.remediation_monitor._maybe_escalate", new=AsyncMock()
            ),
        ):
            await remediation_monitor.run("agent-1", "run-1", "org-1", session)

        volume_findings = [f for f in created_findings if f.category == "remediation_volume"]
        assert len(volume_findings) >= 1
        assert volume_findings[0].severity == "MEDIUM"


# ── Human approval boundary ────────────────────────────────────────────────────


class TestHumanApprovalBoundary:
    def test_risk_monitor_has_no_approve_calls(self) -> None:
        """Verify risk_monitor source does not call approve_draft or close anything."""
        import inspect

        from application.agent_monitoring import risk_monitor

        src = inspect.getsource(risk_monitor)
        assert "approve_draft" not in src
        assert "close_finding" not in src
        assert "resolve_" not in src

    def test_remediation_monitor_has_no_approve_calls(self) -> None:
        import inspect

        from application.agent_monitoring import remediation_monitor

        src = inspect.getsource(remediation_monitor)
        assert "approve_draft" not in src
        assert "close_finding" not in src

    def test_scheduler_has_no_approve_calls(self) -> None:
        import inspect

        from application.agent_monitoring import scheduler

        src = inspect.getsource(scheduler)
        assert "approve_draft" not in src
        assert "approve_assessment" not in src
