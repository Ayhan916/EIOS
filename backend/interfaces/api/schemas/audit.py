from datetime import datetime

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: str
    action: str
    actor_id: str | None
    actor_email: str | None
    entity_type: str | None
    entity_id: str | None
    outcome: str
    detail: str | None
    event_metadata: dict
    created_at: datetime
