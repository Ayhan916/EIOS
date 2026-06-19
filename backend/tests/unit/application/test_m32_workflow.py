"""Unit tests for M32 Disclosure Workflow transitions."""

from __future__ import annotations

import pytest

from application.disclosure.workflow import transition_disclosure


class TestValidTransitions:
    def test_not_started_to_draft_is_valid(self):
        updates = transition_disclosure(
            current_status="Not Started",
            to_status="Draft",
            narrative_text="Any text.",
            actor_id="user-1",
        )
        assert updates["disclosure_status"] == "Draft"

    def test_draft_to_in_review_sets_reviewer(self):
        updates = transition_disclosure(
            current_status="Draft",
            to_status="In Review",
            narrative_text="Prepared narrative.",
            actor_id="user-1",
        )
        assert updates["disclosure_status"] == "In Review"
        assert updates["reviewed_by"] == "user-1"

    def test_in_review_to_approved_sets_approver(self):
        updates = transition_disclosure(
            current_status="In Review",
            to_status="Approved",
            narrative_text="Prepared narrative.",
            actor_id="user-2",
            reviewed_by="user-1",
        )
        assert updates["disclosure_status"] == "Approved"
        assert updates["approved_by"] == "user-2"

    def test_in_review_back_to_draft_resets_reviewer(self):
        updates = transition_disclosure(
            current_status="In Review",
            to_status="Draft",
            narrative_text="Prepared narrative.",
            actor_id="user-2",
            reviewed_by="user-1",
        )
        assert updates["disclosure_status"] == "Draft"
        assert updates["reviewed_by"] is None

    def test_approved_to_published(self):
        updates = transition_disclosure(
            current_status="Approved",
            to_status="Published",
            narrative_text="Complete.",
            actor_id="user-3",
            reviewed_by="user-1",
            approved_by="user-2",
        )
        assert updates["disclosure_status"] == "Published"


class TestFourEyesPrinciple:
    def test_approver_cannot_be_reviewer(self):
        with pytest.raises(ValueError, match="Four-eyes"):
            transition_disclosure(
                current_status="In Review",
                to_status="Approved",
                narrative_text="Text.",
                actor_id="user-1",
                reviewed_by="user-1",
            )

    def test_different_approver_and_reviewer_passes(self):
        updates = transition_disclosure(
            current_status="In Review",
            to_status="Approved",
            narrative_text="Text.",
            actor_id="user-2",
            reviewed_by="user-1",
        )
        assert updates["approved_by"] == "user-2"

    def test_approve_without_reviewer_passes(self):
        # reviewed_by=None means no reviewer recorded yet — should pass
        updates = transition_disclosure(
            current_status="In Review",
            to_status="Approved",
            narrative_text="Text.",
            actor_id="user-2",
            reviewed_by=None,
        )
        assert updates["approved_by"] == "user-2"


class TestNarrativeRequired:
    def test_submit_for_review_requires_narrative(self):
        with pytest.raises(ValueError, match="narrative"):
            transition_disclosure(
                current_status="Draft",
                to_status="In Review",
                narrative_text="",
                actor_id="user-1",
            )

    def test_submit_for_review_whitespace_narrative_rejected(self):
        with pytest.raises(ValueError, match="narrative"):
            transition_disclosure(
                current_status="Draft",
                to_status="In Review",
                narrative_text="   ",
                actor_id="user-1",
            )

    def test_draft_transition_no_narrative_ok(self):
        # Not Started → Draft doesn't need narrative
        updates = transition_disclosure(
            current_status="Not Started",
            to_status="Draft",
            narrative_text="",
            actor_id="user-1",
        )
        assert updates["disclosure_status"] == "Draft"


class TestInvalidTransitions:
    def test_published_cannot_transition(self):
        with pytest.raises(ValueError):
            transition_disclosure(
                current_status="Published",
                to_status="Draft",
                actor_id="user-1",
            )

    def test_draft_cannot_jump_to_approved(self):
        with pytest.raises(ValueError):
            transition_disclosure(
                current_status="Draft",
                to_status="Approved",
                narrative_text="Text.",
                actor_id="user-1",
            )

    def test_unknown_status_raises(self):
        with pytest.raises(ValueError):
            transition_disclosure(
                current_status="Revoked",
                to_status="Draft",
                actor_id="user-1",
            )

    def test_invalid_target_status_raises(self):
        with pytest.raises(ValueError):
            transition_disclosure(
                current_status="Draft",
                to_status="Cancelled",
                actor_id="user-1",
            )
