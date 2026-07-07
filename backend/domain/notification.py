from dataclasses import dataclass
from datetime import datetime

from .base_entity import BaseEntity
from .enums import EntityStatus


@dataclass(slots=True)
class Notification(BaseEntity):
    user_id: str = ""
    organization_id: str = ""
    notification_type: str = ""
    title: str = ""
    body: str = ""
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool = False
    read_at: datetime | None = None
    dedupe_key: str | None = None

    def __post_init__(self) -> None:
        if not self.status or self.status == EntityStatus.DRAFT:
            self.status = EntityStatus.ACTIVE
