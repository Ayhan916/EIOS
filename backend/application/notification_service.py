"""
EIOS Notification Service

Creates in-app notifications and optionally sends emails based on user preferences.
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from domain.notification import Notification
from domain.enums import NotificationType
from infrastructure.persistence.repositories.notification import SQLNotificationRepository
from infrastructure.persistence.repositories.user import SQLUserRepository
from shared.email import send_email

logger = structlog.get_logger(__name__)

_PREF_KEY: dict[str, str] = {
    NotificationType.WORKFLOW_COMPLETED: "email_workflow_completed",
    NotificationType.ACTION_OVERDUE: "email_action_overdue",
    NotificationType.ASSESSMENT_APPROVED: "email_assessment_approved",
    NotificationType.RECOMMENDATION_ASSIGNED: "email_recommendation_assigned",
}


async def notify(
    *,
    session: AsyncSession,
    user_id: str,
    organization_id: str,
    notification_type: str,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    dedupe_key: str | None = None,
    user_email: str | None = None,
    notification_preferences: dict | None = None,
) -> Notification | None:
    """
    Persist an in-app notification and optionally send an email.

    Returns the created Notification, or None if deduplication skipped it.
    """
    notif_repo = SQLNotificationRepository(session)

    if dedupe_key and await notif_repo.exists_by_dedupe_key(dedupe_key):
        return None

    notification = Notification(
        user_id=user_id,
        organization_id=organization_id,
        notification_type=notification_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=dedupe_key,
    )
    saved = await notif_repo.save(notification)

    # Send email if the user has that preference enabled.
    # If notification_preferences is passed by the caller (e.g. overdue batch job that
    # already fetched the user), skip the extra DB lookup.
    pref_key = _PREF_KEY.get(notification_type)
    if pref_key and user_email:
        if notification_preferences is not None:
            wants_email = bool(notification_preferences.get(pref_key, True))
        else:
            wants_email = True
            user_repo = SQLUserRepository(session)
            user = await user_repo.get_by_id(user_id)
            if user is not None:
                wants_email = bool(user.notification_preferences.get(pref_key, True))

        if wants_email:
            await send_email(
                to=user_email,
                subject=title,
                body_html=f"<p>{body}</p>",
                body_text=body,
            )

    logger.info(
        "notification_created",
        notification_id=saved.id,
        user_id=user_id,
        notification_type=notification_type,
    )
    return saved
