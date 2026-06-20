"""M35 Supplier Isolation tests.

Verifies that cross-supplier access is blocked at the service layer.
Tests guard_supplier_resource() from supplier_deps and service-level isolation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from domain.supplier_portal import SupplierUser


def _make_supplier_user(supplier_id: str = "sup-A") -> SupplierUser:
    return SupplierUser(
        id="u-1",
        supplier_id=supplier_id,
        email="a@acme.com",
        display_name="Alice",
        role="supplier_user",
        is_active=True,
        last_login_at=None,
        invited_at=None,
        accepted_at=None,
        notification_preferences={},
    )


class TestGuardSupplierResource:
    def test_same_supplier_passes(self) -> None:
        from interfaces.api.supplier_deps import guard_supplier_resource

        user = _make_supplier_user("sup-A")
        guard_supplier_resource("sup-A", user)  # must not raise

    def test_different_supplier_raises_403(self) -> None:
        from interfaces.api.supplier_deps import guard_supplier_resource

        user = _make_supplier_user("sup-A")
        with pytest.raises(HTTPException) as exc_info:
            guard_supplier_resource("sup-B", user)
        assert exc_info.value.status_code == 403
        assert "not permitted" in exc_info.value.detail


class TestEvidenceIsolation:
    @pytest.mark.asyncio
    async def test_get_evidence_request_wrong_supplier_returns_none(self) -> None:
        from application.supplier_portal.evidence_service import get_supplier_evidence_request

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        result = await get_supplier_evidence_request("req-1", "wrong-supplier", session)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_submission_wrong_supplier_raises(self) -> None:
        """send_message uses supplier_id in WHERE clause — wrong supplier returns None → ValueError."""
        from application.supplier_portal.messaging_service import send_message

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found or access denied"):
            await send_message(
                conversation_id="conv-1",
                sender_id="u-1",
                sender_type="supplier",
                content="Hello",
                supplier_id="wrong-supplier",
                session=session,
            )


class TestRemediationIsolation:
    @pytest.mark.asyncio
    async def test_update_progress_wrong_supplier_raises(self) -> None:
        from application.supplier_portal.remediation_service import update_progress

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await update_progress(
                plan_id="plan-1",
                supplier_id="attacker-supplier",
                completion_percentage=50,
                session=session,
            )


class TestQuestionnaireIsolation:
    @pytest.mark.asyncio
    async def test_save_answer_wrong_supplier_raises(self) -> None:
        from application.supplier_portal.questionnaire_service import save_answer

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="does not belong"):
            await save_answer(
                assignment_id="assign-1",
                question_id="q-1",
                supplier_user_id="u-evil",
                supplier_id="evil-supplier",
                session=session,
            )


class TestConversationIsolation:
    @pytest.mark.asyncio
    async def test_get_messages_wrong_supplier_raises(self) -> None:
        from application.supplier_portal.messaging_service import get_conversation_messages

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found or access denied"):
            await get_conversation_messages("conv-1", "evil-supplier", session=session)
