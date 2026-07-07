"""Pydantic schemas for M30 API Platform endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ── Service Accounts ──────────────────────────────────────────────────────────


class ServiceAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class ServiceAccountResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str
    is_active: bool
    created_at: datetime
    created_by: str | None = None

    model_config = {"from_attributes": True}


# ── API Keys ──────────────────────────────────────────────────────────────────


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    service_account_id: str | None = None
    scopes: list[str] = Field(default_factory=list, min_length=1)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=600)
    rate_limit_per_hour: int = Field(default=1000, ge=10, le=10000)


class ApiKeyCreatedResponse(BaseModel):
    """Returned ONCE at creation — raw_key is never stored and never returned again."""

    id: str
    name: str
    key_prefix: str
    raw_key: str
    scopes: list[str]
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    description: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    service_account_id: str | None = None
    last_used_at: datetime | None = None
    requests_total: int
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    revoked_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Webhook Subscriptions ─────────────────────────────────────────────────────


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    target_url: str = Field(min_length=8)
    events: list[str] = Field(min_length=1)
    secret: str = Field(min_length=16, max_length=256, description="Signing secret for HMAC-SHA256")


class WebhookUpdate(BaseModel):
    name: str | None = None
    target_url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: str
    name: str
    target_url: str
    events: list[str]
    is_active: bool
    failure_count: int
    last_triggered_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Webhook Deliveries ────────────────────────────────────────────────────────


class WebhookDeliveryResponse(BaseModel):
    id: str
    subscription_id: str
    event_type: str
    delivery_status: str
    response_code: int | None = None
    duration_ms: int | None = None
    retry_count: int
    error_message: str | None = None
    delivered_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Usage Analytics ───────────────────────────────────────────────────────────


class ApiKeyUsageSummary(BaseModel):
    id: str
    name: str
    key_prefix: str
    requests_total: int
    last_used_at: datetime | None = None
    is_active: bool
