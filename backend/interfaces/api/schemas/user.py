from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Public user representation — password_hash is never included."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: str
    organization_id: Optional[str] = None
    is_active: bool
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
