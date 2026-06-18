"""
EIOS Domain Model — ReviewAction (M26)

Immutable record of a formal governance decision on an assessment.
Approved, Rejected, or ChangesRequested — each decision is preserved permanently
for audit purposes. Reviewers cannot delete their own decisions.
"""

from dataclasses import dataclass

from .base_entity import BaseEntity
from .enums import ReviewActionType


@dataclass(slots=True, kw_only=True)
class ReviewAction(BaseEntity):
    assessment_id: str
    actor_id: str
    actor_email: str
    action_type: ReviewActionType  # approve | reject | request_changes
    comment: str | None = None     # Optional rationale stored with the decision
