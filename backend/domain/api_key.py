from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class ApiKey(BaseEntity):
    """Tenant-scoped API key for machine-to-machine authentication."""

    organization_id: str
    service_account_id: str | None = None
    name: str = ""
    description: str = ""
    key_hash: str = ""
    key_prefix: str = ""
    scopes: list[str] = field(default_factory=list)
    is_active: bool = True
    last_used_at: datetime | None = None
    requests_total: int = 0
    requests_this_minute: int = 0
    minute_window_start: datetime | None = None
    requests_this_hour: int = 0
    hour_window_start: datetime | None = None
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    revoked_at: datetime | None = None
    revoked_by: str | None = None
