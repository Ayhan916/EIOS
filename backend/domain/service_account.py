from __future__ import annotations

from dataclasses import dataclass

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class ServiceAccount(BaseEntity):
    """Machine identity that owns API keys but is not a human user."""

    organization_id: str
    name: str = ""
    description: str = ""
    is_active: bool = True
