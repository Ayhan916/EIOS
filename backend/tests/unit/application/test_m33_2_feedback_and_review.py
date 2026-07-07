"""M33.2 — Copilot Feedback & Executive Review Domain Tests.

Tests the domain entities and schema validation for:
- CopilotFeedback (helpful/not_helpful/incorrect/outdated)
- CopilotAnswerReview (approved/misleading/investigate)
No I/O — pure domain and schema validation.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.copilot_audit import CopilotAnswerReview, CopilotFeedback
from domain.enums import EntityStatus, FeedbackRating, ReviewDecision
from interfaces.api.schemas.copilot_audit import (
    FeedbackRequest,
    ReviewRequest,
)


class TestFeedbackDomain:
    def test_feedback_creates_with_valid_rating(self):
        fb = CopilotFeedback(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            user_id="user-1",
            rating=FeedbackRating.HELPFUL,
            reason="Very clear and accurate.",
            status=EntityStatus.ACTIVE,
        )
        assert fb.rating == FeedbackRating.HELPFUL
        assert fb.reason == "Very clear and accurate."
        assert fb.organization_id == "org-1"

    def test_feedback_id_auto_generated(self):
        fb = CopilotFeedback(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            user_id="user-1",
            rating=FeedbackRating.NOT_HELPFUL,
            status=EntityStatus.ACTIVE,
        )
        assert len(fb.id) > 0

    def test_feedback_submitted_at_defaults_to_now(self):
        before = datetime.now(UTC)
        fb = CopilotFeedback(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            user_id="user-1",
            rating=FeedbackRating.INCORRECT,
            status=EntityStatus.ACTIVE,
        )
        after = datetime.now(UTC)
        assert before <= fb.submitted_at <= after

    def test_all_valid_feedback_ratings(self):
        for rating in FeedbackRating:
            fb = CopilotFeedback(
                message_id="msg-1",
                conversation_id="conv-1",
                organization_id="org-1",
                user_id="user-1",
                rating=rating,
                status=EntityStatus.ACTIVE,
            )
            assert fb.rating == rating

    def test_feedback_reason_defaults_to_empty(self):
        fb = CopilotFeedback(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            user_id="user-1",
            rating=FeedbackRating.OUTDATED,
            status=EntityStatus.ACTIVE,
        )
        assert fb.reason == ""


class TestReviewDomain:
    def test_review_creates_with_approved_decision(self):
        review = CopilotAnswerReview(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            reviewer_id="exec-1",
            decision=ReviewDecision.APPROVED,
            notes="Answer is factually accurate.",
            status=EntityStatus.ACTIVE,
        )
        assert review.decision == ReviewDecision.APPROVED
        assert review.reviewer_id == "exec-1"

    def test_review_misleading_decision(self):
        review = CopilotAnswerReview(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            reviewer_id="exec-1",
            decision=ReviewDecision.MISLEADING,
            status=EntityStatus.ACTIVE,
        )
        assert review.decision == ReviewDecision.MISLEADING

    def test_review_investigate_decision(self):
        review = CopilotAnswerReview(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            reviewer_id="exec-1",
            decision=ReviewDecision.INVESTIGATE,
            status=EntityStatus.ACTIVE,
        )
        assert review.decision == ReviewDecision.INVESTIGATE

    def test_review_notes_default_to_empty(self):
        review = CopilotAnswerReview(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            reviewer_id="exec-1",
            decision=ReviewDecision.APPROVED,
            status=EntityStatus.ACTIVE,
        )
        assert review.notes == ""

    def test_review_id_auto_generated(self):
        review = CopilotAnswerReview(
            message_id="msg-1",
            conversation_id="conv-1",
            organization_id="org-1",
            reviewer_id="exec-1",
            decision=ReviewDecision.APPROVED,
            status=EntityStatus.ACTIVE,
        )
        assert len(review.id) > 0

    def test_all_valid_review_decisions(self):
        for decision in ReviewDecision:
            review = CopilotAnswerReview(
                message_id="msg-1",
                conversation_id="conv-1",
                organization_id="org-1",
                reviewer_id="exec-1",
                decision=decision,
                status=EntityStatus.ACTIVE,
            )
            assert review.decision == decision


class TestFeedbackRequestSchema:
    def test_valid_helpful_rating(self):
        req = FeedbackRequest(rating="helpful", reason="Great answer")
        assert req.rating == "helpful"

    def test_valid_not_helpful_rating(self):
        req = FeedbackRequest(rating="not_helpful")
        assert req.rating == "not_helpful"

    def test_valid_incorrect_rating(self):
        req = FeedbackRequest(rating="incorrect", reason="Wrong data cited")
        assert req.rating == "incorrect"

    def test_valid_outdated_rating(self):
        req = FeedbackRequest(rating="outdated")
        assert req.rating == "outdated"

    def test_invalid_rating_raises(self):
        with pytest.raises(Exception):
            FeedbackRequest(rating="unknown_rating")

    def test_reason_defaults_to_empty(self):
        req = FeedbackRequest(rating="helpful")
        assert req.reason == ""

    def test_reason_max_length_accepted(self):
        req = FeedbackRequest(rating="helpful", reason="x" * 1000)
        assert len(req.reason) == 1000

    def test_reason_over_max_length_raises(self):
        with pytest.raises(Exception):
            FeedbackRequest(rating="helpful", reason="x" * 1001)


class TestReviewRequestSchema:
    def test_valid_approved_decision(self):
        req = ReviewRequest(decision="approved")
        assert req.decision == "approved"

    def test_valid_misleading_decision(self):
        req = ReviewRequest(decision="misleading", notes="Answer overstates compliance.")
        assert req.decision == "misleading"

    def test_valid_investigate_decision(self):
        req = ReviewRequest(decision="investigate")
        assert req.decision == "investigate"

    def test_invalid_decision_raises(self):
        with pytest.raises(Exception):
            ReviewRequest(decision="reject")

    def test_notes_defaults_to_empty(self):
        req = ReviewRequest(decision="approved")
        assert req.notes == ""

    def test_notes_max_length_accepted(self):
        req = ReviewRequest(decision="approved", notes="n" * 2000)
        assert len(req.notes) == 2000

    def test_notes_over_max_length_raises(self):
        with pytest.raises(Exception):
            ReviewRequest(decision="approved", notes="n" * 2001)


class TestFeedbackEnums:
    def test_feedback_rating_values(self):
        assert FeedbackRating.HELPFUL == "helpful"
        assert FeedbackRating.NOT_HELPFUL == "not_helpful"
        assert FeedbackRating.INCORRECT == "incorrect"
        assert FeedbackRating.OUTDATED == "outdated"

    def test_review_decision_values(self):
        assert ReviewDecision.APPROVED == "approved"
        assert ReviewDecision.MISLEADING == "misleading"
        assert ReviewDecision.INVESTIGATE == "investigate"
