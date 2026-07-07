from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    organization_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginResponse(BaseModel):
    """Response for POST /auth/login.

    When MFA is not enabled: access_token, refresh_token, and user are populated.
    When MFA is required: mfa_required=True and mfa_session_token is populated;
    the client must present mfa_session_token to POST /auth/mfa/verify.
    """

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse | None = None
    mfa_required: bool = False
    mfa_session_token: str | None = None


class RefreshResponse(BaseModel):
    """Refresh token rotation: both tokens are replaced on each refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str


# ── M45.1 External Auditor Access ─────────────────────────────────────────────


class ExternalAccessTokenRequest(BaseModel):
    label: str = Field(
        min_length=1, max_length=255, description="Human-readable label (e.g. audit firm name)"
    )
    org_id: str | None = Field(
        default=None, description="Target org; defaults to the admin's own org"
    )


class ExternalAccessTokenResponse(BaseModel):
    token: str
    token_id: str
    label: str
    org_id: str
    expires_at: datetime


class ExternalAccessRevokeRequest(BaseModel):
    token_id: str = Field(description="token_id from ExternalAccessTokenResponse")
