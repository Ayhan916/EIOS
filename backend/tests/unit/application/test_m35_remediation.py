"""M35 Remediation Service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_plan(status: str = "open", pct: int = 0) -> MagicMock:
    p = MagicMock()
    p.id = "plan-1"
    p.supplier_id = "sup-1"
    p.finding_id = "find-1"
    p.organization_id = "org-1"
    p.title = "Fix emissions"
    p.description = ""
    p.remediation_status = status
    p.completion_percentage = pct
    p.verified_by = None
    p.verified_at = None
    p.created_by = "user-1"
    p.owner_supplier_user_id = None
    p.due_date = None
    p.created_at = datetime.now(UTC)
    p.updated_at = datetime.now(UTC)
    return p


class TestCreateRemediationPlan:
    @pytest.mark.asyncio
    async def test_creates_plan(self) -> None:
        from application.supplier_portal.remediation_service import create_remediation_plan

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        plan = await create_remediation_plan(
            supplier_id="sup-1",
            finding_id="find-1",
            title="Reduce scope 1",
            description="Switch to renewable energy.",
            organization_id="org-1",
            created_by="user-1",
            session=session,
        )
        session.add.assert_called_once()
        assert plan.remediation_status == "open"
        assert plan.completion_percentage == 0


class TestUpdateProgress:
    @pytest.mark.asyncio
    async def test_invalid_percentage_raises(self) -> None:
        from application.supplier_portal.remediation_service import update_progress

        session = AsyncMock()
        with pytest.raises(ValueError, match="between 0 and 100"):
            await update_progress("plan-1", "sup-1", 150, session=session)

    @pytest.mark.asyncio
    async def test_100_percent_auto_completes(self) -> None:
        from application.supplier_portal.remediation_service import update_progress

        plan = _make_plan("in_progress", 50)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=plan)
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await update_progress("plan-1", "sup-1", 100, session=session)
        assert result.remediation_status == "completed"
        assert result.completion_percentage == 100

    @pytest.mark.asyncio
    async def test_open_becomes_in_progress(self) -> None:
        from application.supplier_portal.remediation_service import update_progress

        plan = _make_plan("open", 0)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=plan)
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await update_progress("plan-1", "sup-1", 30, session=session)
        assert result.remediation_status == "in_progress"

    @pytest.mark.asyncio
    async def test_verified_plan_cannot_be_updated(self) -> None:
        from application.supplier_portal.remediation_service import update_progress

        plan = _make_plan("verified", 100)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=plan)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot update a verified"):
            await update_progress("plan-1", "sup-1", 90, session=session)


class TestVerifyPlan:
    @pytest.mark.asyncio
    async def test_verify_completed_plan(self) -> None:
        from application.supplier_portal.remediation_service import verify_plan

        plan = _make_plan("completed", 100)
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=plan)
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await verify_plan("plan-1", "org-1", "verifier-1", session=session)
        assert result.remediation_status == "verified"
        assert result.verified_by == "verifier-1"

    @pytest.mark.asyncio
    async def test_verify_non_completed_raises(self) -> None:
        from application.supplier_portal.remediation_service import verify_plan

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await verify_plan("plan-1", "org-1", "verifier-1", session=session)
