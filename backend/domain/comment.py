"""
EIOS Domain Model — Comment (M26)

Polymorphic comment attached to any entity (Assessment, Finding, Risk, Recommendation).
Supports @mentions, soft-delete, and edit tracking. All comments are immutable
in the audit sense — edits create a new version record via edited_at timestamp.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Comment(BaseEntity):
    entity_type: str  # "Assessment" | "Finding" | "Risk" | "Recommendation"
    entity_id: str
    author_id: str
    content: str
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    # Resolved list of mentioned user IDs (extracted from content at save time)
    mentioned_user_ids: list[str] = field(default_factory=list)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_edited(self) -> bool:
        return self.edited_at is not None
