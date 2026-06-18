from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    body: str
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
