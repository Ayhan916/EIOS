"""M35 Activity Service tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestLogEvent:
    @pytest.mark.asyncio
    async def test_log_creates_event(self) -> None:
        from application.supplier_portal.activity_service import log_event

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        event = await log_event(
            supplier_id="sup-1",
            event_type="login",
            entity_type="supplier_user",
            entity_id="u-1",
            supplier_user_id="u-1",
            metadata={"ip": "1.2.3.4"},
            session=session,
        )
        session.add.assert_called_once()
        assert event.supplier_id == "sup-1"
        assert event.event_type == "login"

    @pytest.mark.asyncio
    async def test_log_survives_flush_error(self) -> None:
        """Activity logging must not blow up the calling transaction."""
        from application.supplier_portal.activity_service import log_event

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock(side_effect=Exception("DB error"))

        event = await log_event(
            supplier_id="sup-1",
            event_type="questionnaire_submitted",
            entity_type="questionnaire_assignment",
            entity_id="assign-1",
            session=session,
        )
        # Should return the model object without raising
        assert event is not None


class TestListActivity:
    @pytest.mark.asyncio
    async def test_returns_events_for_supplier(self) -> None:
        from application.supplier_portal.activity_service import list_activity

        ev1 = MagicMock()
        ev1.supplier_id = "sup-1"
        ev2 = MagicMock()
        ev2.supplier_id = "sup-1"

        session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[ev1, ev2])
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute = AsyncMock(return_value=mock_result)

        events = await list_activity("sup-1", session=session)
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_list_by_user(self) -> None:
        from application.supplier_portal.activity_service import list_activity_by_user

        ev = MagicMock()
        ev.supplier_user_id = "u-1"

        session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[ev])
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute = AsyncMock(return_value=mock_result)

        events = await list_activity_by_user("sup-1", "u-1", session=session)
        assert len(events) == 1
