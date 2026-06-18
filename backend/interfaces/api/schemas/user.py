from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from domain.enums import UserRole


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
    last_login_at: datetime | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    display_name: str | None = None


class UserInviteRequest(BaseModel):
    email: EmailStr
    display_name: str
    role: UserRole = UserRole.ANALYST


class UserInviteResponse(BaseModel):
    user: UserResponse
    temp_password: str
