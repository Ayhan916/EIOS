"""M35 Messaging Service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_conversation(supplier_id: str = "sup-1") -> MagicMock:
    c = MagicMock()
    c.id = "conv-1"
    c.title = "Q4 ESG Discussion"
    c.supplier_id = supplier_id
    c.organization_id = "org-1"
    c.created_by_id = "u-1"
    c.created_by_type = "internal"
    c.created_at = datetime.now(UTC)
    c.updated_at = datetime.now(UTC)
    return c


class TestCreateConversation:
    @pytest.mark.asyncio
    async def test_creates_conversation_and_participant(self) -> None:
        from application.supplier_portal.messaging_service import create_conversation

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        conv = await create_conversation(
            title="ESG Update",
            supplier_id="sup-1",
            organization_id="org-1",
            created_by_id="internal-user",
            created_by_type="internal",
            session=session,
        )
        assert session.add.call_count == 2  # conversation + participant
        assert session.flush.call_count == 2
        assert conv.title == "ESG Update"


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_sends_message(self) -> None:
        from application.supplier_portal.messaging_service import send_message

        conv = _make_conversation("sup-1")
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        mock_conv_result = MagicMock()
        mock_conv_result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=mock_conv_result)

        msg = await send_message(
            conversation_id="conv-1",
            sender_id="u-1",
            sender_type="supplier",
            content="Hello, here's our update.",
            supplier_id="sup-1",
            session=session,
        )
        assert session.add.call_count >= 1  # message + activity event
        assert msg.content == "Hello, here's our update."

    @pytest.mark.asyncio
    async def test_wrong_supplier_raises(self) -> None:
        from application.supplier_portal.messaging_service import send_message

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found or access denied"):
            await send_message(
                conversation_id="conv-1",
                sender_id="attacker",
                sender_type="supplier",
                content="Hack",
                supplier_id="evil-sup",
                session=session,
            )


class TestGetConversationMessages:
    @pytest.mark.asyncio
    async def test_returns_messages(self) -> None:
        from application.supplier_portal.messaging_service import get_conversation_messages

        conv = _make_conversation("sup-1")
        msg1 = MagicMock()
        msg1.id = "m-1"
        msg2 = MagicMock()
        msg2.id = "m-2"

        session = AsyncMock()
        call_count = [0]

        mock_conv_result = MagicMock()
        mock_conv_result.scalar_one_or_none = MagicMock(return_value=conv)
        mock_msg_result = MagicMock()
        mock_msg_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[msg1, msg2]))
        )

        async def execute_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_conv_result
            return mock_msg_result

        session.execute = AsyncMock(side_effect=execute_side_effect)

        msgs = await get_conversation_messages("conv-1", "sup-1", session=session)
        assert len(msgs) == 2

    @pytest.mark.asyncio
    async def test_wrong_supplier_raises(self) -> None:
        from application.supplier_portal.messaging_service import get_conversation_messages

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found or access denied"):
            await get_conversation_messages("conv-1", "wrong-sup", session=session)


class TestAddParticipant:
    @pytest.mark.asyncio
    async def test_adds_participant(self) -> None:
        from application.supplier_portal.messaging_service import add_participant

        conv = _make_conversation("sup-1")
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=mock_result)

        await add_participant(
            conversation_id="conv-1",
            participant_id="new-user",
            participant_type="internal",
            supplier_id="sup-1",
            session=session,
        )
        session.add.assert_called_once()
