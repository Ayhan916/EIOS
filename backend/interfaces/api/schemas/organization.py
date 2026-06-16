from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    organization_type: str
    country: Optional[str] = None
    industry: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
