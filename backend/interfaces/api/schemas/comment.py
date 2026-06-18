from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    entity_type: str = Field(description="Assessment | Finding | Risk | Recommendation")
    entity_id: str
    content: str = Field(min_length=1, max_length=4000)


class CommentEdit(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CommentResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    author_id: str
    author_name: str | None = None
    content: str
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    mentioned_user_ids: list[str] = []
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    is_edited: bool = False

    model_config = {"from_attributes": True}
