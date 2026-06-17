from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """Public user representation — password_hash is never included."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: str
    organization_id: str | None = None
    is_active: bool
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
