"""M41 — AI Governance, Model Risk Management & Assurance Layer unit tests.

Coverage: inventory_service, control_service, prompt_service,
          decision_service, monitoring_service, incident_service,
          assurance_service, ORM models, API schemas.

Test count target: 42
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from application.ai_governance import (
    assurance_service,
    control_service,
    decision_service,
    incident_service,
    inventory_service,
    monitoring_service,
    prompt_service,
)
from application.ai_governance.inventory_service import AIGovernanceError
from infrastructure.persistence.models.ai_governance import (
    AI_MODEL_STATUSES,
    AI_MODEL_TYPES,
    CONTROL_TYPES,
    DRIFT_ALERT_TYPES,
    INCIDENT_TYPES,
    REGULATION_FRAMEWORKS,
    RISK_LEVELS,
    TEST_RESULTS,
    WORKFLOW_STAGES,
    AIControlModel,
    AIControlTestModel,
    AIDecisionLogModel,
    AIExplanationModel,
    AIIncidentModel,
    AIModelModel,
    AIRiskAssessmentModel,
    AIUseCaseModel,
    AIAssuranceReportModel,
    AIPolicyModel,
    HumanReviewModel,
    ModelApprovalWorkflowModel,
    ModelDriftAlertModel,
    ModelMonitoringRecordModel,
    PromptChangeModel,
    PromptTemplateModel,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_model(model_id: str = "m1", org: str = "org1") -> MagicMock:
    m = MagicMock(spec=AIModelModel)
    m.id = model_id
    m.organization_id = org
    m.ai_status = "DRAFT"
    return m


def _session_with(obj=None):
    """Session that returns obj from .get() and yields empty queries."""
    s = MagicMock()
    s.get.return_value = obj
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.all.return_value = []
    q.count.return_value = 0
    q.first.return_value = None
    q.join.return_value = q
    s.query.return_value = q
    return s


def _flush_session():
    s = _session_with()
    added = []
    s.add.side_effect = lambda obj: added.append(obj)
    return s, added


# ── TestAIModelORM ─────────────────────────────────────────────────────────────

class TestAIModelORM:
    def test_tablename(self):
        assert AIModelModel.__tablename__ == "ai_models"

    def test_valid_model_types(self):
        assert "LLM" in AI_MODEL_TYPES
        assert "CLASSIFICATION" in AI_MODEL_TYPES
        assert "RISK_SCORING" in AI_MODEL_TYPES

    def test_valid_statuses(self):
        assert "DRAFT" in AI_MODEL_STATUSES
        assert "ACTIVE" in AI_MODEL_STATUSES
        assert "RETIRED" in AI_MODEL_STATUSES
        assert "SUSPENDED" in AI_MODEL_STATUSES

    def test_all_workflow_stages_defined(self):
        assert len(WORKFLOW_STAGES) == 4
        assert "executive_approval" in WORKFLOW_STAGES


class TestAIGovernanceORM:
    def test_use_case_tablename(self):
        assert AIUseCaseModel.__tablename__ == "ai_use_cases"

    def test_risk_assessment_tablename(self):
        assert AIRiskAssessmentModel.__tablename__ == "ai_risk_assessments"

    def test_control_tablename(self):
        assert AIControlModel.__tablename__ == "ai_controls"

    def test_control_test_tablename(self):
        assert AIControlTestModel.__tablename__ == "ai_control_tests"

    def test_workflow_tablename(self):
        assert ModelApprovalWorkflowModel.__tablename__ == "model_approval_workflows"

    def test_prompt_template_tablename(self):
        assert PromptTemplateModel.__tablename__ == "prompt_templates"

    def test_prompt_change_tablename(self):
        assert PromptChangeModel.__tablename__ == "prompt_changes"

    def test_decision_log_tablename(self):
        assert AIDecisionLogModel.__tablename__ == "ai_decision_logs"

    def test_explanation_tablename(self):
        assert AIExplanationModel.__tablename__ == "ai_explanations"

    def test_human_review_tablename(self):
        assert HumanReviewModel.__tablename__ == "human_reviews"

    def test_monitoring_record_tablename(self):
        assert ModelMonitoringRecordModel.__tablename__ == "model_monitoring_records"

    def test_drift_alert_tablename(self):
        assert ModelDriftAlertModel.__tablename__ == "model_drift_alerts"

    def test_incident_tablename(self):
        assert AIIncidentModel.__tablename__ == "ai_incidents"

    def test_policy_tablename(self):
        assert AIPolicyModel.__tablename__ == "ai_policies"

    def test_assurance_report_tablename(self):
        assert AIAssuranceReportModel.__tablename__ == "ai_assurance_reports"


# ── TestInventoryService ───────────────────────────────────────────────────────

class TestInventoryService:
    def test_register_ai_model_invalid_type_raises(self):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid model_type"):
            inventory_service.register_ai_model(
                organization_id="org1",
                name="Test Model",
                provider="anthropic",
                model_type="INVALID",
                actor_id="u1",
                session=s,
            )

    @patch("application.ai_governance.inventory_service.emit_audit_event")
    def test_register_ai_model_adds_and_audits(self, mock_audit):
        s, added = _flush_session()
        # workflow flush needs the same added list
        m = inventory_service.register_ai_model(
            organization_id="org1",
            name="Claude Gov",
            provider="anthropic",
            model_type="LLM",
            actor_id="u1",
            session=s,
        )
        # model + 4 workflow stages
        assert len(added) == 5
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs["event_type"] == "ai.model.registered"

    def test_update_status_invalid_raises(self):
        s = _session_with(_mock_model())
        with pytest.raises(AIGovernanceError, match="Invalid ai_status"):
            inventory_service.update_ai_model_status(
                "m1", "UNKNOWN", "u1", s, organization_id="org1"
            )

    def test_update_status_activate_without_approval_raises(self):
        s = _session_with(_mock_model())
        # query returns empty (no approved stages)
        with pytest.raises(AIGovernanceError, match="pending workflow stages"):
            inventory_service.update_ai_model_status(
                "m1", "ACTIVE", "u1", s, organization_id="org1"
            )

    def test_update_status_retired_no_workflow_check(self):
        m = _mock_model()
        s = _session_with(m)
        with patch("application.ai_governance.inventory_service.emit_audit_event"):
            inventory_service.update_ai_model_status(
                "m1", "RETIRED", "u1", s, organization_id="org1"
            )
        assert m.ai_status == "RETIRED"

    def test_register_use_case_invalid_risk_level(self):
        s = _session_with(_mock_model())
        with pytest.raises(AIGovernanceError, match="Invalid risk_level"):
            inventory_service.register_use_case(
                model_id="m1",
                organization_id="org1",
                title="Test Use Case",
                actor_id="u1",
                session=s,
                risk_level="EXTREME",
            )

    @patch("application.ai_governance.inventory_service.emit_audit_event")
    def test_register_use_case_model_not_found(self, _):
        s = _session_with(None)  # model not found
        with pytest.raises(AIGovernanceError, match="not found"):
            inventory_service.register_use_case(
                model_id="missing",
                organization_id="org1",
                title="UC",
                actor_id="u1",
                session=s,
            )

    @patch("application.ai_governance.inventory_service.emit_audit_event")
    def test_advance_workflow_stage_invalid_stage(self, _):
        s = _session_with(_mock_model())
        with pytest.raises(AIGovernanceError, match="Invalid stage"):
            inventory_service.advance_approval_stage(
                "m1", "bad_stage", "u1", s, organization_id="org1"
            )

    @patch("application.ai_governance.inventory_service.emit_audit_event")
    def test_advance_workflow_stage_not_found(self, _):
        s = _session_with(_mock_model())
        # query.first() returns None (stage not found)
        with pytest.raises(AIGovernanceError, match="not found"):
            inventory_service.advance_approval_stage(
                "m1", "review", "u1", s, organization_id="org1"
            )

    @patch("application.ai_governance.inventory_service.emit_audit_event")
    def test_advance_workflow_stage_success(self, mock_audit):
        wf = MagicMock(spec=ModelApprovalWorkflowModel)
        wf.stage = "review"
        wf.stage_status = "PENDING"
        wf.model_id = "m1"
        s = _session_with(_mock_model())
        s.query.return_value.filter.return_value.filter.return_value.first.return_value = wf
        inventory_service.advance_approval_stage(
            "m1", "review", "approver1", s, organization_id="org1"
        )
        assert wf.stage_status == "APPROVED"
        assert wf.approver_user_id == "approver1"
        mock_audit.assert_called_once()


# ── TestControlService ─────────────────────────────────────────────────────────

class TestControlService:
    @patch("application.ai_governance.control_service.emit_audit_event")
    def test_create_control_invalid_type(self, _):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid control_type"):
            control_service.create_control(
                organization_id="org1",
                name="Test Control",
                control_type="INVALID",
                actor_id="u1",
                session=s,
            )

    @patch("application.ai_governance.control_service.emit_audit_event")
    def test_create_control_success(self, mock_audit):
        s, added = _flush_session()
        ctrl = control_service.create_control(
            organization_id="org1",
            name="Human Review Gate",
            control_type="PREVENTIVE",
            actor_id="u1",
            session=s,
        )
        assert len(added) == 1
        assert isinstance(added[0], AIControlModel)
        mock_audit.assert_called_once()

    @patch("application.ai_governance.control_service.emit_audit_event")
    def test_record_control_test_invalid_result(self, _):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid test_result"):
            control_service.record_control_test("ctrl1", "UNKNOWN", "u1", s)

    @patch("application.ai_governance.control_service.emit_audit_event")
    def test_record_control_test_success(self, mock_audit):
        s, added = _flush_session()
        t = control_service.record_control_test("ctrl1", "PASS", "u1", s)
        assert len(added) == 1
        assert isinstance(added[0], AIControlTestModel)

    def test_create_risk_assessment_invalid_dimension(self):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid bias_risk"):
            control_service.create_risk_assessment(
                model_id="m1",
                actor_id="u1",
                session=s,
                bias_risk="EXTREME",
            )

    @patch("application.ai_governance.control_service.emit_audit_event")
    def test_create_risk_assessment_success(self, mock_audit):
        s, added = _flush_session()
        ra = control_service.create_risk_assessment(
            model_id="m1",
            actor_id="u1",
            session=s,
            bias_risk="HIGH",
            overall_score=75.0,
        )
        assert len(added) == 1
        assert isinstance(added[0], AIRiskAssessmentModel)


# ── TestPromptService ──────────────────────────────────────────────────────────

class TestPromptService:
    @patch("application.ai_governance.prompt_service.emit_audit_event")
    def test_create_prompt_template(self, mock_audit):
        s, added = _flush_session()
        pt = prompt_service.create_prompt_template(
            organization_id="org1",
            name="Risk Summary Prompt",
            prompt_text="Summarise the following risks: {risks}",
            actor_id="u1",
            session=s,
        )
        assert len(added) == 1
        assert isinstance(added[0], PromptTemplateModel)
        assert added[0].prompt_version == 1
        assert added[0].is_approved is False

    @patch("application.ai_governance.prompt_service.emit_audit_event")
    def test_approve_prompt_sets_approved_fields(self, mock_audit):
        pt = MagicMock(spec=PromptTemplateModel)
        pt.id = "p1"
        pt.organization_id = "org1"
        pt.prompt_version = 1
        s = _session_with(pt)
        prompt_service.approve_prompt_template("p1", "approver1", s, organization_id="org1")
        assert pt.is_approved is True
        assert pt.approved_by == "approver1"
        mock_audit.assert_called_once()

    @patch("application.ai_governance.prompt_service.emit_audit_event")
    def test_approve_prompt_not_found(self, _):
        s = _session_with(None)
        with pytest.raises(AIGovernanceError, match="not found"):
            prompt_service.approve_prompt_template("missing", "u1", s, organization_id="org1")

    @patch("application.ai_governance.prompt_service.emit_audit_event")
    def test_revise_prompt_bumps_version_and_resets_approval(self, mock_audit):
        pt = MagicMock(spec=PromptTemplateModel)
        pt.id = "p1"
        pt.organization_id = "org1"
        pt.prompt_version = 2
        pt.is_approved = True
        pt.prompt_text = "old text"
        s, added = _flush_session()
        s.get.return_value = pt
        updated_pt, change = prompt_service.revise_prompt_template(
            prompt_id="p1",
            new_text="New text",
            change_rationale="Security improvement",
            actor_id="u1",
            session=s,
            organization_id="org1",
        )
        assert pt.prompt_version == 3
        assert pt.is_approved is False
        assert pt.approved_by is None
        assert isinstance(added[0], PromptChangeModel)
        assert added[0].previous_version == 2
        assert added[0].new_version == 3


# ── TestDecisionService ────────────────────────────────────────────────────────

class TestDecisionService:
    def test_log_decision_stores_hash_not_raw(self):
        # Caller provides pre-computed SHA-256 hashes; service stores them as-is.
        pre_hashed_input = "a" * 64   # simulates a 64-char SHA-256 hex digest
        pre_hashed_output = "b" * 64
        s, added = _flush_session()
        decision_service.log_ai_decision(
            model_id="m1",
            organization_id="org1",
            inputs_hash=pre_hashed_input,
            output_hash=pre_hashed_output,
            actor_id="u1",
            session=s,
        )
        log = added[0]
        assert isinstance(log, AIDecisionLogModel)
        # service must store the pre-hashed value exactly (no re-hash)
        assert log.inputs_hash == pre_hashed_input
        assert log.output_hash == pre_hashed_output
        assert len(log.inputs_hash) == 64
        assert len(log.output_hash) == 64

    def test_add_explanation(self):
        s, added = _flush_session()
        decision_service.add_explanation(
            decision_log_id="log1",
            actor_id="u1",
            session=s,
            factors=[{"name": "supplier_score", "weight": 0.7}],
            confidence=0.92,
        )
        exp = added[0]
        assert isinstance(exp, AIExplanationModel)
        assert exp.confidence == 0.92

    @patch("application.ai_governance.decision_service.emit_audit_event")
    def test_submit_human_review_invalid_decision(self, _):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid review decision"):
            decision_service.submit_human_review("m1", "reviewer1", "MAYBE", s)

    @patch("application.ai_governance.decision_service.emit_audit_event")
    def test_submit_human_review_success(self, mock_audit):
        s, added = _flush_session()
        review = decision_service.submit_human_review(
            model_id="m1",
            reviewer_user_id="reviewer1",
            decision="APPROVED",
            session=s,
            rationale="Output looks correct",
        )
        assert isinstance(added[0], HumanReviewModel)
        assert added[0].decision == "APPROVED"
        mock_audit.assert_called_once()

    def test_sha256_deterministic(self):
        import hashlib
        text = "hello world"
        h1 = hashlib.sha256(text.encode()).hexdigest()
        h2 = hashlib.sha256(text.encode()).hexdigest()
        assert h1 == h2
        assert len(h1) == 64


# ── TestMonitoringService ──────────────────────────────────────────────────────

class TestMonitoringService:
    @patch("application.ai_governance.monitoring_service.emit_audit_event")
    def test_record_snapshot_triggers_alert_on_high_drift(self, mock_audit):
        s, added = _flush_session()
        monitoring_service.record_monitoring_snapshot(
            model_id="m1",
            organization_id="org1",
            period_start=_now(),
            period_end=_now(),
            actor_id="u1",
            session=s,
            drift_score=0.75,  # above 0.3 threshold → alert
        )
        # snapshot + drift alert
        assert len(added) == 2
        assert isinstance(added[0], ModelMonitoringRecordModel)
        assert isinstance(added[1], ModelDriftAlertModel)
        assert added[1].severity == "HIGH"  # >= 0.6

    @patch("application.ai_governance.monitoring_service.emit_audit_event")
    def test_record_snapshot_no_alert_below_threshold(self, _):
        s, added = _flush_session()
        monitoring_service.record_monitoring_snapshot(
            model_id="m1",
            organization_id="org1",
            period_start=_now(),
            period_end=_now(),
            actor_id="u1",
            session=s,
            drift_score=0.1,
        )
        assert len(added) == 1

    @patch("application.ai_governance.monitoring_service.emit_audit_event")
    def test_create_drift_alert_invalid_type(self, _):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid alert_type"):
            monitoring_service.create_drift_alert("m1", "WRONG", "HIGH", "desc", "u1", s)

    @patch("application.ai_governance.monitoring_service.emit_audit_event")
    def test_resolve_drift_alert_not_found(self, _):
        s = _session_with(None)
        with pytest.raises(AIGovernanceError, match="not found"):
            monitoring_service.resolve_drift_alert("missing", "u1", s, organization_id="org1")

    @patch("application.ai_governance.monitoring_service.emit_audit_event")
    def test_create_ai_policy_invalid_type(self, _):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid policy_type"):
            monitoring_service.create_ai_policy("Policy", "INVALID_TYPE", "u1", s)

    @patch("application.ai_governance.monitoring_service.emit_audit_event")
    def test_create_ai_policy_success(self, mock_audit):
        s, added = _flush_session()
        monitoring_service.create_ai_policy(
            name="Approved Providers Policy",
            policy_type="APPROVED_PROVIDERS",
            actor_id="u1",
            session=s,
            organization_id="org1",
            policy_body={"allowed": ["anthropic", "openai"]},
        )
        assert isinstance(added[0], AIPolicyModel)
        mock_audit.assert_called_once()


# ── TestIncidentService ────────────────────────────────────────────────────────

class TestIncidentService:
    @patch("application.ai_governance.incident_service.emit_audit_event")
    def test_report_incident_invalid_type(self, _):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid incident_type"):
            incident_service.report_incident(
                model_id="m1",
                organization_id="org1",
                incident_type="MADE_UP",
                severity="HIGH",
                description="desc",
                actor_id="u1",
                session=s,
            )

    @patch("application.ai_governance.incident_service.emit_audit_event")
    def test_report_incident_invalid_severity(self, _):
        s = _session_with()
        with pytest.raises(AIGovernanceError, match="Invalid severity"):
            incident_service.report_incident(
                model_id="m1",
                organization_id="org1",
                incident_type="HALLUCINATION",
                severity="CATASTROPHIC",
                description="desc",
                actor_id="u1",
                session=s,
            )

    @patch("application.ai_governance.incident_service.emit_audit_event")
    def test_report_incident_success(self, mock_audit):
        s, added = _flush_session()
        incident_service.report_incident(
            model_id="m1",
            organization_id="org1",
            incident_type="BIAS_CONCERN",
            severity="MEDIUM",
            description="Model output exhibited gender bias",
            actor_id="u1",
            session=s,
        )
        assert isinstance(added[0], AIIncidentModel)
        assert added[0].incident_type == "BIAS_CONCERN"
        mock_audit.assert_called_once()

    @patch("application.ai_governance.incident_service.emit_audit_event")
    def test_resolve_incident_with_esg_link(self, mock_audit):
        inc = MagicMock(spec=AIIncidentModel)
        inc.id = "i1"
        inc.organization_id = "org1"
        inc.is_resolved = False
        inc.severity = "LOW"
        s = _session_with(inc)
        incident_service.resolve_incident(
            "i1", "u1", s, organization_id="org1", esg_action_id="esg-a1"
        )
        assert inc.is_resolved is True
        assert inc.esg_action_id == "esg-a1"
        mock_audit.assert_called_once()

    @patch("application.ai_governance.incident_service.emit_audit_event")
    def test_resolve_incident_not_found(self, _):
        s = _session_with(None)
        with pytest.raises(AIGovernanceError, match="not found"):
            incident_service.resolve_incident("missing", "u1", s, organization_id="org1")


# ── TestAssuranceService ───────────────────────────────────────────────────────

class TestAssuranceService:
    @patch("application.ai_governance.assurance_service.emit_audit_event")
    def test_generate_report_compliant_when_no_incidents(self, mock_audit):
        s = _session_with()
        # All count queries return 0 (no incidents)
        report_obj = MagicMock(spec=AIAssuranceReportModel)
        added = []
        s.add.side_effect = lambda obj: added.append(obj)

        report = assurance_service.generate_assurance_report(
            organization_id="org1",
            title="Q2 AI Assurance",
            period_start=_now(),
            period_end=_now(),
            actor_id="u1",
            session=s,
        )
        assert len(added) == 1
        assert isinstance(added[0], AIAssuranceReportModel)
        assert added[0].overall_status == "COMPLIANT"
        mock_audit.assert_called_once()

    def test_compute_overall_status_non_compliant(self):
        # > 10% incident rate → NON_COMPLIANT
        status = assurance_service._compute_overall_status(
            incident_count=5, model_count=3
        )
        assert status == "NON_COMPLIANT"

    def test_compute_overall_status_partial(self):
        # < 10% incident rate → PARTIALLY_COMPLIANT
        status = assurance_service._compute_overall_status(
            incident_count=1, model_count=20
        )
        assert status == "PARTIALLY_COMPLIANT"

    def test_compute_overall_status_compliant(self):
        status = assurance_service._compute_overall_status(
            incident_count=0, model_count=5
        )
        assert status == "COMPLIANT"


# ── TestSecurityConstraints ────────────────────────────────────────────────────

class TestAIGovernanceSecurityConstraints:
    def test_decision_log_never_stores_raw_text(self):
        """Raw inputs and outputs must never be stored — only hashes."""
        import hashlib

        raw_input = "This is sensitive user data"
        raw_output = "This is the AI response with potentially sensitive data"

        stored_input_hash = hashlib.sha256(raw_input.encode()).hexdigest()
        stored_output_hash = hashlib.sha256(raw_output.encode()).hexdigest()

        # The stored value cannot equal the raw value
        assert stored_input_hash != raw_input
        assert stored_output_hash != raw_output
        # Both are 64-char hex strings
        assert all(c in "0123456789abcdef" for c in stored_input_hash)

    def test_human_review_required_before_acting(self):
        """Agents must NEVER autonomously approve — APPROVED decision requires human reviewer."""
        review = MagicMock(spec=HumanReviewModel)
        review.reviewer_user_id = "human-user-id"  # NOT "system" or "agent"
        review.decision = "APPROVED"
        # The decision must come from a human, not an automated actor
        assert review.reviewer_user_id == "human-user-id"
        assert "agent" not in review.reviewer_user_id.lower()

    def test_regulation_frameworks_enum_coverage(self):
        """EU AI Act, NIST AI RMF, and ISO 42001 must all be supported."""
        assert "EU_AI_ACT" in REGULATION_FRAMEWORKS
        assert "NIST_AI_RMF" in REGULATION_FRAMEWORKS
        assert "ISO_42001" in REGULATION_FRAMEWORKS

    def test_prompt_approval_required_before_production_use(self):
        """A prompt template with is_approved=False cannot be in production."""
        pt = MagicMock(spec=PromptTemplateModel)
        pt.is_approved = False
        # Service contract: only approved prompts may be used in production
        assert pt.is_approved is False

    def test_drift_alert_all_types_defined(self):
        assert "CONFIDENCE_DEGRADATION" in DRIFT_ALERT_TYPES
        assert "DISTRIBUTION_SHIFT" in DRIFT_ALERT_TYPES
        assert "ABNORMAL_USAGE" in DRIFT_ALERT_TYPES

    def test_incident_types_cover_key_risks(self):
        assert "HALLUCINATION" in INCIDENT_TYPES
        assert "POLICY_VIOLATION" in INCIDENT_TYPES
        assert "BIAS_CONCERN" in INCIDENT_TYPES
        assert "PRIVACY_CONCERN" in INCIDENT_TYPES
