from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityResponse(BaseModel):
    """Base response fields for all domain entities."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    version: int
    owner: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime
