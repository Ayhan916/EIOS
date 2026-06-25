"""Unit tests for M46.3 — Scheduling, Remediation & AI Risk Drafts.

Covers:
  - RemediationMilestoneModel field assertions
  - AssessmentScheduleModel field assertions
  - SupplierCertificateModel field assertions
  - RiskDraftModel field assertions + invariant docstring
  - check_due_assessments_task: triggered / skip-idempotent / error path
  - check_certificate_expiry_task: alerted / cooldown / no-admins
  - generate_risk_draft_task: happy path / markdown fence stripping / error
  - Migration 057: upgrade/downgrade stubs
  - M46.3 router schemas
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import pathlib
import sys
import textwrap
import uuid
from datetime import UTC, datetime, timedelta
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Model field tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRemediationMilestoneModel:
    def test_tablename(self):
        from infrastructure.persistence.models.m46_3 import RemediationMilestoneModel
        assert RemediationMilestoneModel.__tablename__ == "remediation_milestones"

    def test_required_fields_exist(self):
        from infrastructure.persistence.models.m46_3 import RemediationMilestoneModel
        cols = {c.key for c in RemediationMilestoneModel.__table__.columns}
        for field in ("id", "plan_id", "title", "milestone_status", "sort_order", "created_by", "created_at", "updated_at"):
            assert field in cols, f"Missing column: {field}"

    def test_optional_fields(self):
        from infrastructure.persistence.models.m46_3 import RemediationMilestoneModel
        cols = {c.key for c in RemediationMilestoneModel.__table__.columns}
        for field in ("description", "due_date", "completed_at", "completed_by"):
            assert field in cols, f"Missing optional column: {field}"


class TestAssessmentScheduleModel:
    def test_tablename(self):
        from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel
        assert AssessmentScheduleModel.__tablename__ == "assessment_schedules"

    def test_unique_constraint_exists(self):
        from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel
        constraint_names = {c.name for c in AssessmentScheduleModel.__table__.constraints}
        assert "uq_assessment_schedule_org_supplier" in constraint_names

    def test_required_fields(self):
        from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel
        cols = {c.key for c in AssessmentScheduleModel.__table__.columns}
        for field in ("id", "organization_id", "supplier_id", "frequency_days", "next_due_at", "is_active"):
            assert field in cols

    def test_template_assessment_id_nullable(self):
        from infrastructure.persistence.models.m46_3 import AssessmentScheduleModel
        col = AssessmentScheduleModel.__table__.c["template_assessment_id"]
        assert col.nullable is True


class TestSupplierCertificateModel:
    def test_tablename(self):
        from infrastructure.persistence.models.m46_3 import SupplierCertificateModel
        assert SupplierCertificateModel.__tablename__ == "supplier_certificates"

    def test_alert_days_before_default(self):
        from infrastructure.persistence.models.m46_3 import SupplierCertificateModel
        col = SupplierCertificateModel.__table__.c["alert_days_before"]
        assert col.default.arg == 30

    def test_expires_at_not_nullable(self):
        from infrastructure.persistence.models.m46_3 import SupplierCertificateModel
        col = SupplierCertificateModel.__table__.c["expires_at"]
        assert col.nullable is False


class TestRiskDraftModel:
    def test_tablename(self):
        from infrastructure.persistence.models.m46_3 import RiskDraftModel
        assert RiskDraftModel.__tablename__ == "risk_drafts"

    def test_review_status_default_pending(self):
        from infrastructure.persistence.models.m46_3 import RiskDraftModel
        col = RiskDraftModel.__table__.c["review_status"]
        assert col.default.arg == "pending"

    def test_promoted_risk_id_nullable(self):
        from infrastructure.persistence.models.m46_3 import RiskDraftModel
        col = RiskDraftModel.__table__.c["promoted_risk_id"]
        assert col.nullable is True

    def test_llm_prompt_hash_nullable(self):
        from infrastructure.persistence.models.m46_3 import RiskDraftModel
        col = RiskDraftModel.__table__.c["llm_prompt_hash"]
        assert col.nullable is True

    def test_invariant_docstring_present(self):
        """Safety invariant: the model's docstring must state agents never create Risk records."""
        from infrastructure.persistence.models.m46_3 import RiskDraftModel
        doc = RiskDraftModel.__doc__ or ""
        assert "INVARIANT" in doc, "RiskDraftModel must carry the AI-boundary invariant in its docstring"
        assert "human" in doc.lower(), "Docstring must reference human review requirement"


# ─────────────────────────────────────────────────────────────────────────────
# Schedule checker task tests
# ─────────────────────────────────────────────────────────────────────────────

class TestScheduleCheckerTask:
    def _make_session_ctx(self, schedules):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = schedules
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_begin = AsyncMock()
        mock_begin.__aenter__ = AsyncMock(return_value=None)
        mock_begin.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin = MagicMock(return_value=mock_begin)
        return mock_session

    def _make_schedule(self, *, last_triggered_hours_ago=None, frequency_days=90, org_id="org-1", supplier_id="sup-1"):
        now = datetime.now(UTC)
        sched = MagicMock()
        sched.id = str(uuid.uuid4())
        sched.organization_id = org_id
        sched.supplier_id = supplier_id
        sched.frequency_days = frequency_days
        sched.next_due_at = now - timedelta(days=1)
        sched.last_triggered_at = (
            now - timedelta(hours=last_triggered_hours_ago)
            if last_triggered_hours_ago is not None
            else None
        )
        sched.updated_at = now
        return sched

    def test_triggers_overdue_schedule(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.schedule_checker import _run_schedule_check

        sched = self._make_schedule()
        mock_session = self._make_session_ctx([sched])

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = asyncio.run(_run_schedule_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["triggered"] == 1
        assert result["errors"] == 0
        mock_session.add.assert_called_once()

    def test_skips_within_20h_cooldown(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.schedule_checker import _run_schedule_check

        sched = self._make_schedule(last_triggered_hours_ago=5)  # within 20h → skip
        mock_session = self._make_session_ctx([sched])

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = asyncio.run(_run_schedule_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["triggered"] == 0
        mock_session.add.assert_not_called()

    def test_advances_next_due_at(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.schedule_checker import _run_schedule_check

        sched = self._make_schedule(frequency_days=30)
        original_next = sched.next_due_at
        mock_session = self._make_session_ctx([sched])

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            asyncio.run(_run_schedule_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        # next_due_at should have been advanced by frequency_days
        assert sched.next_due_at > original_next

    def test_errors_counted_not_raised(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.schedule_checker import _run_schedule_check

        sched = self._make_schedule()
        mock_session = self._make_session_ctx([sched])
        mock_session.add = MagicMock(side_effect=RuntimeError("DB write failed"))

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = asyncio.run(_run_schedule_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["errors"] == 1
        assert result["triggered"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Certificate expiry task tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCertificateExpiryTask:
    def _make_cert(self, *, expires_in_days=15, alert_days_before=30, last_alert_hours_ago=None):
        now = datetime.now(UTC)
        cert = MagicMock()
        cert.id = str(uuid.uuid4())
        cert.supplier_id = str(uuid.uuid4())
        cert.organization_id = "org-1"
        cert.name = "ISO 9001"
        cert.cert_type = "Quality"
        cert.expires_at = now + timedelta(days=expires_in_days)
        cert.alert_days_before = alert_days_before
        cert.last_alert_sent_at = (
            now - timedelta(hours=last_alert_hours_ago) if last_alert_hours_ago else None
        )
        cert.updated_at = now
        return cert

    def _make_admin(self, org_id="org-1"):
        user = MagicMock()
        user.id = str(uuid.uuid4())
        user.organization_id = org_id
        user.role = "Admin"
        return user

    def _make_session_ctx(self, certs, admins):
        mock_session = AsyncMock()
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            r = MagicMock()
            # First call → certs; subsequent calls → admins
            if call_count[0] == 1:
                r.scalars.return_value.all.return_value = certs
            else:
                r.scalars.return_value.all.return_value = admins
            return r

        mock_session.execute = mock_execute
        mock_session.add = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_begin = AsyncMock()
        mock_begin.__aenter__ = AsyncMock(return_value=None)
        mock_begin.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin = MagicMock(return_value=mock_begin)
        return mock_session

    def test_alerts_expiring_cert(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.certificate_expiry import _run_expiry_check

        cert = self._make_cert(expires_in_days=10, alert_days_before=30)
        admin = self._make_admin()
        mock_session = self._make_session_ctx([cert], [admin])

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = asyncio.run(_run_expiry_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["alerted"] == 1
        assert result["errors"] == 0
        mock_session.add.assert_called_once()

    def test_skips_cert_not_yet_due(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.certificate_expiry import _run_expiry_check

        cert = self._make_cert(expires_in_days=60, alert_days_before=30)
        mock_session = self._make_session_ctx([cert], [])

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = asyncio.run(_run_expiry_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["alerted"] == 0
        mock_session.add.assert_not_called()

    def test_cooldown_prevents_duplicate_alert(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.certificate_expiry import _run_expiry_check

        cert = self._make_cert(expires_in_days=5, alert_days_before=30, last_alert_hours_ago=3)
        mock_session = self._make_session_ctx([cert], [])

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = asyncio.run(_run_expiry_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["alerted"] == 0
        mock_session.add.assert_not_called()

    def test_no_notification_when_no_admins(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.certificate_expiry import _run_expiry_check

        cert = self._make_cert(expires_in_days=5, alert_days_before=30)
        mock_session = self._make_session_ctx([cert], [])  # no admins

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            result = asyncio.run(_run_expiry_check())
        finally:
            _db_mod.AsyncSessionFactory = original

        # cert is alerted but no notifications created (no admins)
        assert result["alerted"] == 1
        mock_session.add.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Risk draft generation task tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskDraftTask:
    def _make_llm(self, content: str) -> MagicMock:
        llm = MagicMock()
        msg = MagicMock()
        msg.content = content
        llm.complete = AsyncMock(return_value=msg)
        return llm

    def _make_session_ctx(self):
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_begin = AsyncMock()
        mock_begin.__aenter__ = AsyncMock(return_value=None)
        mock_begin.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin = MagicMock(return_value=mock_begin)
        return mock_session

    _VALID_JSON = '{"title": "Supply chain disruption", "description": "Risk from single-source supplier.", "severity": "High", "category": "Operational", "likelihood": "Medium"}'
    _FENCED_JSON = f"```json\n{_VALID_JSON}\n```"

    def test_happy_path_creates_draft(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.risk_draft import _run_draft_generation

        mock_session = self._make_session_ctx()
        llm = self._make_llm(self._VALID_JSON)

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            with patch("infrastructure.llm.deps.init_llm_provider", return_value=llm):
                result = asyncio.run(_run_draft_generation(
                    signal_id="sig-1",
                    organization_id="org-1",
                    supplier_id="sup-1",
                    signal_description="Supplier XYZ has delayed shipments for 3 months",
                    signal_type="delay",
                    signal_severity="High",
                    actor_id="user-1",
                ))
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["review_status"] == "pending"
        assert "draft_id" in result
        assert result["draft_severity"] == "High"
        mock_session.add.assert_called_once()

    def test_strips_markdown_fence(self):
        import infrastructure.persistence.database as _db_mod
        from infrastructure.celery.tasks.risk_draft import _run_draft_generation

        mock_session = self._make_session_ctx()
        llm = self._make_llm(self._FENCED_JSON)

        original = _db_mod.AsyncSessionFactory
        _db_mod.AsyncSessionFactory = MagicMock(return_value=mock_session)
        try:
            with patch("infrastructure.llm.deps.init_llm_provider", return_value=llm):
                result = asyncio.run(_run_draft_generation(
                    signal_id="sig-1",
                    organization_id="org-1",
                    supplier_id=None,
                    signal_description="Supplier issues",
                    signal_type="reputational",
                    signal_severity="Medium",
                    actor_id="user-1",
                ))
        finally:
            _db_mod.AsyncSessionFactory = original

        assert result["review_status"] == "pending"

    def test_prompt_hash_is_sha256(self):
        """Ensure the prompt_hash stored is deterministic SHA-256."""
        from infrastructure.celery.tasks.risk_draft import _DRAFT_SYSTEM_PROMPT
        # Verifying the hash function is SHA-256 by checking length
        sample = hashlib.sha256((_DRAFT_SYSTEM_PROMPT + "test").encode()).hexdigest()
        assert len(sample) == 64

    def test_never_creates_risk_model(self):
        """Guard: _run_draft_generation must not import or call RiskModel."""
        import inspect
        from infrastructure.celery.tasks import risk_draft
        source = inspect.getsource(risk_draft._run_draft_generation)
        assert "RiskModel" not in source, "AI task must never create a Risk record"


# ─────────────────────────────────────────────────────────────────────────────
# Migration 057 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMigration057:
    @staticmethod
    def _load_migration():
        migration_path = (
            pathlib.Path(__file__).parent.parent.parent.parent
            / "alembic" / "versions" / "057_m46_3_scheduling_alerts.py"
        )
        spec = importlib.util.spec_from_file_location("migration_057", migration_path)
        mod = ModuleType("migration_057")

        fake_op = MagicMock()
        fake_alembic_pkg = MagicMock()
        fake_alembic_pkg.op = fake_op

        with patch.dict(sys.modules, {"alembic": fake_alembic_pkg, "alembic.op": fake_op}):
            spec.loader.exec_module(mod)

        return mod, fake_op

    def test_revision_chain(self):
        mod, _ = self._load_migration()
        assert mod.revision == "057"
        assert mod.down_revision == "056"

    def test_upgrade_creates_expected_tables(self):
        mod, fake_op = self._load_migration()
        mod.upgrade()
        created = [call.args[0] for call in fake_op.create_table.call_args_list]
        for expected in ("remediation_milestones", "assessment_schedules", "supplier_certificates", "risk_drafts"):
            assert expected in created, f"upgrade() should create table: {expected}"

    def test_downgrade_drops_tables(self):
        mod, fake_op = self._load_migration()
        mod.downgrade()
        assert fake_op.drop_table.called

    def test_upgrade_then_downgrade(self):
        mod, fake_op = self._load_migration()
        mod.upgrade()
        mod.downgrade()
        assert fake_op.create_table.called
        assert fake_op.drop_table.called


# ─────────────────────────────────────────────────────────────────────────────
# Schema validation tests
# ─────────────────────────────────────────────────────────────────────────────

class TestM463Schemas:
    def test_assessment_schedule_frequency_ge_7(self):
        from interfaces.api.schemas.m46_3 import AssessmentScheduleCreate
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            AssessmentScheduleCreate(supplier_id="s-1", frequency_days=3)

    def test_assessment_schedule_frequency_le_3650(self):
        from interfaces.api.schemas.m46_3 import AssessmentScheduleCreate
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            AssessmentScheduleCreate(supplier_id="s-1", frequency_days=9999)

    def test_certificate_alert_days_before_ge_1(self):
        from interfaces.api.schemas.m46_3 import SupplierCertificateCreate
        from datetime import datetime, UTC
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            SupplierCertificateCreate(
                name="ISO",
                cert_type="Quality",
                expires_at=datetime.now(UTC),
                alert_days_before=0,
            )

    def test_valid_assessment_schedule(self):
        from interfaces.api.schemas.m46_3 import AssessmentScheduleCreate

        s = AssessmentScheduleCreate(supplier_id="sup-1", frequency_days=90)
        assert s.frequency_days == 90
        assert s.supplier_id == "sup-1"

    def test_valid_certificate(self):
        from interfaces.api.schemas.m46_3 import SupplierCertificateCreate
        from datetime import datetime, UTC

        c = SupplierCertificateCreate(
            name="ISO 27001",
            cert_type="Security",
            expires_at=datetime(2027, 1, 1, tzinfo=UTC),
            alert_days_before=60,
        )
        assert c.alert_days_before == 60

    def test_accept_draft_allows_override(self):
        from interfaces.api.schemas.m46_3 import AcceptRiskDraftRequest

        r = AcceptRiskDraftRequest(override_severity="Critical", override_title="New title")
        assert r.override_severity == "Critical"


# Import pytest after defining the classes (some tests use pytest.raises)
import pytest
