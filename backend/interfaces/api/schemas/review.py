from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from domain.enums import ReviewActionType


class SubmitForReviewRequest(BaseModel):
    reviewer_id: str | None = None
    review_due_date: datetime | None = None


class AssignReviewerRequest(BaseModel):
    reviewer_id: str
    review_due_date: datetime | None = None


class ReviewActionRequest(BaseModel):
    action_type: ReviewActionType
    comment: str | None = Field(default=None, max_length=4000)


class ReviewActionResponse(BaseModel):
    id: str
    assessment_id: str
    actor_id: str
    actor_email: str
    action_type: str
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityEvent(BaseModel):
    event_type: str  # "audit" | "comment" | "review_action"
    timestamp: datetime
    actor_id: str | None = None
    actor_name: str | None = None
    action: str
    detail: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    # Populated only for comment events
    comment_id: str | None = None
    comment_content: str | None = None
