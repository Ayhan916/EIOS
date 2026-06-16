"""
EIOS Canonical Base Entity

All enterprise domain entities shall inherit from this class.
Fields conform to architecture/008 (Attribute Model, AATTR-0001).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from .enums import EntityStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class BaseEntity:
    id: str = field(default_factory=lambda: str(uuid4()))
    status: EntityStatus = field(default=EntityStatus.DRAFT)
    version: int = 1
    owner: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
