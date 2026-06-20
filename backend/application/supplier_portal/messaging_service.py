"""M35 Supplier Messaging Service.

Manages threaded conversations between internal and supplier users.

All conversations are scoped by (supplier_id, organization_id).
No supplier user can access another supplier's conversations.
All messages are retained in full.

create_conversation()      — start a new thread
send_message()             — post a message to a conversation
list_conversations()       — list for a supplier or org
get_conversation_messages()— paginated message list
add_participant()          — add user to conversation
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


async def create_conversation(
    title: str,
    supplier_id: str,
    organization_id: str,
    created_by_id: str,
    created_by_type: str = "internal",
    session=None,
) -> object:
    from infrastructure.persistence.models.supplier_portal import (
        ConversationModel,
        ConversationParticipantModel,
    )

    now = datetime.now(UTC)
    conv = ConversationModel(
        id=str(uuid.uuid4()),
        title=title,
        supplier_id=supplier_id,
        organization_id=organization_id,
        created_by_id=created_by_id,
        created_by_type=created_by_type,
        created_at=now,
        updated_at=now,
    )
    session.add(conv)
    await session.flush()

    # Add creator as first participant
    participant = ConversationParticipantModel(
        id=str(uuid.uuid4()),
        conversation_id=conv.id,
        participant_id=created_by_id,
        participant_type=created_by_type,
        joined_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(participant)
    await session.flush()
    return conv


async def get_conversation(
    conversation_id: str,
    supplier_id: str,
    session=None,
) -> object | None:
    """Load a conversation scoped to a supplier (isolation guard)."""
    from infrastructure.persistence.models.supplier_portal import ConversationModel
    from sqlalchemy import select

    stmt = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.supplier_id == supplier_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def send_message(
    conversation_id: str,
    sender_id: str,
    sender_type: str,
    content: str,
    supplier_id: str,
    session=None,
) -> object:
    """Post a message. Validates that the conversation belongs to supplier_id. F5: logs activity."""
    from infrastructure.persistence.models.supplier_portal import (
        ConversationModel,
        MessageModel,
        SupplierActivityEventModel,
    )
    from sqlalchemy import select
    import json

    # Isolation: verify conversation belongs to this supplier
    conv_stmt = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.supplier_id == supplier_id,
    )
    conv = (await session.execute(conv_stmt)).scalar_one_or_none()
    if conv is None:
        raise ValueError("Conversation not found or access denied")

    now = datetime.now(UTC)
    message = MessageModel(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_type=sender_type,
        content=content,
        created_at=now,
        updated_at=now,
    )
    session.add(message)
    conv.updated_at = now
    await session.flush()

    # F5: activity audit (supplier-side sender only — internal senders don't have supplier_user_id)
    supplier_user_id = sender_id if sender_type == "supplier" else None
    activity = SupplierActivityEventModel(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        supplier_user_id=supplier_user_id,
        event_type="message_sent",
        entity_type="message",
        entity_id=message.id,
        metadata_json=json.dumps({"conversation_id": conversation_id, "sender_type": sender_type}),
        created_at=now,
        updated_at=now,
    )
    session.add(activity)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("messaging_activity_log_failed", error=str(exc))

    return message


async def list_conversations(
    supplier_id: str,
    organization_id: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from infrastructure.persistence.models.supplier_portal import ConversationModel
    from sqlalchemy import select

    stmt = select(ConversationModel).where(
        ConversationModel.supplier_id == supplier_id
    )
    if organization_id:
        stmt = stmt.where(ConversationModel.organization_id == organization_id)
    stmt = stmt.order_by(ConversationModel.updated_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_conversation_messages(
    conversation_id: str,
    supplier_id: str,
    limit: int = 100,
    offset: int = 0,
    session=None,
) -> list:
    """Paginated message list.  Verifies conversation belongs to supplier_id."""
    from infrastructure.persistence.models.supplier_portal import (
        ConversationModel,
        MessageModel,
    )
    from sqlalchemy import select

    conv_stmt = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.supplier_id == supplier_id,
    )
    conv = (await session.execute(conv_stmt)).scalar_one_or_none()
    if conv is None:
        raise ValueError("Conversation not found or access denied")

    stmt = (
        select(MessageModel)
        .where(MessageModel.conversation_id == conversation_id)
        .order_by(MessageModel.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def add_participant(
    conversation_id: str,
    participant_id: str,
    participant_type: str,
    supplier_id: str,
    session=None,
) -> object:
    from infrastructure.persistence.models.supplier_portal import (
        ConversationModel,
        ConversationParticipantModel,
    )
    from sqlalchemy import select

    conv_stmt = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.supplier_id == supplier_id,
    )
    conv = (await session.execute(conv_stmt)).scalar_one_or_none()
    if conv is None:
        raise ValueError("Conversation not found or access denied")

    now = datetime.now(UTC)
    participant = ConversationParticipantModel(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        participant_id=participant_id,
        participant_type=participant_type,
        joined_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(participant)
    try:
        await session.flush()
    except Exception:
        pass  # UniqueConstraint violation if already a participant
    return participant
