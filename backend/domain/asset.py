"""
EIOS Domain Model — Asset

Canonical Enterprise Object per architecture/026.
Represents an enterprise asset (Data, Document, System, Knowledge).
"""

from dataclasses import dataclass
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Asset(BaseEntity):
    title: str
    description: str
    asset_type: str = ""
    asset_class: Optional[str] = None
    location: Optional[str] = None
    organization_id: Optional[str] = None
