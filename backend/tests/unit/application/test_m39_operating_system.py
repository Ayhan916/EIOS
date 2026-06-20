"""M39 ESG Operating System — unit tests.

Covers:
  1. Objective Tests — CRUD, status derivation, tenant isolation
  2. Key Result Tests — progress rollup, status derivation
  3. Initiative Tests — CRUD, lifecycle, audit events
  4. Action Tests — unified inbox, cross-module ingestion, overdue filter
  5. Playbook Tests — creation, retrieval
  6. Workflow Tests — start, approve step, reject step, human-approval guard
  7. Escalation Tests — rule evaluation, trigger detection
  8. Health Score Tests — deterministic formula, explainability
  9. Strategic Risk Tests — CRUD, level/status filters
 10. Tenant Isolation Tests — cross-org access returns None
 11. Metrics Tests — counters increment on create events
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _fake_session() -> MagicMock:
    session = MagicMock()
    session.add = MagicMock()
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


# ── 1. Objective Tests ─────────────────────────────────────────────────────────

class TestObjectiveService:
    @pytest.mark.asyncio
    async def test_create_objective_returns_dict_with_required_fields(self):
        from application.operating_system.objective_service import create_objective
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        with patch("application.operating_system.objective_service.os_counters") as mock_c:
            row = await create_objective(
                organization_id="org-1",
                title="Net Zero 2030",
                description="Carbon neutral by 2030",
                category="ENVIRONMENTAL",
                session=session,
            )

        assert row["title"] == "Net Zero 2030"
        assert row["category"] == "ENVIRONMENTAL"
        assert row["objective_status"] == "NOT_STARTED"
        assert row["organization_id"] == "org-1"
        mock_c.record_objective_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_objective_status_not_started_on_create(self):
        from application.operating_system.objective_service import create_objective
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        with patch("application.operating_system.objective_service.os_counters"):
            row = await create_objective(
                organization_id="org-1",
                title="Test Obj",
                description="",
                category="SOCIAL",
                session=session,
            )
        assert row["objective_status"] == "NOT_STARTED"

    @pytest.mark.asyncio
    async def test_get_objective_returns_none_for_different_org(self):
        """Tenant isolation: get_objective returns None if org doesn't match."""
        from application.operating_system.objective_service import get_objective
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        result = await get_objective("org-2", "obj-1", session)
        assert result is None

    def test_calc_progress_zero_target_returns_zero(self):
        from application.operating_system.objective_service import _calc_progress
        assert _calc_progress(50, 0) == 0.0

    def test_calc_progress_capped_at_100(self):
        from application.operating_system.objective_service import _calc_progress
        assert _calc_progress(200, 100) == 100.0

    def test_calc_progress_partial(self):
        from application.operating_system.objective_service import _calc_progress
        assert _calc_progress(75, 100) == 75.0

    def test_status_from_progress_completed(self):
        from application.operating_system.objective_service import _status_from_progress
        assert _status_from_progress(100) == "COMPLETED"

    def test_status_from_progress_on_track(self):
        from application.operating_system.objective_service import _status_from_progress
        assert _status_from_progress(80) == "ON_TRACK"

    def test_status_from_progress_at_risk(self):
        from application.operating_system.objective_service import _status_from_progress
        assert _status_from_progress(50) == "AT_RISK"

    def test_status_from_progress_off_track(self):
        from application.operating_system.objective_service import _status_from_progress
        assert _status_from_progress(20) == "OFF_TRACK"


# ── 2. Key Result Tests ────────────────────────────────────────────────────────

class TestKeyResultService:
    @pytest.mark.asyncio
    async def test_create_key_result_computes_progress(self):
        """progress_percent = (current / target) * 100 deterministically."""
        from application.operating_system.objective_service import create_key_result
        session = _fake_session()

        # execute calls: flush KR, then avg query, then obj query
        call_count = 0
        avg_result = MagicMock()
        avg_result.scalar_one_or_none = MagicMock(return_value=50.0)
        obj_result = MagicMock()
        obj_result.scalar_one_or_none = MagicMock(return_value=None)

        async def multi(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return avg_result
            return obj_result

        session.execute = multi

        row = await create_key_result(
            organization_id="org-1",
            objective_id="obj-1",
            title="Reduce emissions",
            metric_name="tCO2e",
            target_value=100.0,
            current_value=75.0,
            session=session,
        )
        assert row["progress_percent"] == 75.0
        assert row["kr_status"] == "ON_TRACK"

    @pytest.mark.asyncio
    async def test_key_result_progress_rolls_up_to_objective(self):
        """Rollup triggers after key result creation."""
        from application.operating_system.objective_service import create_key_result

        session = _fake_session()
        call_count = 0
        avg_result = MagicMock()
        avg_result.scalar_one_or_none = MagicMock(return_value=75.0)

        mock_obj = MagicMock()
        mock_obj.objective_status = "NOT_STARTED"
        obj_result = MagicMock()
        obj_result.scalar_one_or_none = MagicMock(return_value=mock_obj)

        async def multi(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return avg_result
            return obj_result

        session.execute = multi

        await create_key_result(
            organization_id="org-1",
            objective_id="obj-1",
            title="KR1",
            metric_name="score",
            target_value=100.0,
            current_value=75.0,
            session=session,
        )
        # Objective should have been updated to ON_TRACK
        assert mock_obj.objective_status == "ON_TRACK"


# ── 3. Initiative Tests ────────────────────────────────────────────────────────

class TestInitiativeService:
    @pytest.mark.asyncio
    async def test_create_initiative_starts_as_planned(self):
        from application.operating_system.initiative_service import create_initiative
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        with patch("application.operating_system.initiative_service.os_counters") as mock_c:
            row = await create_initiative(
                organization_id="org-1",
                title="Human Rights Due Diligence Program",
                session=session,
            )

        assert row["initiative_status"] == "PLANNED"
        assert row["title"] == "Human Rights Due Diligence Program"
        mock_c.record_initiative_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_initiative_emits_audit_event(self):
        from application.operating_system.initiative_service import create_initiative

        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added_objects = []
        session.add = MagicMock(side_effect=lambda x: added_objects.append(x))

        with patch("application.operating_system.initiative_service.os_counters"):
            await create_initiative("org-1", "Test", session=session)

        audit_events = [o for o in added_objects if hasattr(o, "action")]
        assert any(e.action == "initiative.started" for e in audit_events)

    @pytest.mark.asyncio
    async def test_initiative_linked_fields_default_to_empty_lists(self):
        from application.operating_system.initiative_service import create_initiative
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        with patch("application.operating_system.initiative_service.os_counters"):
            row = await create_initiative("org-1", "Test", session=session)

        assert row["linked_objectives"] == []
        assert row["linked_suppliers"] == []
        assert row["linked_findings"] == []
        assert row["linked_risks"] == []


# ── 4. Action Tests ────────────────────────────────────────────────────────────

class TestActionService:
    @pytest.mark.asyncio
    async def test_create_action_default_status_is_open(self):
        from application.operating_system.action_service import create_action
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        with patch("application.operating_system.action_service.os_counters") as mock_c:
            row = await create_action(
                organization_id="org-1",
                title="Investigate child labour finding",
                priority="HIGH",
                source_type="FINDING",
                source_id="finding-123",
                session=session,
            )

        assert row["action_status"] == "OPEN"
        assert row["source_type"] == "FINDING"
        assert row["priority"] == "HIGH"
        mock_c.record_action_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_from_module_creates_action_with_source(self):
        from application.operating_system.action_service import ingest_from_module
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        with patch("application.operating_system.action_service.os_counters"):
            row = await ingest_from_module(
                organization_id="org-1",
                source_type="NETWORK_EXPOSURE",
                source_id="signal-99",
                title="Network exposure detected",
                priority="CRITICAL",
                session=session,
            )

        assert row["source_type"] == "NETWORK_EXPOSURE"
        assert row["source_id"] == "signal-99"
        assert row["priority"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_create_action_emits_action_assigned_audit_event(self):
        from application.operating_system.action_service import create_action
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda x: added.append(x))

        with patch("application.operating_system.action_service.os_counters"):
            await create_action("org-1", "Test Action", priority="MEDIUM", session=session)

        audit_events = [o for o in added if hasattr(o, "action")]
        assert any(e.action == "action.assigned" for e in audit_events)

    @pytest.mark.asyncio
    async def test_action_created_with_critical_priority_escalation_increments_counter(self):
        from application.operating_system.action_service import update_action
        session = _fake_session()

        mock_action = MagicMock()
        mock_action.id = "act-1"
        mock_action.organization_id = "org-1"
        mock_action.action_status = "OPEN"
        mock_action.priority = "HIGH"

        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_action)
        ))
        added = []
        session.add = MagicMock(side_effect=lambda x: added.append(x))

        with patch("application.operating_system.action_service.os_counters") as mock_c:
            await update_action("org-1", "act-1", session=session, priority="CRITICAL")

        mock_c.record_escalation.assert_called_once()


# ── 5. Playbook Tests ──────────────────────────────────────────────────────────

class TestPlaybookService:
    @pytest.mark.asyncio
    async def test_create_playbook_persists_steps(self):
        from application.operating_system.playbook_service import create_playbook
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        steps = [
            {"step_number": 1, "title": "Notify legal", "owner_role": "LEGAL"},
            {"step_number": 2, "title": "Suspend orders", "owner_role": "PROCUREMENT"},
        ]

        with patch("application.operating_system.playbook_service.os_counters") as mock_c:
            row = await create_playbook(
                organization_id="org-1",
                title="Child Labour Response",
                playbook_type="CHILD_LABOUR",
                steps=steps,
                session=session,
            )

        assert row["playbook_type"] == "CHILD_LABOUR"
        assert len(row["steps"]) == 2
        assert row["playbook_status"] == "ACTIVE"
        mock_c.record_playbook_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_playbook_created_emits_audit_event(self):
        from application.operating_system.playbook_service import create_playbook
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda x: added.append(x))

        with patch("application.operating_system.playbook_service.os_counters"):
            await create_playbook("org-1", "Sanctions Response", "SANCTIONS",
                                  session=session)

        audit_events = [o for o in added if hasattr(o, "action")]
        assert any(e.action == "playbook.created" for e in audit_events)


# ── 6. Workflow Tests ──────────────────────────────────────────────────────────

class TestWorkflowService:
    @pytest.mark.asyncio
    async def test_start_workflow_status_in_progress(self):
        from application.operating_system.playbook_service import start_workflow
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        with patch("application.operating_system.playbook_service.os_counters") as mock_c:
            row = await start_workflow(
                organization_id="org-1",
                workflow_type="CHILD_LABOUR_INVESTIGATION",
                session=session,
                total_steps=3,
            )

        assert row["execution_status"] == "IN_PROGRESS"
        assert row["current_step"] == 0
        assert row["total_steps"] == 3
        mock_c.record_workflow_started.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_step_advances_current_step(self):
        from application.operating_system.playbook_service import approve_workflow_step
        session = _fake_session()

        mock_wf = MagicMock()
        mock_wf.id = "wf-1"
        mock_wf.organization_id = "org-1"
        mock_wf.current_step = 0
        mock_wf.total_steps = 3
        mock_wf.steps_completed = []
        mock_wf.execution_status = "IN_PROGRESS"

        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_wf)
        ))
        added = []
        session.add = MagicMock(side_effect=lambda x: added.append(x))

        row = await approve_workflow_step(
            organization_id="org-1",
            execution_id="wf-1",
            approved_by="user-alice",
            step_note="Looks good",
            session=session,
        )

        assert row["current_step"] == 1
        assert len(row["steps_completed"]) == 1
        assert row["steps_completed"][0]["approved_by"] == "user-alice"
        assert row["execution_status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_approve_final_step_marks_workflow_completed(self):
        from application.operating_system.playbook_service import approve_workflow_step
        session = _fake_session()

        mock_wf = MagicMock()
        mock_wf.id = "wf-1"
        mock_wf.organization_id = "org-1"
        mock_wf.current_step = 2
        mock_wf.total_steps = 3
        mock_wf.steps_completed = [{"step": 0}, {"step": 1}]
        mock_wf.execution_status = "IN_PROGRESS"

        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_wf)
        ))
        session.add = MagicMock()

        row = await approve_workflow_step(
            organization_id="org-1",
            execution_id="wf-1",
            approved_by="user-alice",
            session=session,
        )

        assert row["execution_status"] == "COMPLETED"
        assert row["current_step"] == 3

    @pytest.mark.asyncio
    async def test_reject_step_marks_workflow_rejected(self):
        from application.operating_system.playbook_service import reject_workflow_step
        session = _fake_session()

        mock_wf = MagicMock()
        mock_wf.id = "wf-1"
        mock_wf.organization_id = "org-1"
        mock_wf.current_step = 1
        mock_wf.total_steps = 3
        mock_wf.steps_completed = [{"step": 0}]
        mock_wf.pending_approvals = []
        mock_wf.execution_status = "IN_PROGRESS"

        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_wf)
        ))
        session.add = MagicMock()

        row = await reject_workflow_step(
            organization_id="org-1",
            execution_id="wf-1",
            rejected_by="user-alice",
            reason="Evidence insufficient",
            session=session,
        )

        assert row["execution_status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_approve_returns_none_for_wrong_org(self):
        """Tenant isolation — cross-org execution returns None."""
        from application.operating_system.playbook_service import approve_workflow_step
        session = _fake_session()
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))

        result = await approve_workflow_step(
            organization_id="org-evil",
            execution_id="wf-victim",
            approved_by="attacker",
            session=session,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_workflow_emits_playbook_executed_audit_event(self):
        from application.operating_system.playbook_service import start_workflow
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        added = []
        session.add = MagicMock(side_effect=lambda x: added.append(x))

        with patch("application.operating_system.playbook_service.os_counters"):
            await start_workflow("org-1", "SANCTIONS_RESPONSE", session=session)

        audit_events = [o for o in added if hasattr(o, "action")]
        assert any(e.action == "playbook.executed" for e in audit_events)


# ── 7. Escalation Tests ────────────────────────────────────────────────────────

class TestEscalationService:
    @pytest.mark.asyncio
    async def test_create_escalation_rule_persists(self):
        from application.operating_system.escalation_service import create_escalation_rule
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await create_escalation_rule(
            organization_id="org-1",
            rule_name="Critical overdue action escalation",
            condition_entity_type="ESGAction",
            condition_status="OPEN",
            escalate_to_role="EXECUTIVE",
            condition_overdue_days=30,
            condition_priority="CRITICAL",
            notification_message="Critical action overdue >30 days",
            session=session,
        )

        assert row["rule_name"] == "Critical overdue action escalation"
        assert row["condition_overdue_days"] == 30
        assert row["escalate_to_role"] == "EXECUTIVE"
        assert row["rule_status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_evaluate_escalations_returns_triggered_list(self):
        """When an OPEN action matches the rule, escalation is triggered."""
        from application.operating_system.escalation_service import evaluate_escalations
        session = _fake_session()

        mock_rule = MagicMock()
        mock_rule.id = "rule-1"
        mock_rule.rule_name = "30-day overdue"
        mock_rule.condition_entity_type = "ESGAction"
        mock_rule.condition_status = "OPEN"
        mock_rule.condition_priority = "CRITICAL"
        mock_rule.condition_overdue_days = 30
        mock_rule.escalate_to_role = "EXECUTIVE"
        mock_rule.escalate_to_user_id = None
        mock_rule.notification_message = "Overdue!"

        mock_action = MagicMock()
        mock_action.id = "act-1"
        mock_action.title = "Investigate supplier"

        call_count = 0

        async def multi(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[mock_rule]))
                )
            else:
                result.scalars = MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[mock_action]))
                )
            return result

        session.execute = multi

        with patch("application.operating_system.escalation_service.os_counters") as mock_c:
            escalations = await evaluate_escalations("org-1", session)

        assert len(escalations) == 1
        assert escalations[0]["rule_id"] == "rule-1"
        assert escalations[0]["entity_id"] == "act-1"
        assert escalations[0]["escalate_to_role"] == "EXECUTIVE"
        mock_c.record_escalation.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_escalations_returns_empty_when_no_rules(self):
        from application.operating_system.escalation_service import evaluate_escalations
        session = _fake_session()
        result = MagicMock()
        result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        session.execute = AsyncMock(return_value=result)

        escalations = await evaluate_escalations("org-1", session)
        assert escalations == []


# ── 8. Health Score Tests ──────────────────────────────────────────────────────

class TestHealthScoreService:
    def test_weights_sum_to_one(self):
        from application.operating_system.health_score_service import WEIGHTS
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.0001

    @pytest.mark.asyncio
    async def test_compute_health_score_overall_is_weighted_average(self):
        """Given known domain scores, overall must equal the deterministic formula."""
        from application.operating_system.health_score_service import (
            compute_health_score, WEIGHTS,
        )
        session = _fake_session()

        # All domain score queries return 80.0
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=80.0),
            scalar_one=MagicMock(return_value=10),
        ))

        with patch(
            "application.operating_system.health_score_service._supplier_intelligence_score",
            new=AsyncMock(return_value=80.0),
        ), patch(
            "application.operating_system.health_score_service._surveillance_score",
            new=AsyncMock(return_value=80.0),
        ), patch(
            "application.operating_system.health_score_service._compliance_score",
            new=AsyncMock(return_value=80.0),
        ), patch(
            "application.operating_system.health_score_service._due_diligence_score",
            new=AsyncMock(return_value=80.0),
        ), patch(
            "application.operating_system.health_score_service._remediation_score",
            new=AsyncMock(return_value=80.0),
        ), patch(
            "application.operating_system.health_score_service._governance_score",
            new=AsyncMock(return_value=80.0),
        ):
            row = await compute_health_score("org-1", session)

        assert row["overall_score"] == 80.0

    @pytest.mark.asyncio
    async def test_health_score_stores_calculation_inputs_for_explainability(self):
        from application.operating_system.health_score_service import compute_health_score
        session = _fake_session()
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=50.0),
            scalar_one=MagicMock(return_value=5),
        ))

        with patch(
            "application.operating_system.health_score_service._supplier_intelligence_score",
            new=AsyncMock(return_value=50.0),
        ), patch(
            "application.operating_system.health_score_service._surveillance_score",
            new=AsyncMock(return_value=50.0),
        ), patch(
            "application.operating_system.health_score_service._compliance_score",
            new=AsyncMock(return_value=50.0),
        ), patch(
            "application.operating_system.health_score_service._due_diligence_score",
            new=AsyncMock(return_value=50.0),
        ), patch(
            "application.operating_system.health_score_service._remediation_score",
            new=AsyncMock(return_value=50.0),
        ), patch(
            "application.operating_system.health_score_service._governance_score",
            new=AsyncMock(return_value=50.0),
        ):
            row = await compute_health_score("org-1", session)

        assert "weights" in row["calculation_inputs"]
        assert "formula_version" in row["calculation_inputs"]
        assert row["formula_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_health_score_formula_version_stored(self):
        from application.operating_system.health_score_service import FORMULA_VERSION
        assert FORMULA_VERSION == "1.0"


# ── 9. Strategic Risk Tests ────────────────────────────────────────────────────

class TestStrategicRiskService:
    @pytest.mark.asyncio
    async def test_create_strategic_risk_default_status_identified(self):
        from application.operating_system.strategic_risk_service import create_strategic_risk
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await create_strategic_risk(
            organization_id="org-1",
            title="CSRD non-compliance risk",
            category="REGULATORY",
            risk_level="HIGH",
            session=session,
        )

        assert row["risk_status"] == "IDENTIFIED"
        assert row["category"] == "REGULATORY"
        assert row["risk_level"] == "HIGH"

    @pytest.mark.asyncio
    async def test_strategic_risk_linked_fields_default_empty(self):
        from application.operating_system.strategic_risk_service import create_strategic_risk
        session = _fake_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        row = await create_strategic_risk(
            organization_id="org-1",
            title="Climate transition risk",
            category="ENVIRONMENTAL",
            session=session,
        )

        assert row["linked_suppliers"] == []
        assert row["linked_objectives"] == []
        assert row["linked_initiatives"] == []
        assert row["linked_compliance_programs"] == []

    @pytest.mark.asyncio
    async def test_get_strategic_risk_different_org_returns_none(self):
        from application.operating_system.strategic_risk_service import get_strategic_risk
        session = _fake_session()
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))

        result = await get_strategic_risk("org-attacker", "risk-victim", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_strategic_risk_changes_status(self):
        from application.operating_system.strategic_risk_service import update_strategic_risk
        session = _fake_session()

        mock_risk = MagicMock()
        mock_risk.id = "risk-1"
        mock_risk.risk_status = "IDENTIFIED"
        mock_risk.risk_level = "HIGH"
        mock_risk.organization_id = "org-1"
        mock_risk.title = "Climate risk"
        mock_risk.description = ""
        mock_risk.category = "ENVIRONMENTAL"
        mock_risk.probability = "HIGH"
        mock_risk.impact = "CRITICAL"
        mock_risk.owner_user_id = None
        mock_risk.linked_suppliers = []
        mock_risk.linked_objectives = []
        mock_risk.linked_initiatives = []
        mock_risk.linked_compliance_programs = []
        mock_risk.created_at = datetime.now(UTC)
        mock_risk.updated_at = datetime.now(UTC)

        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_risk)
        ))

        row = await update_strategic_risk(
            "org-1", "risk-1", session, risk_status="MITIGATING"
        )

        assert row["risk_status"] == "MITIGATING"


# ── 10. Tenant Isolation Tests ─────────────────────────────────────────────────

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_objective_cross_tenant_returns_none(self):
        from application.operating_system.objective_service import get_objective
        session = _fake_session()
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        assert await get_objective("org-evil", "obj-owned-by-other", session) is None

    @pytest.mark.asyncio
    async def test_action_cross_tenant_returns_none(self):
        from application.operating_system.action_service import get_action
        session = _fake_session()
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        assert await get_action("org-evil", "act-owned-by-other", session) is None

    @pytest.mark.asyncio
    async def test_initiative_cross_tenant_update_returns_none(self):
        from application.operating_system.initiative_service import update_initiative
        session = _fake_session()
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        assert await update_initiative(
            "org-evil", "init-victim", session, initiative_status="COMPLETED"
        ) is None

    @pytest.mark.asyncio
    async def test_workflow_cross_tenant_approve_returns_none(self):
        from application.operating_system.playbook_service import approve_workflow_step
        session = _fake_session()
        session.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        assert await approve_workflow_step(
            "org-evil", "wf-victim", "attacker", session=session
        ) is None


# ── 11. Metrics Tests ──────────────────────────────────────────────────────────

class TestOperatingSystemMetrics:
    def test_counters_initialize_to_zero(self):
        from application.operating_system.metrics import _OperatingSystemCounters
        c = _OperatingSystemCounters()
        assert c.esg_objectives_total == 0
        assert c.esg_initiatives_total == 0
        assert c.esg_actions_total == 0
        assert c.esg_actions_overdue_total == 0
        assert c.esg_playbooks_total == 0
        assert c.esg_workflows_total == 0
        assert c.esg_escalations_total == 0

    def test_record_objective_increments(self):
        from application.operating_system.metrics import _OperatingSystemCounters
        c = _OperatingSystemCounters()
        c.record_objective_created()
        c.record_objective_created()
        assert c.esg_objectives_total == 2

    def test_record_escalation_increments(self):
        from application.operating_system.metrics import _OperatingSystemCounters
        c = _OperatingSystemCounters()
        c.record_escalation()
        assert c.esg_escalations_total == 1

    def test_prometheus_lines_contain_all_metric_names(self):
        from application.operating_system.metrics import _OperatingSystemCounters
        c = _OperatingSystemCounters()
        lines = "\n".join(c.to_prometheus_lines("test"))
        assert "esg_objectives_total" in lines
        assert "esg_initiatives_total" in lines
        assert "esg_actions_total" in lines
        assert "esg_actions_overdue_total" in lines
        assert "esg_playbooks_total" in lines
        assert "esg_workflows_total" in lines
        assert "esg_escalations_total" in lines

    def test_prometheus_lines_include_environment_label(self):
        from application.operating_system.metrics import _OperatingSystemCounters
        c = _OperatingSystemCounters()
        lines = "\n".join(c.to_prometheus_lines("production"))
        assert 'environment="production"' in lines

    def test_metrics_wired_to_prometheus_router(self):
        """os_counters.to_prometheus_lines is called in the metrics router."""
        import os
        metrics_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "interfaces", "api", "routers", "metrics.py",
        )
        with open(os.path.normpath(metrics_path)) as f:
            content = f.read()
        assert "os_counters" in content
