"""
EIOS Domain Model — Asset

Canonical Enterprise Object per architecture/026.
Represents an enterprise asset (Data, Document, System, Knowledge).
"""

from dataclasses import dataclass

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Asset(BaseEntity):
    title: str
    description: str
    asset_type: str = ""
    asset_class: str | None = None
    location: str | None = None
    organization_id: str | None = None
