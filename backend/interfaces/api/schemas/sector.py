from pydantic import BaseModel, Field

from .base import EntityResponse


class SectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    nace_code: str = Field(min_length=1, max_length=20)
    nace_description: str | None = None
    risk_profile: str | None = None
    parent_sector_id: str | None = None
    organization_id: str | None = None


class SectorResponse(EntityResponse):
    name: str
    nace_code: str
    nace_description: str | None = None
    risk_profile: str | None = None
    parent_sector_id: str | None = None
    organization_id: str | None = None
