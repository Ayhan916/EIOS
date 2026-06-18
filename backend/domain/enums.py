"""
EIOS Domain Enumerations

EntityStatus: 9-state lifecycle per architecture/012 (ASTATE-0001).
All other enums are architecturally stable classifications.
"""

from enum import Enum


class EntityStatus(str, Enum):
    CREATED = "Created"
    DRAFT = "Draft"
    VALIDATED = "Validated"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    ARCHIVED = "Archived"
    DELETED = "Deleted"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ConfidenceLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ControlType(str, Enum):
    PREVENTIVE = "Preventive"
    DETECTIVE = "Detective"
    CORRECTIVE = "Corrective"


class EvidenceType(str, Enum):
    DOCUMENT = "Document"
    REPORT = "Report"
    PUBLICATION = "Publication"
    WEBSITE = "Website"
    DATA = "Data"
    TESTIMONY = "Testimony"


class UserRole(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


_ROLE_ORDER: dict[str, int] = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.REVIEWER: 3,
    UserRole.ADMIN: 4,
}


def has_min_role(user_role: str, min_role: UserRole) -> bool:
    """Return True if user_role meets or exceeds min_role."""
    user_order = _ROLE_ORDER.get(user_role, 0)
    return user_order >= _ROLE_ORDER[min_role]


class ActionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"


class NotificationType(str, Enum):
    WORKFLOW_COMPLETED = "workflow_completed"
    ACTION_OVERDUE = "action_overdue"
    ASSESSMENT_APPROVED = "assessment_approved"
    RECOMMENDATION_ASSIGNED = "recommendation_assigned"
    REVIEWER_ASSIGNED = "reviewer_assigned"
    REVIEW_SUBMITTED = "review_submitted"
    CHANGES_REQUESTED = "changes_requested"
    COMMENT_MENTION = "comment_mention"


class EvidenceStrength(str, Enum):
    WEAK = "Weak"
    MODERATE = "Moderate"
    STRONG = "Strong"
    VERY_STRONG = "Very Strong"


class ReviewStatus(str, Enum):
    DRAFT = "Draft"
    IN_REVIEW = "InReview"
    CHANGES_REQUESTED = "ChangesRequested"
    APPROVED = "Approved"
    ARCHIVED = "Archived"


class ReviewActionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


# Allowed review status transitions: {from_status: {to_status, ...}}
_REVIEW_TRANSITIONS: dict[ReviewStatus, set[ReviewStatus]] = {
    ReviewStatus.DRAFT: {ReviewStatus.IN_REVIEW},
    ReviewStatus.IN_REVIEW: {ReviewStatus.APPROVED, ReviewStatus.CHANGES_REQUESTED},
    ReviewStatus.CHANGES_REQUESTED: {ReviewStatus.IN_REVIEW},
    ReviewStatus.APPROVED: {ReviewStatus.ARCHIVED},
    ReviewStatus.ARCHIVED: set(),
}


def is_valid_review_transition(from_status: ReviewStatus, to_status: ReviewStatus) -> bool:
    return to_status in _REVIEW_TRANSITIONS.get(from_status, set())
