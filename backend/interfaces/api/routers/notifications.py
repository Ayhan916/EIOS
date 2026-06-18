from fastapi import APIRouter, Depends, HTTPException, status

from domain.user import User
from infrastructure.persistence.repositories.notification import SQLNotificationRepository
from interfaces.api.deps import get_current_user, get_notification_repo
from interfaces.api.schemas.notification import NotificationListResponse, NotificationResponse

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    current_user: User = Depends(get_current_user),
    repo: SQLNotificationRepository = Depends(get_notification_repo),
) -> NotificationListResponse:
    items = await repo.list_for_user(current_user.id)
    unread = await repo.unread_count(current_user.id)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        unread_count=unread,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLNotificationRepository = Depends(get_notification_repo),
) -> NotificationResponse:
    notification = await repo.get_by_id(notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await repo.mark_read(notification_id, current_user.id)
    notification.is_read = True
    return NotificationResponse.model_validate(notification)


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    repo: SQLNotificationRepository = Depends(get_notification_repo),
) -> None:
    await repo.mark_all_read(current_user.id)
