"""M35.1 Hardening tests — covers all 10 security fixes (F1-F10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── F1: send_internal_message scoped by organization_id ──────────────────────


class TestF1InternalMessageIsolation:
    def test_send_internal_message_filters_by_organization_id(self) -> None:
        """Source must include organization_id in the conversation WHERE clause."""
        import importlib
        import importlib.util

        importlib.util.spec_from_file_location(
            "_spi_internal",
            "interfaces/api/routers/supplier_portal_internal.py",
        )
        src = open("interfaces/api/routers/supplier_portal_internal.py").read()
        assert "organization_id" in src
        # Specifically the send_internal_message function must include it
        # Find the function source by slicing from the def to next @router
        start = src.find("async def send_internal_message(")
        end = src.find("\n@router.", start)
        if end == -1:
            end = len(src)
        fn_src = src[start:end]
        assert "organization_id" in fn_src, (
            "F1 BLOCKER: send_internal_message must filter conversation by organization_id"
        )


# ── F2: DB-backed single-use password reset tokens ───────────────────────────


class TestF2PasswordResetTokens:
    @pytest.mark.asyncio
    async def test_generate_token_stores_hash(self) -> None:
        from application.supplier_portal.supplier_auth_service import (
            generate_password_reset_token,
        )

        user = MagicMock()
        user.supplier_id = "sup-1"

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        user_result = MagicMock()
        user_result.scalar_one_or_none = MagicMock(return_value=user)
        session.execute = AsyncMock(return_value=user_result)

        raw_token = await generate_password_reset_token(email="a@b.com", session=session)
        assert raw_token is not None
        assert len(raw_token) > 20
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_token_returns_none_if_user_not_found(self) -> None:
        from application.supplier_portal.supplier_auth_service import (
            generate_password_reset_token,
        )

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=result)
        session.add = MagicMock()

        raw_token = await generate_password_reset_token(email="nobody@b.com", session=session)
        assert raw_token is None
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_password_rejects_used_token(self) -> None:
        from application.supplier_portal.supplier_auth_service import reset_password

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="Invalid, expired, or already-used"):
            await reset_password(token="bad-token", new_password="NewPass1!", session=session)

    @pytest.mark.asyncio
    async def test_reset_password_marks_used_at(self) -> None:
        from application.supplier_portal.supplier_auth_service import reset_password

        reset_record = MagicMock()
        reset_record.email = "a@b.com"
        reset_record.supplier_id = "sup-1"
        reset_record.used_at = None

        user = MagicMock()
        user.supplier_id = "sup-1"
        user.failed_login_attempts = 3
        user.locked_until = None

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none = MagicMock(return_value=reset_record)
            else:
                result.scalar_one_or_none = MagicMock(return_value=user)
            return result

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=side_effect)
        session.add = MagicMock()
        session.flush = AsyncMock()

        with patch("shared.security.hash_password", return_value="hashed"):
            await reset_password(token="raw-token", new_password="NewPass1!", session=session)

        assert reset_record.used_at is not None
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


# ── F3: SELECT FOR UPDATE on concurrent state transitions ────────────────────


class TestF3SelectForUpdate:
    def test_review_submission_uses_with_for_update(self) -> None:
        src = open("application/supplier_portal/evidence_service.py").read()
        start = src.find("async def review_submission(")
        end = src.find("\nasync def ", start + 1)
        fn_src = src[start:end] if end != -1 else src[start:]
        assert "with_for_update" in fn_src

    def test_review_assignment_uses_with_for_update(self) -> None:
        src = open("application/supplier_portal/questionnaire_service.py").read()
        start = src.find("async def review_assignment(")
        end = src.find("\nasync def ", start + 1)
        fn_src = src[start:end] if end != -1 else src[start:]
        assert "with_for_update" in fn_src

    def test_verify_plan_uses_with_for_update(self) -> None:
        src = open("application/supplier_portal/remediation_service.py").read()
        start = src.find("async def verify_plan(")
        end = src.find("\nasync def ", start + 1)
        fn_src = src[start:end] if end != -1 else src[start:]
        assert "with_for_update" in fn_src


# ── F4: Status rollback prevention ───────────────────────────────────────────


class TestF4StatusRollback:
    @pytest.mark.asyncio
    async def test_cannot_rollback_completed_to_open(self) -> None:
        from application.supplier_portal.remediation_service import update_progress

        plan = MagicMock()
        plan.remediation_status = "completed"
        plan.owner_supplier_user_id = None

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=plan)
        session.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="Cannot roll back a completed"):
            await update_progress(
                plan_id="plan-1",
                supplier_id="sup-1",
                completion_percentage=50,
                new_status="open",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_cannot_rollback_completed_to_in_progress(self) -> None:
        from application.supplier_portal.remediation_service import update_progress

        plan = MagicMock()
        plan.remediation_status = "completed"
        plan.owner_supplier_user_id = None

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=plan)
        session.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="Cannot roll back a completed"):
            await update_progress(
                plan_id="plan-1",
                supplier_id="sup-1",
                completion_percentage=80,
                new_status="in_progress",
                session=session,
            )


# ── F5: Activity logging on every state transition ───────────────────────────


class TestF5ActivityLogging:
    @pytest.mark.asyncio
    async def test_submit_evidence_logs_event(self) -> None:
        from application.supplier_portal.evidence_service import submit_evidence

        sub = MagicMock()
        sub.submission_status = "draft"
        sub.supplier_id = "sup-1"
        sub.supplier_user_id = "usr-1"
        sub.evidence_request_id = "req-1"

        call_count = 0
        execute_results = []

        for _ in range(3):
            r = MagicMock()
            r.scalar_one_or_none = MagicMock(return_value=sub)
            execute_results.append(r)
        # Flush result for the UPDATE
        update_r = MagicMock()
        update_r.scalar_one_or_none = MagicMock(return_value=None)
        execute_results.append(update_r)

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            r = execute_results[call_count] if call_count < len(execute_results) else MagicMock()
            call_count += 1
            return r

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=side_effect)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await submit_evidence(
            submission_id="sub-1",
            supplier_id="sup-1",
            supplier_user_id="usr-1",
            session=session,
        )
        assert session.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_submit_questionnaire_logs_event(self) -> None:
        from application.supplier_portal.questionnaire_service import submit_questionnaire

        assignment = MagicMock()
        assignment.questionnaire_status = "in_progress"
        assignment.supplier_id = "sup-1"

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=assignment)
        session.execute = AsyncMock(return_value=result)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await submit_questionnaire(
            assignment_id="assign-1",
            supplier_id="sup-1",
            supplier_user_id="usr-1",
            session=session,
        )
        # activity record was added
        assert session.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_send_message_logs_activity(self) -> None:
        from application.supplier_portal.messaging_service import send_message

        conv = MagicMock()
        conv.supplier_id = "sup-1"
        conv.updated_at = None

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=result)
        session.add = MagicMock()
        session.flush = AsyncMock()

        await send_message(
            conversation_id="conv-1",
            sender_id="usr-s1",
            sender_type="supplier",
            content="hello",
            supplier_id="sup-1",
            session=session,
        )
        # Both the message and the activity record should be added
        assert session.add.call_count == 2


# ── F6: Dashboard real queries ────────────────────────────────────────────────


class TestF6DashboardRealQueries:
    @pytest.mark.asyncio
    async def test_dashboard_returns_real_counts(self) -> None:
        from application.supplier_portal.dashboard_service import get_supplier_dashboard

        session = AsyncMock()
        call_count = 0

        async def count_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            r.scalar_one = MagicMock(return_value=call_count)
            # For the activity query (scalars chain)
            scalars = MagicMock()
            scalars.all = MagicMock(return_value=[])
            r.scalars = MagicMock(return_value=scalars)
            return r

        session.execute = AsyncMock(side_effect=count_side_effect)

        dashboard = await get_supplier_dashboard(supplier_id="sup-1", session=session)
        # Should have queried at least 7 times (ev, q, rem, overdue, findings, recs, activity)
        assert session.execute.call_count >= 7
        assert dashboard.open_findings > 0
        assert dashboard.open_recommendations > 0


# ── F7: Brute-force lockout ───────────────────────────────────────────────────


class TestF7BruteForceLogin:
    @pytest.mark.asyncio
    async def test_locked_account_raises_immediately(self) -> None:
        from application.supplier_portal.supplier_auth_service import login_supplier_user

        future_time = datetime.now(UTC) + timedelta(minutes=10)
        user = MagicMock()
        user.email = "a@b.com"
        user.supplier_id = "sup-1"
        user.password_hash = "hashed"
        user.failed_login_attempts = 5
        user.locked_until = future_time

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=user)
        session.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="Account temporarily locked"):
            await login_supplier_user(email="a@b.com", password="wrong", session=session)

    @pytest.mark.asyncio
    async def test_failed_login_increments_counter(self) -> None:
        from application.supplier_portal.supplier_auth_service import login_supplier_user

        user = MagicMock()
        user.email = "a@b.com"
        user.supplier_id = "sup-1"
        user.password_hash = "correct_hash"
        user.failed_login_attempts = 1
        user.locked_until = None

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=user)
        session.execute = AsyncMock(return_value=result)
        session.flush = AsyncMock()

        with patch("shared.security.verify_password", return_value=False):
            with pytest.raises(ValueError, match="Invalid email or password"):
                await login_supplier_user(email="a@b.com", password="wrong", session=session)

        assert user.failed_login_attempts == 2

    @pytest.mark.asyncio
    async def test_fifth_failure_sets_locked_until(self) -> None:
        from application.supplier_portal.supplier_auth_service import login_supplier_user

        user = MagicMock()
        user.email = "a@b.com"
        user.supplier_id = "sup-1"
        user.password_hash = "correct_hash"
        user.failed_login_attempts = 4
        user.locked_until = None

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=user)
        session.execute = AsyncMock(return_value=result)
        session.flush = AsyncMock()

        with patch("shared.security.verify_password", return_value=False):
            with pytest.raises(ValueError):
                await login_supplier_user(email="a@b.com", password="wrong", session=session)

        assert user.locked_until is not None

    @pytest.mark.asyncio
    async def test_successful_login_resets_counter(self) -> None:
        from application.supplier_portal.supplier_auth_service import login_supplier_user

        user = MagicMock()
        user.email = "a@b.com"
        user.supplier_id = "sup-1"
        user.id = "usr-1"
        user.role = "admin"
        user.password_hash = "correct_hash"
        user.failed_login_attempts = 3
        user.locked_until = None

        call_count = 0

        async def execute_side(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            r.scalar_one_or_none = MagicMock(return_value=user)
            scalars = MagicMock()
            scalars.all = MagicMock(return_value=[])
            r.scalars = MagicMock(return_value=scalars)
            return r

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=execute_side)
        session.add = MagicMock()
        session.flush = AsyncMock()

        with (
            patch("shared.security.verify_password", return_value=True),
            patch("shared.security.create_supplier_access_token", return_value="access"),
            patch("shared.security.create_supplier_refresh_token", return_value="refresh"),
        ):
            access, refresh = await login_supplier_user(
                email="a@b.com", password="correct", session=session
            )

        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert access == "access"


# ── F8: Duplicate submission prevention ──────────────────────────────────────


class TestF8DuplicateSubmission:
    @pytest.mark.asyncio
    async def test_returns_existing_draft_without_creating_new(self) -> None:
        from application.supplier_portal.evidence_service import create_submission

        existing = MagicMock()
        existing.submission_status = "draft"

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=existing)
        session.execute = AsyncMock(return_value=result)
        session.add = MagicMock()

        returned = await create_submission(
            evidence_request_id="req-1",
            supplier_user_id="usr-1",
            supplier_id="sup-1",
            session=session,
        )
        assert returned is existing
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_if_already_submitted(self) -> None:
        from application.supplier_portal.evidence_service import create_submission

        existing = MagicMock()
        existing.submission_status = "submitted"

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=existing)
        session.execute = AsyncMock(return_value=result)

        with pytest.raises(ValueError, match="already exists"):
            await create_submission(
                evidence_request_id="req-1",
                supplier_user_id="usr-1",
                supplier_id="sup-1",
                session=session,
            )


# ── F9: Question belongs to template validation ───────────────────────────────


class TestF9QuestionValidation:
    @pytest.mark.asyncio
    async def test_save_answer_rejects_question_from_different_template(self) -> None:
        from application.supplier_portal.questionnaire_service import save_answer

        assignment = MagicMock()
        assignment.questionnaire_status = "in_progress"
        assignment.template_id = "tmpl-1"
        assignment.supplier_id = "sup-1"

        call_count = 0

        async def execute_side(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            if call_count == 1:
                # assignment query
                r.scalar_one_or_none = MagicMock(return_value=assignment)
            else:
                # question query — returns None (wrong template)
                r.scalar_one_or_none = MagicMock(return_value=None)
            return r

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=execute_side)

        with pytest.raises(ValueError, match="does not belong to this questionnaire"):
            await save_answer(
                assignment_id="assign-1",
                question_id="q-from-other-template",
                supplier_user_id="usr-1",
                supplier_id="sup-1",
                session=session,
            )


# ── F10: Activity endpoint limit cap ─────────────────────────────────────────


class TestF10ActivityLimitCap:
    def test_activity_endpoint_limit_has_upper_bound(self) -> None:
        src = open("interfaces/api/routers/supplier_portal.py").read()
        start = src.find("async def get_activity(")
        end = src.find("\n@router.", start)
        if end == -1:
            end = len(src)
        fn_src = src[start:end]
        assert "le=500" in fn_src, "F10: /activity limit must have le=500 upper bound"
        assert "ge=1" in fn_src, "F10: /activity limit must have ge=1 lower bound"
