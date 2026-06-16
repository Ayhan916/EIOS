from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EntityResponse(BaseModel):
    """Base response fields for all domain entities."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    version: int
    owner: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
