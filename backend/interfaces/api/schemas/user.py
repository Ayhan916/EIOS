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
    notification_preferences: dict = {}
    mfa_enabled: bool = False


class NotificationPreferencesUpdate(BaseModel):
    """Strict update — only the 4 supported keys are accepted."""
    email_workflow_completed: bool | None = None
    email_action_overdue: bool | None = None
    email_assessment_approved: bool | None = None
    email_recommendation_assigned: bool | None = None


class PatchMeRequest(BaseModel):
    notification_preferences: NotificationPreferencesUpdate | None = None
    display_name: str | None = None


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
