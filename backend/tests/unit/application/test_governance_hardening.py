"""
Unit tests for M26.1 Governance Hardening.

Covers:
  1.  Four-eyes: is_valid_review_transition still works (FSM unchanged)
  2.  Four-eyes check is SEPARATE from FSM — no state machine change
  3.  Role hierarchy — analyst below reviewer
  4.  has_min_role correctly classifies each role
"""

from __future__ import annotations

import pytest

from domain.enums import UserRole, has_min_role, is_valid_review_transition, ReviewStatus


class TestFourEyesRoleGuard:
    """Confirm the role hierarchy that enforces four-eyes at the HTTP layer."""

    def test_analyst_does_not_meet_reviewer(self) -> None:
        assert not has_min_role(UserRole.ANALYST.value, UserRole.REVIEWER)

    def test_reviewer_meets_reviewer(self) -> None:
        assert has_min_role(UserRole.REVIEWER.value, UserRole.REVIEWER)

    def test_admin_meets_reviewer(self) -> None:
        assert has_min_role(UserRole.ADMIN.value, UserRole.REVIEWER)

    def test_viewer_does_not_meet_reviewer(self) -> None:
        assert not has_min_role(UserRole.VIEWER.value, UserRole.REVIEWER)

    def test_analyst_does_not_meet_admin(self) -> None:
        assert not has_min_role(UserRole.ANALYST.value, UserRole.ADMIN)

    def test_reviewer_does_not_meet_admin(self) -> None:
        assert not has_min_role(UserRole.REVIEWER.value, UserRole.ADMIN)


class TestFSMUnchanged:
    """The four-eyes fix must not alter any FSM transitions."""

    def test_draft_to_in_review(self) -> None:
        assert is_valid_review_transition(ReviewStatus.DRAFT, ReviewStatus.IN_REVIEW)

    def test_in_review_to_approved(self) -> None:
        assert is_valid_review_transition(ReviewStatus.IN_REVIEW, ReviewStatus.APPROVED)

    def test_in_review_to_changes_requested(self) -> None:
        assert is_valid_review_transition(ReviewStatus.IN_REVIEW, ReviewStatus.CHANGES_REQUESTED)

    def test_changes_requested_back_to_in_review(self) -> None:
        assert is_valid_review_transition(ReviewStatus.CHANGES_REQUESTED, ReviewStatus.IN_REVIEW)

    def test_approved_to_archived(self) -> None:
        assert is_valid_review_transition(ReviewStatus.APPROVED, ReviewStatus.ARCHIVED)

    def test_archived_terminal(self) -> None:
        for target in ReviewStatus:
            assert not is_valid_review_transition(ReviewStatus.ARCHIVED, target)
