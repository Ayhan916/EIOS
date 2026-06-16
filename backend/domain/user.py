"""
EIOS Domain Model — User

Canonical Enterprise Object per architecture/026.
Represents an authenticated platform participant.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class User(BaseEntity):
    email: str
    display_name: str
    role: str = ""
    organization_id: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    password_hash: Optional[str] = None
