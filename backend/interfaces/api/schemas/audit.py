from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: str
    action: str
    actor_id: Optional[str]
    actor_email: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[str]
    outcome: str
    detail: Optional[str]
    event_metadata: dict
    created_at: datetime
