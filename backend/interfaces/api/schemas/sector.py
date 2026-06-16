from typing import Optional

from pydantic import BaseModel, Field

from .base import EntityResponse


class SectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    nace_code: str = Field(min_length=1, max_length=20)
    nace_description: Optional[str] = None
    risk_profile: Optional[str] = None
    parent_sector_id: Optional[str] = None
    organization_id: Optional[str] = None


class SectorResponse(EntityResponse):
    name: str
    nace_code: str
    nace_description: Optional[str] = None
    risk_profile: Optional[str] = None
    parent_sector_id: Optional[str] = None
    organization_id: Optional[str] = None
