from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    country: str | None = None
    industry: str | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    organization_type: str
    country: str | None = None
    industry: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
