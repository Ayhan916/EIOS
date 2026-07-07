"""M41.1 — AI Governance Hardening unit tests.

Covers all audit findings fixed in M41.1:

  TestM41Security          — actor attribution (no "system" actor)
  TestM41TenantIsolation   — cross-org mutations rejected via _assert_org_ownership
  TestM41WorkflowFSM       — terminal states (APPROVED/REJECTED/SKIPPED) are immutable
  TestM41PromptGovernance  — unapproved / cross-org prompts blocked; history preserved
  TestM41IncidentGovernance — HIGH/CRITICAL severity gate; idempotent resolution (409)
  TestM41Auditability      — drift resolution and regulation mapping creation emit audit events
  TestM41Pagination        — limit/offset wired through all list functions
  TestM41DecisionLogging   — pre-hashed values stored as-is; prompt approval enforced
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from application.ai_governance import (
    control_service,
    decision_service,
    incident_service,
    inventory_service,
    monitoring_service,
    prompt_service,
)
from application.ai_governance.inventory_service import (
    AIGovernanceConflict,
    AIGovernanceError,
    _assert_org_ownership,
)
from infrastructure.persistence.models.ai_governance import (
    HIGH_SEVERITY_LEVELS,
    TERMINAL_WORKFLOW_STATUSES,
    AIDecisionLogModel,
    AIIncidentModel,
    AIModelModel,
    AIRegulationMappingHistoryModel,
    AIRegulationMappingModel,
    HumanReviewModel,
    ModelApprovalWorkflowModel,
    PromptChangeModel,
    PromptTemplateModel,
)

# ── Shared helpers ────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(UTC)


def _flush_session(get_return=None):
    s = MagicMock()
    s.get.return_value = get_return
    added = []
    s.add.side_effect = lambda obj: added.append(obj)
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.offset.return_value = q
    q.all.return_value = []
    q.count.return_value = 0
    q.first.return_value = None
    s.query.return_value = q
    return s, added


def _mock_model(model_id="m1", org="org1", status="DRAFT"):
    m = MagicMock(spec=AIModelModel)
    m.id = model_id
    m.organization_id = org
    m.ai_status = status
    return m


def _mock_incident(incident_id="inc1", org="org1", severity="LOW", resolved=False):
    i = MagicMock(spec=AIIncidentModel)
    i.id = incident_id
    i.organization_id = org
    i.severity = severity
    i.is_resolved = resolved
    return i


def _mock_prompt(prompt_id="pt1", org="org1", approved=True, text="hello"):
    pt = MagicMock(spec=PromptTemplateModel)
    pt.id = prompt_id
    pt.organization_id = org
    pt.is_approved = approved
    pt.prompt_text = text
    pt.prompt_version = 1
    return pt


def _mock_workflow(wf_id="wf1", model_id="m1", stage="risk_review", stage_status="PENDING"):
    wf = MagicMock(spec=ModelApprovalWorkflowModel)
    wf.id = wf_id
    wf.model_id = model_id
    wf.stage = stage
    wf.stage_status = stage_status
    return wf


def _mock_mapping(mapping_id="rm1", org="org1", status="NOT_ASSESSED"):
    rm = MagicMock(spec=AIRegulationMappingModel)
    rm.id = mapping_id
    rm.organization_id = org
    rm.compliance_status = status
    return rm


# ── TestM41Security ───────────────────────────────────────────────────────────


class TestM41Security:
    """Services must attribute actions to a real actor_id, not 'system'."""

    def test_register_model_records_actor(self):
        s, added = _flush_session()
        inventory_service.register_ai_model(
            organization_id="org1",
            name="TestModel",
            provider="Anthropic",
            model_type="LLM",
            actor_id="user-abc",
            session=s,
        )
        model = added[0]
        assert model.created_by == "user-abc"
        assert model.updated_by == "user-abc"

    def test_report_incident_records_actor(self):
        s, added = _flush_session()
        incident_service.report_incident(
            model_id="m1",
            organization_id="org1",
            incident_type="HALLUCINATION",
            severity="LOW",
            description="test",
            actor_id="reviewer-xyz",
            session=s,
        )
        inc = added[0]
        assert inc.created_by == "reviewer-xyz"

    def test_approve_prompt_records_actor(self):
        pt = _mock_prompt(approved=False)
        s, added = _flush_session(get_return=pt)
        with patch("application.ai_governance.prompt_service.emit_audit_event"):
            prompt_service.approve_prompt_template("pt1", "approver-1", s, organization_id="org1")
        assert pt.approved_by == "approver-1"

    def test_resolve_drift_alert_records_actor(self):
        model = _mock_model()
        alert = MagicMock()
        alert.id = "alert1"
        alert.organization_id = "org1"
        alert.is_resolved = False

        s = MagicMock()
        # get(AIModelModel) called second for model lookup
        s.get.side_effect = [alert, model]
        added = []
        s.add.side_effect = lambda obj: added.append(obj)
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = model
        s.query.return_value = q

        with patch("application.ai_governance.monitoring_service.emit_audit_event") as mock_emit:
            monitoring_service.resolve_drift_alert(
                "alert1", "ops-engineer", s, organization_id="org1"
            )
        # audit event must use real actor
        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args.kwargs
        assert call_kwargs["actor_id"] == "ops-engineer"


# ── TestM41TenantIsolation ────────────────────────────────────────────────────


class TestM41TenantIsolation:
    """Cross-tenant mutations must raise AIGovernanceError."""

    def test_assert_org_ownership_raises_on_wrong_org(self):
        record = MagicMock()
        record.organization_id = "org-A"
        with pytest.raises(AIGovernanceError, match="not found"):
            _assert_org_ownership(record, "org-B", "Model")

    def test_assert_org_ownership_raises_on_none(self):
        with pytest.raises(AIGovernanceError, match="not found"):
            _assert_org_ownership(None, "org-A", "Model")

    def test_assert_org_ownership_passes_on_match(self):
        record = MagicMock()
        record.organization_id = "org-A"
        _assert_org_ownership(record, "org-A", "Model")  # no raise

    def test_update_model_status_cross_org_blocked(self):
        model = _mock_model(org="org-A")
        s, _ = _flush_session(get_return=model)
        with pytest.raises(AIGovernanceError):
            inventory_service.update_ai_model_status(
                "m1", "ACTIVE", "attacker", s, organization_id="org-B"
            )

    def test_resolve_incident_cross_org_blocked(self):
        inc = _mock_incident(org="org-A")
        s, _ = _flush_session(get_return=inc)
        with pytest.raises(AIGovernanceError):
            incident_service.resolve_incident("inc1", "attacker", s, organization_id="org-B")

    def test_approve_prompt_cross_org_blocked(self):
        pt = _mock_prompt(org="org-A", approved=False)
        s, _ = _flush_session(get_return=pt)
        with pytest.raises(AIGovernanceError):
            prompt_service.approve_prompt_template("pt1", "attacker", s, organization_id="org-B")

    def test_revise_prompt_cross_org_blocked(self):
        pt = _mock_prompt(org="org-A")
        s, _ = _flush_session(get_return=pt)
        with pytest.raises(AIGovernanceError):
            prompt_service.revise_prompt_template(
                prompt_id="pt1",
                new_text="new",
                change_rationale="rationale",
                actor_id="attacker",
                session=s,
                organization_id="org-B",
            )

    def test_update_regulation_mapping_cross_org_blocked(self):
        rm = _mock_mapping(org="org-A")
        s, _ = _flush_session(get_return=rm)
        with pytest.raises(AIGovernanceError):
            control_service.update_regulation_mapping_status(
                "rm1", "COMPLIANT", "attacker", s, organization_id="org-B"
            )


# ── TestM41WorkflowFSM ────────────────────────────────────────────────────────


class TestM41WorkflowFSM:
    """Terminal workflow states must be immutable."""

    def test_terminal_statuses_defined(self):
        assert frozenset({"APPROVED", "REJECTED", "SKIPPED"}) == TERMINAL_WORKFLOW_STATUSES

    @pytest.mark.parametrize("terminal_status", ["APPROVED", "REJECTED", "SKIPPED"])
    def test_terminal_state_raises_conflict(self, terminal_status):
        wf = _mock_workflow(stage_status=terminal_status)
        model = _mock_model()
        s = MagicMock()
        # query(ModelApprovalWorkflowModel).filter().first() → wf
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = wf
        s.query.return_value = q
        s.get.return_value = model

        with pytest.raises(AIGovernanceConflict, match="terminal"):
            inventory_service.advance_approval_stage(
                model_id="m1",
                stage="risk_assessment",
                actor_id="u1",
                session=s,
                organization_id="org1",
            )

    def test_pending_state_allows_transition(self):
        wf = _mock_workflow(stage_status="PENDING")
        model = _mock_model()
        s = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = wf
        s.query.return_value = q
        s.get.return_value = model

        with patch("application.ai_governance.inventory_service.emit_audit_event"):
            result = inventory_service.advance_approval_stage(
                model_id="m1",
                stage="risk_assessment",
                actor_id="u1",
                session=s,
                organization_id="org1",
            )
        # no exception — transition succeeded
        assert result is wf


# ── TestM41PromptGovernance ───────────────────────────────────────────────────


class TestM41PromptGovernance:
    """Prompt approval, cross-org rejection, and history preservation."""

    def test_revise_prompt_preserves_previous_text(self):
        pt = _mock_prompt(text="original text")
        s, added = _flush_session(get_return=pt)
        with patch("application.ai_governance.prompt_service.emit_audit_event"):
            prompt_service.revise_prompt_template(
                prompt_id="pt1",
                new_text="updated text",
                change_rationale="improved clarity",
                actor_id="u1",
                session=s,
                organization_id="org1",
            )
        change = next(obj for obj in added if isinstance(obj, PromptChangeModel))
        assert change.previous_prompt_text == "original text"
        assert change.new_prompt_text == "updated text"

    def test_revise_prompt_unapproves_template(self):
        pt = _mock_prompt(approved=True)
        s, added = _flush_session(get_return=pt)
        with patch("application.ai_governance.prompt_service.emit_audit_event"):
            prompt_service.revise_prompt_template(
                prompt_id="pt1",
                new_text="new text",
                change_rationale="reason",
                actor_id="u1",
                session=s,
                organization_id="org1",
            )
        assert pt.is_approved is False

    def test_unapproved_prompt_blocked_in_decision_log(self):
        pt = _mock_prompt(approved=False)
        s, _ = _flush_session(get_return=pt)
        with pytest.raises(AIGovernanceError, match="not approved"):
            decision_service.log_ai_decision(
                model_id="m1",
                organization_id="org1",
                inputs_hash="a" * 64,
                output_hash="b" * 64,
                actor_id="u1",
                session=s,
                prompt_id="pt1",
            )

    def test_cross_org_prompt_blocked_in_decision_log(self):
        pt = _mock_prompt(org="org-other", approved=True)
        s, _ = _flush_session(get_return=pt)
        with pytest.raises(AIGovernanceError, match="organization"):
            decision_service.log_ai_decision(
                model_id="m1",
                organization_id="org1",
                inputs_hash="a" * 64,
                output_hash="b" * 64,
                actor_id="u1",
                session=s,
                prompt_id="pt1",
            )

    def test_nonexistent_prompt_blocked_in_decision_log(self):
        s, _ = _flush_session(get_return=None)
        with pytest.raises(AIGovernanceError, match="organization"):
            decision_service.log_ai_decision(
                model_id="m1",
                organization_id="org1",
                inputs_hash="a" * 64,
                output_hash="b" * 64,
                actor_id="u1",
                session=s,
                prompt_id="nonexistent",
            )


# ── TestM41IncidentGovernance ─────────────────────────────────────────────────


class TestM41IncidentGovernance:
    """HIGH/CRITICAL incidents require human review; resolution is idempotent."""

    def test_high_severity_constants_defined(self):
        assert frozenset({"HIGH", "CRITICAL"}) == HIGH_SEVERITY_LEVELS

    @pytest.mark.parametrize("severity", ["HIGH", "CRITICAL"])
    def test_high_severity_incident_requires_human_review(self, severity):
        inc = _mock_incident(severity=severity, resolved=False)
        s, _ = _flush_session(get_return=inc)
        # query().filter().first() returns None → no human review
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        s.query.return_value = q

        with pytest.raises(AIGovernanceError, match="human review"):
            incident_service.resolve_incident("inc1", "u1", s, organization_id="org1")

    @pytest.mark.parametrize("severity", ["HIGH", "CRITICAL"])
    def test_high_severity_resolves_with_approved_review(self, severity):
        inc = _mock_incident(severity=severity, resolved=False)
        review = MagicMock(spec=HumanReviewModel)
        review.decision = "APPROVED"
        s, _ = _flush_session(get_return=inc)
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = review
        s.query.return_value = q

        with patch("application.ai_governance.incident_service.emit_audit_event"):
            result = incident_service.resolve_incident("inc1", "u1", s, organization_id="org1")
        assert result.is_resolved is True

    def test_low_severity_resolves_without_review(self):
        inc = _mock_incident(severity="LOW", resolved=False)
        s, _ = _flush_session(get_return=inc)
        with patch("application.ai_governance.incident_service.emit_audit_event"):
            result = incident_service.resolve_incident("inc1", "u1", s, organization_id="org1")
        assert result.is_resolved is True

    def test_already_resolved_raises_conflict(self):
        inc = _mock_incident(resolved=True)
        s, _ = _flush_session(get_return=inc)
        with pytest.raises(AIGovernanceConflict, match="already resolved"):
            incident_service.resolve_incident("inc1", "u1", s, organization_id="org1")


# ── TestM41Auditability ───────────────────────────────────────────────────────


class TestM41Auditability:
    """Governance actions must emit named audit events."""

    def test_drift_alert_resolution_emits_audit_event(self):
        alert = MagicMock()
        alert.id = "alert1"
        alert.organization_id = "org1"
        alert.is_resolved = False
        model = _mock_model()

        s = MagicMock()
        s.get.return_value = alert
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = model
        s.query.return_value = q
        added = []
        s.add.side_effect = lambda obj: added.append(obj)

        with patch("application.ai_governance.monitoring_service.emit_audit_event") as mock_emit:
            monitoring_service.resolve_drift_alert("alert1", "u1", s, organization_id="org1")
        mock_emit.assert_called_once()
        assert mock_emit.call_args.kwargs["event_type"] == "ai.drift_alert.resolved"

    def test_regulation_mapping_creation_emits_audit_event(self):
        s, added = _flush_session()
        with patch("application.ai_governance.control_service.emit_audit_event") as mock_emit:
            control_service.create_regulation_mapping(
                framework="EU_AI_ACT",
                organization_id="org1",
                actor_id="u1",
                session=s,
            )
        mock_emit.assert_called_once()
        assert mock_emit.call_args.kwargs["event_type"] == "ai.regulation_mapping.created"

    def test_regulation_mapping_status_change_emits_audit_event(self):
        rm = _mock_mapping()
        s, added = _flush_session(get_return=rm)
        with patch("application.ai_governance.control_service.emit_audit_event") as mock_emit:
            control_service.update_regulation_mapping_status(
                "rm1", "COMPLIANT", "u1", s, organization_id="org1"
            )
        mock_emit.assert_called_once()
        assert mock_emit.call_args.kwargs["event_type"] == "ai.regulation_mapping.status_changed"

    def test_regulation_mapping_status_change_creates_history_record(self):
        rm = _mock_mapping(status="NOT_ASSESSED")
        s, added = _flush_session(get_return=rm)
        with patch("application.ai_governance.control_service.emit_audit_event"):
            control_service.update_regulation_mapping_status(
                "rm1", "COMPLIANT", "u1", s, organization_id="org1"
            )
        history = next(obj for obj in added if isinstance(obj, AIRegulationMappingHistoryModel))
        assert history.previous_status == "NOT_ASSESSED"
        assert history.new_status == "COMPLIANT"
        assert history.changed_by == "u1"


# ── TestM41Pagination ─────────────────────────────────────────────────────────


class TestM41Pagination:
    """All list functions must pass limit/offset through to the query."""

    def test_list_ai_models_respects_limit_offset(self):
        s = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.offset.return_value = q
        q.all.return_value = []
        s.query.return_value = q
        inventory_service.list_ai_models("org1", s, limit=10, offset=5)
        q.limit.assert_called_with(10)
        q.offset.assert_called_with(5)

    def test_list_incidents_respects_limit_offset(self):
        s = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.offset.return_value = q
        q.all.return_value = []
        s.query.return_value = q
        incident_service.list_incidents("org1", s, limit=20, offset=40)
        q.limit.assert_called_with(20)
        q.offset.assert_called_with(40)

    def test_list_decision_logs_respects_limit_offset(self):
        s = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.offset.return_value = q
        q.all.return_value = []
        s.query.return_value = q
        decision_service.list_decision_logs("m1", s, limit=100, offset=50)
        q.limit.assert_called_with(100)
        q.offset.assert_called_with(50)

    def test_list_regulation_mappings_respects_limit_offset(self):
        s = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.offset.return_value = q
        q.all.return_value = []
        s.query.return_value = q
        control_service.list_regulation_mappings("org1", s, limit=5, offset=0)
        q.limit.assert_called_with(5)
        q.offset.assert_called_with(0)

    def test_list_drift_alerts_respects_limit_offset(self):
        s = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.join.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.offset.return_value = q
        q.all.return_value = []
        s.query.return_value = q
        monitoring_service.list_drift_alerts("m1", s, limit=15, offset=30)
        q.limit.assert_called_with(15)
        q.offset.assert_called_with(30)


# ── TestM41DecisionLogging ────────────────────────────────────────────────────


class TestM41DecisionLogging:
    """Decision log service stores pre-hashed values as-is (no re-hash)."""

    def test_prehashed_values_stored_verbatim(self):
        pre_hash_in = "c" * 64
        pre_hash_out = "d" * 64
        s, added = _flush_session()
        decision_service.log_ai_decision(
            model_id="m1",
            organization_id="org1",
            inputs_hash=pre_hash_in,
            output_hash=pre_hash_out,
            actor_id="u1",
            session=s,
        )
        log = next(obj for obj in added if isinstance(obj, AIDecisionLogModel))
        assert log.inputs_hash == pre_hash_in
        assert log.output_hash == pre_hash_out

    def test_no_double_hash(self):
        """If service re-hashed, stored value would differ from the input."""
        pre_hash_in = "e" * 64
        pre_hash_out = "f" * 64
        s, added = _flush_session()
        decision_service.log_ai_decision(
            model_id="m1",
            organization_id="org1",
            inputs_hash=pre_hash_in,
            output_hash=pre_hash_out,
            actor_id="u1",
            session=s,
        )
        log = next(obj for obj in added if isinstance(obj, AIDecisionLogModel))
        # If double-hash occurred, SHA256("eeee...") would be stored — which is NOT "eeee..."
        assert log.inputs_hash == pre_hash_in, "Double-hash detected: service must not re-hash"

    def test_decision_without_prompt_id_allowed(self):
        s, added = _flush_session()
        decision_service.log_ai_decision(
            model_id="m1",
            organization_id="org1",
            inputs_hash="a" * 64,
            output_hash="b" * 64,
            actor_id="u1",
            session=s,
            prompt_id=None,
        )
        log = next(obj for obj in added if isinstance(obj, AIDecisionLogModel))
        assert log.prompt_id is None

    def test_approved_same_org_prompt_allowed(self):
        pt = _mock_prompt(approved=True, org="org1")
        s, added = _flush_session(get_return=pt)
        decision_service.log_ai_decision(
            model_id="m1",
            organization_id="org1",
            inputs_hash="a" * 64,
            output_hash="b" * 64,
            actor_id="u1",
            session=s,
            prompt_id="pt1",
        )
        log = next(obj for obj in added if isinstance(obj, AIDecisionLogModel))
        assert log.prompt_id == "pt1"
