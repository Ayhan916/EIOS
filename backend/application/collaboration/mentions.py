"""
M26 Mention Extraction

Parses @display_name tokens from comment content and resolves them to user IDs.
Generates COMMENT_MENTION notifications for each resolved user.
Only users within the same organisation are resolved (tenant isolation).
"""

from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import NotificationType
from infrastructure.persistence.repositories.user import SQLUserRepository

# Matches @Word, @First.Last, @display-name (dots/hyphens only between word chars)
_MENTION_RE = re.compile(r"@(\w+(?:[.\-]\w+)*)", re.UNICODE)


def extract_mention_handles(content: str) -> list[str]:
    """Return a de-duplicated list of @handle tokens found in content."""
    return list(dict.fromkeys(m.group(1) for m in _MENTION_RE.finditer(content)))


async def resolve_mentions(
    content: str,
    organization_id: str,
    session: AsyncSession,
) -> list[str]:
    """Return user IDs for @handles that resolve to active org members."""
    handles = extract_mention_handles(content)
    if not handles:
        return []
    user_repo = SQLUserRepository(session)
    all_users = await user_repo.list_by_organization(organization_id)
    handle_set = {h.lower() for h in handles}
    return [
        u.id
        for u in all_users
        if u.is_active and _matches_handle(u.display_name, u.email, handle_set)
    ]


def _matches_handle(display_name: str, email: str, handle_set: set[str]) -> bool:
    normalised = display_name.replace(" ", ".").lower()
    email_local = email.split("@")[0].lower()
    return normalised in handle_set or email_local in handle_set


async def notify_mentions(
    *,
    session: AsyncSession,
    mentioned_user_ids: list[str],
    author_name: str,
    entity_type: str,
    entity_id: str,
    assessment_id: str,
    organization_id: str,
) -> None:
    """Fire COMMENT_MENTION notifications for all resolved mentions."""
    if not mentioned_user_ids:
        return

    from application import notification_service
    from infrastructure.persistence.repositories.user import SQLUserRepository

    user_repo = SQLUserRepository(session)

    for uid in mentioned_user_ids:
        user = await user_repo.get_by_id(uid)
        if user is None:
            continue
        await notification_service.notify(
            session=session,
            user_id=uid,
            organization_id=organization_id,
            notification_type=NotificationType.COMMENT_MENTION,
            title=f"{author_name} mentioned you",
            body=f"You were mentioned in a comment on {entity_type} {entity_id}.",
            entity_type=entity_type,
            entity_id=entity_id,
            dedupe_key=f"mention:{entity_id}:{uid}:{assessment_id}",
            user_email=user.email,
        )
