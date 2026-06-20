"""M36 Unit Tests — Alert Engine, Escalation, and Draft Approval."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

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


def _make_finding(
    finding_id="f-1",
    severity="HIGH",
    confidence_score=0.85,
    category="RISK",
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
    f.title = "Test Finding"
    f.description = "Test description"
    f.source_data_json = source_data or {}
    return f


def _make_draft(draft_id="d-1", status="PENDING", finding_id="f-1"):
    d = MagicMock()
    d.id = draft_id
    d.draft_status = status
    d.agent_finding_id = finding_id
    d.organization_id = "org-1"
    d.approved_by = None
    d.approved_at = None
    d.rejection_reason = None
    d.updated_at = None
    return d


# ── create_alert ───────────────────────────────────────────────────────────────

class TestCreateAlert:
    async def test_creates_alert_record(self) -> None:
        from application.agent_monitoring.alert_service import create_alert

        # M36.2: create_alert now checks for duplicates via session.execute
        no_dup_result = MagicMock()
        no_dup_result.scalar_one_or_none = MagicMock(return_value=None)
        no_dup_result.scalars.return_value.all.return_value = []

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock(return_value=no_dup_result)

        alert = await create_alert(
            organization_id="org-1",
            agent_id="agent-1",
            severity="high",
            title="High Risk Detected",
            message="Risk score exceeded threshold",
            session=session,
        )

        assert session.add.called
        assert alert.severity == "HIGH"  # uppercased
        assert alert.organization_id == "org-1"
        assert alert.acknowledged_at is None

    async def test_alert_id_is_uuid(self) -> None:
        import re
        from application.agent_monitoring.alert_service import create_alert

        no_dup_result = MagicMock()
        no_dup_result.scalar_one_or_none = MagicMock(return_value=None)
        no_dup_result.scalars.return_value.all.return_value = []

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock(return_value=no_dup_result)

        alert = await create_alert(
            organization_id="org-1",
            agent_id="agent-1",
            severity="WARNING",
            title="Test",
            message="Test message",
            session=session,
        )
        assert re.match(r"[0-9a-f-]{36}", alert.id)


# ── Auto escalation logic ──────────────────────────────────────────────────────

class TestAutoEscalation:
    async def test_critical_finding_creates_critical_alert(self) -> None:
        from application.agent_monitoring.alert_service import evaluate_finding

        finding = _make_finding(severity="CRITICAL", confidence_score=0.9)

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        # M36.2: scalar_one_or_none=None ensures dedup check finds no existing alert
        rules_result = MagicMock()
        rules_result.scalar_one_or_none = MagicMock(return_value=None)
        rules_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=rules_result)

        alerts = await evaluate_finding(finding, "org-1", session)

        assert len(alerts) == 1
        assert alerts[0].severity == "CRITICAL"

    async def test_high_finding_with_high_confidence_creates_high_alert(self) -> None:
        from application.agent_monitoring.alert_service import evaluate_finding

        finding = _make_finding(severity="HIGH", confidence_score=0.80)

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        rules_result = MagicMock()
        rules_result.scalar_one_or_none = MagicMock(return_value=None)
        rules_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=rules_result)

        alerts = await evaluate_finding(finding, "org-1", session)

        assert len(alerts) == 1
        assert alerts[0].severity == "HIGH"

    async def test_high_finding_with_low_confidence_no_alert(self) -> None:
        from application.agent_monitoring.alert_service import evaluate_finding

        finding = _make_finding(severity="HIGH", confidence_score=0.50)

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        rules_result = MagicMock()
        rules_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=rules_result)

        alerts = await evaluate_finding(finding, "org-1", session)

        assert len(alerts) == 0

    async def test_low_severity_creates_no_auto_alert(self) -> None:
        from application.agent_monitoring.alert_service import evaluate_finding

        finding = _make_finding(severity="LOW", confidence_score=0.99)

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        rules_result = MagicMock()
        rules_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=rules_result)

        alerts = await evaluate_finding(finding, "org-1", session)

        assert len(alerts) == 0


# ── _matches_rule ──────────────────────────────────────────────────────────────

class TestMatchesRule:
    def test_severity_match(self) -> None:
        from application.agent_monitoring.alert_service import _matches_rule

        finding = _make_finding(severity="CRITICAL")
        assert _matches_rule(finding, {"metric": "severity", "value": "CRITICAL"})
        assert not _matches_rule(finding, {"metric": "severity", "value": "LOW"})

    def test_confidence_score_gt(self) -> None:
        from application.agent_monitoring.alert_service import _matches_rule

        finding = _make_finding(confidence_score=0.85)
        assert _matches_rule(finding, {"metric": "confidence_score", "operator": "gt", "threshold": 0.8})
        assert not _matches_rule(finding, {"metric": "confidence_score", "operator": "gt", "threshold": 0.9})

    def test_category_match(self) -> None:
        from application.agent_monitoring.alert_service import _matches_rule

        finding = _make_finding(category="RISK")
        assert _matches_rule(finding, {"metric": "category", "value": "RISK"})
        assert not _matches_rule(finding, {"metric": "category", "value": "COMPLIANCE"})

    def test_sanctions_exposure_from_source_data(self) -> None:
        from application.agent_monitoring.alert_service import _matches_rule

        finding_yes = _make_finding(source_data={"sanctions_exposure": True})
        finding_no = _make_finding(source_data={"sanctions_exposure": False})

        assert _matches_rule(finding_yes, {"metric": "sanctions_exposure"})
        assert not _matches_rule(finding_no, {"metric": "sanctions_exposure"})

    def test_risk_score_delta_lt(self) -> None:
        from application.agent_monitoring.alert_service import _matches_rule

        finding = _make_finding(source_data={"risk_score_delta": -15.0})
        assert _matches_rule(finding, {"metric": "risk_score_delta", "operator": "lt", "threshold": -10.0})
        assert not _matches_rule(finding, {"metric": "risk_score_delta", "operator": "lt", "threshold": -20.0})

    def test_unknown_metric_returns_false(self) -> None:
        from application.agent_monitoring.alert_service import _matches_rule

        finding = _make_finding()
        assert not _matches_rule(finding, {"metric": "nonexistent_metric"})


# ── User-defined escalation rules ──────────────────────────────────────────────

class TestUserDefinedEscalationRules:
    async def test_user_rule_creates_additional_alert(self) -> None:
        from application.agent_monitoring.alert_service import evaluate_finding

        finding = _make_finding(severity="MEDIUM", confidence_score=0.60, category="SANCTIONS")

        rule = MagicMock()
        rule.name = "Sanctions escalation"
        rule.condition_json = {"metric": "category", "value": "SANCTIONS"}
        rule.escalation_severity = "CRITICAL"

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        rules_result = MagicMock()
        rules_result.scalar_one_or_none = MagicMock(return_value=None)
        rules_result.scalars.return_value.all.return_value = [rule]
        session.execute = AsyncMock(return_value=rules_result)

        alerts = await evaluate_finding(finding, "org-1", session)

        # MEDIUM with conf 0.60 → no auto escalation; but user rule fires
        user_alerts = [a for a in alerts if "[Sanctions escalation]" in a.title]
        assert len(user_alerts) == 1
        assert user_alerts[0].severity == "CRITICAL"


# ── create_escalation_rule ─────────────────────────────────────────────────────

class TestCreateEscalationRule:
    async def test_creates_rule_record(self) -> None:
        from application.agent_monitoring.alert_service import create_escalation_rule

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        rule = await create_escalation_rule(
            organization_id="org-1",
            name="Test Rule",
            description="A test rule",
            condition_json={"metric": "severity", "value": "HIGH"},
            escalation_severity="critical",
            created_by="user-1",
            session=session,
        )

        session.add.assert_called_once()
        assert rule.organization_id == "org-1"
        assert rule.escalation_severity == "CRITICAL"
        assert rule.enabled is True


# ── Draft approval ─────────────────────────────────────────────────────────────

class TestDraftApproval:
    async def test_approve_pending_draft(self) -> None:
        from application.agent_monitoring.alert_service import approve_draft

        draft = _make_draft(status="PENDING", finding_id=None)
        session = _make_session(scalar_one_or_none=draft)

        result = await approve_draft("d-1", "org-1", "user-1", session)

        assert result.draft_status == "APPROVED"
        assert result.approved_by == "user-1"

    async def test_approve_non_pending_raises(self) -> None:
        from application.agent_monitoring.alert_service import approve_draft

        draft = _make_draft(status="REJECTED")
        session = _make_session(scalar_one_or_none=draft)

        with pytest.raises(ValueError, match="Cannot approve"):
            await approve_draft("d-1", "org-1", "user-1", session)

    async def test_approve_not_found_raises(self) -> None:
        from application.agent_monitoring.alert_service import approve_draft

        session = _make_session(scalar_one_or_none=None)

        with pytest.raises(ValueError, match="Draft not found"):
            await approve_draft("d-1", "org-1", "user-1", session)

    async def test_approve_triggers_mark_converted(self) -> None:
        """approve_draft() must call mark_converted on the linked finding."""
        from application.agent_monitoring.alert_service import approve_draft

        draft = _make_draft(status="PENDING", finding_id="f-1")
        session = _make_session(scalar_one_or_none=draft)

        with pytest.MonkeyPatch.context() as mp:
            converted_calls = []

            async def _fake_convert(finding_id, org_id, sess):
                converted_calls.append(finding_id)

            mp.setattr(
                "application.agent_monitoring.finding_service.mark_converted",
                _fake_convert,
            )

            await approve_draft("d-1", "org-1", "user-1", session)

        assert "f-1" in converted_calls

    async def test_reject_pending_draft(self) -> None:
        from application.agent_monitoring.alert_service import reject_draft

        draft = _make_draft(status="PENDING")
        session = _make_session(scalar_one_or_none=draft)

        result = await reject_draft("d-1", "org-1", "user-1", "Not relevant", session)

        assert result.draft_status == "REJECTED"
        assert result.rejection_reason == "Not relevant"

    async def test_reject_non_pending_raises(self) -> None:
        from application.agent_monitoring.alert_service import reject_draft

        draft = _make_draft(status="APPROVED")
        session = _make_session(scalar_one_or_none=draft)

        with pytest.raises(ValueError, match="Cannot reject"):
            await reject_draft("d-1", "org-1", "user-1", "Too late", session)


# ── create_recommendation_draft ────────────────────────────────────────────────

class TestCreateRecommendationDraft:
    async def test_creates_pending_draft(self) -> None:
        from application.agent_monitoring.alert_service import create_recommendation_draft

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        draft = await create_recommendation_draft(
            organization_id="org-1",
            agent_id="agent-1",
            recommendation_text="Initiate supplier audit",
            rationale="Risk score exceeds threshold",
            confidence_score=0.88,
            session=session,
        )

        session.add.assert_called_once()
        assert draft.draft_status == "PENDING"
        assert draft.approved_by is None
        assert draft.approved_at is None

    async def test_draft_never_auto_approved(self) -> None:
        """Agents must NEVER approve their own drafts."""
        from application.agent_monitoring.alert_service import create_recommendation_draft

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        draft = await create_recommendation_draft(
            organization_id="org-1",
            agent_id="agent-1",
            recommendation_text="Some action",
            rationale="Some rationale",
            confidence_score=0.99,
            session=session,
        )

        # Human approval model: status MUST be PENDING on creation
        assert draft.draft_status == "PENDING"
        assert draft.approved_at is None


# ── acknowledge_alert ──────────────────────────────────────────────────────────

class TestAcknowledgeAlert:
    async def test_acknowledge_sets_timestamp(self) -> None:
        from application.agent_monitoring.alert_service import acknowledge_alert

        alert = MagicMock()
        alert.id = "a-1"
        alert.organization_id = "org-1"
        alert.acknowledged_at = None
        alert.acknowledged_by = None

        session = _make_session(scalar_one_or_none=alert)

        result = await acknowledge_alert("a-1", "org-1", "user-1", session)

        assert result.acknowledged_at is not None
        assert result.acknowledged_by == "user-1"

    async def test_double_acknowledge_raises(self) -> None:
        from application.agent_monitoring.alert_service import acknowledge_alert

        alert = MagicMock()
        alert.id = "a-1"
        alert.organization_id = "org-1"
        alert.acknowledged_at = datetime.now(UTC)

        session = _make_session(scalar_one_or_none=alert)

        with pytest.raises(ValueError, match="already acknowledged"):
            await acknowledge_alert("a-1", "org-1", "user-1", session)

    async def test_alert_not_found_raises(self) -> None:
        from application.agent_monitoring.alert_service import acknowledge_alert

        session = _make_session(scalar_one_or_none=None)

        with pytest.raises(ValueError, match="Alert not found"):
            await acknowledge_alert("missing", "org-1", "user-1", session)
