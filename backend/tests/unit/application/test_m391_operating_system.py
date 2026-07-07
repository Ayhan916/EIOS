"""M39.1 ESG Operating System Completion — unit tests.

Covers:
  1. CalendarService — CRUD, audit events, recurrence support
  2. ProgramService — CRUD, lifecycle
  3. ControlService — CRUD, type/effectiveness
  4. ControlTestService — create updates parent effectiveness, delete
  5. ComplianceOperationService — CRUD, sync_from_m31 idempotency
  6. AccountabilityService — assign, list, remove, role enforcement
  7. ExecutiveOversight — M39 fields in executive dashboard
  8. TimelineEndpoint — chronological aggregation
  9. CrossModuleOrchestration — ingest_from_module_idempotent, M37/M38 wiring
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Shared helpers ─────────────────────────────────────────────────────────────


def _fake_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


def _scalar_result(value) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    r.scalar_one = MagicMock(return_value=value)
    r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    return r


def _scalars_result(items: list) -> MagicMock:
    r = MagicMock()
    r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=items)))
    r.scalar_one = MagicMock(return_value=len(items))
    r.all = MagicMock(return_value=items)
    return r


def _mock_calendar_event(org="org-1") -> MagicMock:
    e = MagicMock()
    e.id = "evt-1"
    e.organization_id = org
    e.title = "Q1 Board Review"
    e.event_type = "BOARD_REVIEW"
    e.scheduled_at = datetime(2026, 3, 31, 10, 0, tzinfo=UTC)
    e.recurrence_rule = "FREQ=QUARTERLY"
    e.reminder_days = 14
    e.event_status = "SCHEDULED"
    e.linked_entity_type = None
    e.linked_entity_id = None
    e.notes = ""
    e.created_at = datetime.now(UTC)
    e.updated_at = datetime.now(UTC)
    return e


def _mock_program(org="org-1") -> MagicMock:
    p = MagicMock()
    p.id = "prog-1"
    p.organization_id = org
    p.title = "CSRD Compliance Program 2026"
    p.description = ""
    p.program_status = "ACTIVE"
    p.linked_objectives = []
    p.linked_initiatives = []
    p.linked_suppliers = []
    p.created_at = datetime.now(UTC)
    p.updated_at = datetime.now(UTC)
    return p


def _mock_control(org="org-1") -> MagicMock:
    c = MagicMock()
    c.id = "ctrl-1"
    c.organization_id = org
    c.control_name = "Supplier Code of Conduct Sign-off"
    c.control_type = "PREVENTIVE"
    c.owner_user_id = None
    c.frequency = "ANNUAL"
    c.evidence_required = True
    c.effectiveness_status = "NOT_TESTED"
    c.created_at = datetime.now(UTC)
    c.updated_at = datetime.now(UTC)
    return c


def _mock_control_test(org="org-1") -> MagicMock:
    t = MagicMock()
    t.id = "test-1"
    t.organization_id = org
    t.control_id = "ctrl-1"
    t.performed_by = "user-99"
    t.test_result = "PASS"
    t.findings = ""
    t.tested_at = datetime.now(UTC)
    t.created_at = datetime.now(UTC)
    t.updated_at = datetime.now(UTC)
    return t


def _mock_compliance_op(org="org-1", framework="CSRD") -> MagicMock:
    op = MagicMock()
    op.id = "compop-1"
    op.organization_id = org
    op.framework_name = framework
    op.coverage_percent = 72.5
    op.gap_count = 3
    op.owner_user_id = None
    op.operation_status = "IN_PROGRESS"
    op.actions = []
    op.last_synced_at = datetime.now(UTC)
    op.created_at = datetime.now(UTC)
    op.updated_at = datetime.now(UTC)
    return op


def _mock_assignment(org="org-1") -> MagicMock:
    a = MagicMock()
    a.id = "asgn-1"
    a.organization_id = org
    a.entity_type = "ESGObjective"
    a.entity_id = "obj-1"
    a.role = "OWNER"
    a.assigned_to_user_id = "user-1"
    a.assigned_by_user_id = None
    a.assigned_at = datetime.now(UTC)
    a.assignment_status = "ACTIVE"
    a.created_at = datetime.now(UTC)
    a.updated_at = datetime.now(UTC)
    return a


# ── 1. Calendar Service ────────────────────────────────────────────────────────


class TestCalendarService:
    @pytest.mark.asyncio
    async def test_create_event_returns_dict(self):
        from application.operating_system.calendar_service import create_event

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        scheduled = datetime(2026, 3, 31, 10, 0, tzinfo=UTC)

        row = await create_event(
            organization_id="org-1",
            title="Q1 Board Review",
            event_type="BOARD_REVIEW",
            scheduled_at=scheduled,
            recurrence_rule="FREQ=QUARTERLY",
            reminder_days=14,
            session=session,
        )

        assert row["title"] == "Q1 Board Review"
        assert row["event_type"] == "BOARD_REVIEW"
        assert row["event_status"] == "SCHEDULED"
        assert row["recurrence_rule"] == "FREQ=QUARTERLY"
        assert row["reminder_days"] == 14

    @pytest.mark.asyncio
    async def test_create_event_emits_audit_event(self):
        from application.operating_system.calendar_service import create_event

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        await create_event(
            organization_id="org-1",
            title="Test",
            event_type="BOARD_REVIEW",
            scheduled_at=datetime.now(UTC),
            session=session,
        )

        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "calendar.event_created" for e in audit_events)

    @pytest.mark.asyncio
    async def test_list_events_returns_all(self):
        from application.operating_system.calendar_service import list_events

        session = _fake_session()
        evt = _mock_calendar_event()
        session.execute = AsyncMock(return_value=_scalars_result([evt]))

        rows = await list_events("org-1", session)

        assert len(rows) == 1
        assert rows[0]["title"] == "Q1 Board Review"

    @pytest.mark.asyncio
    async def test_get_event_not_found_returns_none(self):
        from application.operating_system.calendar_service import get_event

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await get_event("org-1", "nonexistent", session)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_event_emits_updated_audit(self):
        from application.operating_system.calendar_service import update_event

        session = _fake_session()
        evt = _mock_calendar_event()
        session.execute = AsyncMock(return_value=_scalar_result(evt))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        row = await update_event("org-1", "evt-1", session, event_status="COMPLETED")

        assert row is not None
        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "calendar.event_updated" for e in audit_events)

    @pytest.mark.asyncio
    async def test_delete_event_returns_false_when_not_found(self):
        from application.operating_system.calendar_service import delete_event

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await delete_event("org-1", "nonexistent", session)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_event_emits_deleted_audit(self):
        from application.operating_system.calendar_service import delete_event

        session = _fake_session()
        evt = _mock_calendar_event()
        session.execute = AsyncMock(return_value=_scalar_result(evt))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        result = await delete_event("org-1", "evt-1", session)

        assert result is True
        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "calendar.event_deleted" for e in audit_events)


# ── 2. Program Service ─────────────────────────────────────────────────────────


class TestProgramService:
    @pytest.mark.asyncio
    async def test_create_program_status_active(self):
        from application.operating_system.program_service import create_program

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await create_program("org-1", "CSRD 2026", session, description="Main program")

        assert row["title"] == "CSRD 2026"
        assert row["program_status"] == "ACTIVE"
        assert row["linked_objectives"] == []

    @pytest.mark.asyncio
    async def test_create_program_emits_audit(self):
        from application.operating_system.program_service import create_program

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        await create_program("org-1", "Test Program", session)

        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "program.created" for e in audit_events)

    @pytest.mark.asyncio
    async def test_list_programs_empty(self):
        from application.operating_system.program_service import list_programs

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalars_result([]))

        rows = await list_programs("org-1", session)

        assert rows == []

    @pytest.mark.asyncio
    async def test_update_program_to_archived_emits_deleted_audit(self):
        from application.operating_system.program_service import update_program

        session = _fake_session()
        prog = _mock_program()
        session.execute = AsyncMock(return_value=_scalar_result(prog))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        row = await update_program("org-1", "prog-1", session, program_status="ARCHIVED")

        assert row is not None
        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "program.deleted" for e in audit_events)

    @pytest.mark.asyncio
    async def test_get_program_not_found(self):
        from application.operating_system.program_service import get_program

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await get_program("org-1", "missing", session)

        assert result is None


# ── 3. Control Service ────────────────────────────────────────────────────────


class TestControlService:
    @pytest.mark.asyncio
    async def test_create_control_default_not_tested(self):
        from application.operating_system.control_service import create_control

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await create_control(
            organization_id="org-1",
            control_name="Code of Conduct Sign-off",
            control_type="PREVENTIVE",
            session=session,
        )

        assert row["control_name"] == "Code of Conduct Sign-off"
        assert row["control_type"] == "PREVENTIVE"
        assert row["effectiveness_status"] == "NOT_TESTED"

    @pytest.mark.asyncio
    async def test_create_control_emits_audit(self):
        from application.operating_system.control_service import create_control

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        await create_control("org-1", "Test Control", "DETECTIVE", session=session)

        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "control.created" for e in audit_events)

    @pytest.mark.asyncio
    async def test_list_controls_with_type_filter(self):
        from application.operating_system.control_service import list_controls

        session = _fake_session()
        ctrl = _mock_control()
        session.execute = AsyncMock(return_value=_scalars_result([ctrl]))

        rows = await list_controls("org-1", session, control_type="PREVENTIVE")

        assert len(rows) == 1
        assert rows[0]["control_type"] == "PREVENTIVE"

    @pytest.mark.asyncio
    async def test_update_control_not_found_returns_none(self):
        from application.operating_system.control_service import update_control

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await update_control("org-1", "missing", session, frequency="QUARTERLY")

        assert result is None


# ── 4. Control Test Service ───────────────────────────────────────────────────


class TestControlTestService:
    @pytest.mark.asyncio
    async def test_create_test_pass_updates_parent_effectiveness(self):
        from application.operating_system.control_test_service import create_test

        session = _fake_session()
        ctrl = _mock_control()
        # First call returns the test, second returns the control
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(None),  # dedup check (no existing test model in flush)
                _scalar_result(ctrl),  # parent control lookup
            ]
        )
        session.execute = AsyncMock(return_value=_scalar_result(ctrl))

        row = await create_test(
            organization_id="org-1",
            control_id="ctrl-1",
            test_result="PASS",
            tested_at=datetime.now(UTC),
            session=session,
        )

        assert row["test_result"] == "PASS"
        # Parent effectiveness should have been updated
        assert ctrl.effectiveness_status == "EFFECTIVE"

    @pytest.mark.asyncio
    async def test_create_test_fail_sets_ineffective(self):
        from application.operating_system.control_test_service import create_test

        session = _fake_session()
        ctrl = _mock_control()
        session.execute = AsyncMock(return_value=_scalar_result(ctrl))

        row = await create_test(
            organization_id="org-1",
            control_id="ctrl-1",
            test_result="FAIL",
            tested_at=datetime.now(UTC),
            session=session,
        )

        assert row["test_result"] == "FAIL"
        assert ctrl.effectiveness_status == "INEFFECTIVE"

    @pytest.mark.asyncio
    async def test_create_test_partial_sets_partially_effective(self):
        from application.operating_system.control_test_service import create_test

        session = _fake_session()
        ctrl = _mock_control()
        session.execute = AsyncMock(return_value=_scalar_result(ctrl))

        await create_test(
            organization_id="org-1",
            control_id="ctrl-1",
            test_result="PARTIAL",
            tested_at=datetime.now(UTC),
            session=session,
        )

        assert ctrl.effectiveness_status == "PARTIALLY_EFFECTIVE"

    @pytest.mark.asyncio
    async def test_create_test_emits_audit(self):
        from application.operating_system.control_test_service import create_test

        session = _fake_session()
        ctrl = _mock_control()
        session.execute = AsyncMock(return_value=_scalar_result(ctrl))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        await create_test("org-1", "ctrl-1", "PASS", datetime.now(UTC), session)

        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "control.tested" for e in audit_events)

    @pytest.mark.asyncio
    async def test_delete_test_not_found_returns_false(self):
        from application.operating_system.control_test_service import delete_test

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await delete_test("org-1", "missing", session)

        assert result is False

    @pytest.mark.asyncio
    async def test_list_tests_filtered_by_control(self):
        from application.operating_system.control_test_service import list_tests

        session = _fake_session()
        t = _mock_control_test()
        session.execute = AsyncMock(return_value=_scalars_result([t]))

        rows = await list_tests("org-1", session, control_id="ctrl-1")

        assert len(rows) == 1
        assert rows[0]["control_id"] == "ctrl-1"


# ── 5. Compliance Operation Service ──────────────────────────────────────────


class TestComplianceOperationService:
    @pytest.mark.asyncio
    async def test_create_operation_default_in_progress(self):
        from application.operating_system.compliance_operation_service import (
            create_compliance_operation,
        )

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await create_compliance_operation("org-1", "CSRD", session)

        assert row["framework_name"] == "CSRD"
        assert row["operation_status"] == "IN_PROGRESS"
        assert row["gap_count"] == 0

    @pytest.mark.asyncio
    async def test_sync_from_m31_creates_when_not_exists(self):
        from application.operating_system.compliance_operation_service import sync_from_m31

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await sync_from_m31(
            organization_id="org-1",
            framework_name="CSDDD",
            coverage_percent=85.0,
            gap_count=2,
            session=session,
        )

        assert row["framework_name"] == "CSDDD"
        assert row["coverage_percent"] == 85.0
        assert row["gap_count"] == 2

    @pytest.mark.asyncio
    async def test_sync_from_m31_updates_existing(self):
        from application.operating_system.compliance_operation_service import sync_from_m31

        session = _fake_session()
        existing = _mock_compliance_op()
        session.execute = AsyncMock(return_value=_scalar_result(existing))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        await sync_from_m31("org-1", "CSRD", 90.0, 1, session)

        assert existing.coverage_percent == 90.0
        assert existing.gap_count == 1
        # Should not create a new ComplianceOperationModel
        from infrastructure.persistence.models.operating_system import ComplianceOperationModel

        new_ops = [o for o in added if isinstance(o, ComplianceOperationModel)]
        assert len(new_ops) == 0

    @pytest.mark.asyncio
    async def test_sync_from_m31_emits_synced_audit(self):
        from application.operating_system.compliance_operation_service import sync_from_m31

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        await sync_from_m31("org-1", "ESRS", 60.0, 5, session)

        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "compliance_op.synced" for e in audit_events)

    @pytest.mark.asyncio
    async def test_list_operations_empty(self):
        from application.operating_system.compliance_operation_service import (
            list_compliance_operations,
        )

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalars_result([]))

        rows = await list_compliance_operations("org-1", session)

        assert rows == []

    @pytest.mark.asyncio
    async def test_get_operation_not_found(self):
        from application.operating_system.compliance_operation_service import (
            get_compliance_operation,
        )

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await get_compliance_operation("org-1", "missing", session)

        assert result is None


# ── 6. Accountability Service ─────────────────────────────────────────────────


class TestAccountabilityService:
    @pytest.mark.asyncio
    async def test_assign_creates_active_assignment(self):
        from application.operating_system.accountability_service import assign_accountability

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await assign_accountability(
            organization_id="org-1",
            entity_type="ESGObjective",
            entity_id="obj-1",
            role="OWNER",
            assigned_to_user_id="user-1",
            session=session,
        )

        assert row["role"] == "OWNER"
        assert row["assignment_status"] == "ACTIVE"
        assert row["entity_type"] == "ESGObjective"

    @pytest.mark.asyncio
    async def test_assign_emits_assigned_audit(self):
        from application.operating_system.accountability_service import assign_accountability

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        await assign_accountability("org-1", "ESGObjective", "obj-1", "REVIEWER", "user-2", session)

        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "accountability.assigned" for e in audit_events)

    @pytest.mark.asyncio
    async def test_remove_assignment_soft_deletes(self):
        from application.operating_system.accountability_service import remove_assignment

        session = _fake_session()
        asgn = _mock_assignment()
        session.execute = AsyncMock(return_value=_scalar_result(asgn))
        added = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        result = await remove_assignment("org-1", "asgn-1", session)

        assert result is True
        assert asgn.assignment_status == "REMOVED"
        from infrastructure.persistence.models.audit_event import AuditEventModel

        audit_events = [o for o in added if isinstance(o, AuditEventModel)]
        assert any(e.action == "accountability.removed" for e in audit_events)

    @pytest.mark.asyncio
    async def test_remove_assignment_not_found(self):
        from application.operating_system.accountability_service import remove_assignment

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await remove_assignment("org-1", "nonexistent", session)

        assert result is False

    @pytest.mark.asyncio
    async def test_list_assignments_by_role(self):
        from application.operating_system.accountability_service import list_assignments

        session = _fake_session()
        asgn = _mock_assignment()
        session.execute = AsyncMock(return_value=_scalars_result([asgn]))

        rows = await list_assignments("org-1", session, role="OWNER")

        assert len(rows) == 1
        assert rows[0]["role"] == "OWNER"

    @pytest.mark.asyncio
    async def test_get_assignment_not_found(self):
        from application.operating_system.accountability_service import get_assignment

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await get_assignment("org-1", "missing", session)

        assert result is None


# ── 7. Executive Oversight ────────────────────────────────────────────────────


class TestExecutiveOversight:
    def test_executive_dashboard_schema_has_esg_summary(self):
        from interfaces.api.schemas.executive import ExecutiveDashboard

        assert "esg_summary" in ExecutiveDashboard.model_fields

    def test_esg_operating_summary_has_required_fields(self):
        from interfaces.api.schemas.executive import ESGOperatingSummary

        fields = set(ESGOperatingSummary.model_fields.keys())
        assert "objectives_at_risk" in fields
        assert "initiatives_at_risk" in fields
        assert "strategic_risks_critical" in fields
        assert "strategic_risks_total" in fields
        assert "overdue_esg_actions" in fields

    def test_esg_summary_is_optional(self):
        from interfaces.api.schemas.executive import (
            ActionSummary,
            ExecutiveDashboard,
            GovernanceSummary,
            PortfolioSummary,
        )

        dashboard = ExecutiveDashboard(
            portfolio_summary=PortfolioSummary(
                total_suppliers=0,
                scored_suppliers=0,
                critical_risk_suppliers=0,
                high_risk_suppliers=0,
                moderate_risk_suppliers=0,
                low_risk_suppliers=0,
                improving_suppliers=0,
                deteriorating_suppliers=0,
                avg_esg_score=None,
                avg_risk_score=None,
                risk_distribution={},
            ),
            action_summary=ActionSummary(
                open_actions=0, overdue_actions=0, total_actions=0, resolution_rate=None
            ),
            governance_summary=GovernanceSummary(
                assessments_awaiting_review=0, assessments_approved=0, critical_findings_total=0
            ),
        )
        assert dashboard.esg_summary is None

    def test_esg_summary_can_be_set(self):
        from interfaces.api.schemas.executive import (
            ActionSummary,
            ESGOperatingSummary,
            ExecutiveDashboard,
            GovernanceSummary,
            PortfolioSummary,
        )

        summary = ESGOperatingSummary(
            objectives_at_risk=2,
            initiatives_at_risk=1,
            strategic_risks_critical=3,
            strategic_risks_total=5,
            overdue_esg_actions=4,
        )
        dashboard = ExecutiveDashboard(
            portfolio_summary=PortfolioSummary(
                total_suppliers=0,
                scored_suppliers=0,
                critical_risk_suppliers=0,
                high_risk_suppliers=0,
                moderate_risk_suppliers=0,
                low_risk_suppliers=0,
                improving_suppliers=0,
                deteriorating_suppliers=0,
                avg_esg_score=None,
                avg_risk_score=None,
                risk_distribution={},
            ),
            action_summary=ActionSummary(
                open_actions=0, overdue_actions=0, total_actions=0, resolution_rate=None
            ),
            governance_summary=GovernanceSummary(
                assessments_awaiting_review=0, assessments_approved=0, critical_findings_total=0
            ),
            esg_summary=summary,
        )
        assert dashboard.esg_summary.objectives_at_risk == 2
        assert dashboard.esg_summary.strategic_risks_total == 5


# ── 8. Timeline Endpoint ──────────────────────────────────────────────────────


class TestTimelineEndpoint:
    def test_timeline_entry_schema_fields(self):
        from interfaces.api.schemas.operating_system import TimelineEntry

        fields = set(TimelineEntry.model_fields.keys())
        assert "event_type" in fields
        assert "entity_type" in fields
        assert "entity_id" in fields
        assert "title" in fields
        assert "timestamp" in fields
        assert "status" in fields

    def test_timeline_entry_instantiation(self):
        from interfaces.api.schemas.operating_system import TimelineEntry

        entry = TimelineEntry(
            event_type="objective.created",
            entity_type="ESGObjective",
            entity_id="obj-1",
            title="Net Zero 2030",
            timestamp=datetime.now(UTC),
            status="NOT_STARTED",
        )
        assert entry.event_type == "objective.created"
        assert entry.entity_id == "obj-1"

    def test_timeline_route_exists_in_router(self):
        import os

        router_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__), "../../../interfaces/api/routers/operating_system.py"
            )
        )
        with open(router_path) as f:
            content = f.read()
        assert '"/timeline"' in content or "'/timeline'" in content

    def test_all_new_routes_registered(self):
        import os

        router_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__), "../../../interfaces/api/routers/operating_system.py"
            )
        )
        with open(router_path) as f:
            content = f.read()
        for expected in [
            "/calendar",
            "/programs",
            "/controls",
            "/tests",
            "/compliance-operations",
            "/accountability",
            "/timeline",
        ]:
            assert f'"{expected}"' in content or f"'{expected}'" in content, (
                f"Missing route: {expected}"
            )


# ── 9. Cross-Module Orchestration ─────────────────────────────────────────────


class TestCrossModuleOrchestration:
    @pytest.mark.asyncio
    async def test_ingest_idempotent_skips_when_exists(self):
        from application.operating_system.action_service import ingest_from_module_idempotent

        session = _fake_session()
        existing_action = MagicMock()
        session.execute = AsyncMock(return_value=_scalar_result(existing_action))

        result = await ingest_from_module_idempotent(
            organization_id="org-1",
            source_type="SURVEILLANCE_SIGNAL",
            source_id="sig-1",
            title="Critical signal",
            priority="CRITICAL",
            session=session,
        )

        assert result is None
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_idempotent_creates_when_not_exists(self):
        from application.operating_system.action_service import ingest_from_module_idempotent

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await ingest_from_module_idempotent(
            organization_id="org-1",
            source_type="NETWORK_EXPOSURE",
            source_id="cluster-1",
            title="Network incident cluster: Child Labour",
            priority="HIGH",
            session=session,
        )

        assert result is not None
        assert result["source_type"] == "NETWORK_EXPOSURE"
        assert result["source_id"] == "cluster-1"
        assert result["priority"] == "HIGH"

    @pytest.mark.asyncio
    async def test_m37_critical_signal_triggers_esg_action(self):
        from application.surveillance.signal_service import create_signal

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        ingested = []

        with patch(
            "application.operating_system.action_service.ingest_from_module_idempotent",
            new=AsyncMock(side_effect=lambda **kw: ingested.append(kw)),
        ):
            await create_signal(
                organization_id="org-1",
                signal_type="DRIFT",
                source_type="EXTERNAL",
                severity="CRITICAL",
                title="Critical supplier drift",
                description="Supplier X critical drift detected",
                session=session,
                skip_if_active=False,
            )

        assert len(ingested) == 1
        assert ingested[0]["source_type"] == "SURVEILLANCE_SIGNAL"
        assert ingested[0]["priority"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_m37_non_critical_signal_does_not_trigger_action(self):
        from application.surveillance.signal_service import create_signal

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        ingested = []

        with patch(
            "application.operating_system.action_service.ingest_from_module_idempotent",
            new=AsyncMock(side_effect=lambda **kw: ingested.append(kw)),
        ):
            await create_signal(
                organization_id="org-1",
                signal_type="DRIFT",
                source_type="EXTERNAL",
                severity="MEDIUM",
                title="Medium signal",
                description="",
                session=session,
                skip_if_active=False,
            )

        assert len(ingested) == 0

    def test_dashboard_schema_has_new_fields(self):
        from interfaces.api.schemas.operating_system import OperatingSystemDashboard

        fields = set(OperatingSystemDashboard.model_fields.keys())
        assert "compliance_operations" in fields
        assert "governance_calendar_events" in fields
        assert "programs_total" in fields
        assert "controls_total" in fields
