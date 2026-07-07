"""Unit tests for M32 Disclosure Readiness Engine."""

from __future__ import annotations

from application.disclosure.readiness_engine import (
    APPROVAL_COVERAGE_THRESHOLD,
    PUBLISH_COVERAGE_THRESHOLD,
    REVIEW_COVERAGE_THRESHOLD,
    determine_readiness,
)


class TestNotStarted:
    def test_no_narrative_is_not_started(self):
        status, rationale = determine_readiness(
            disclosure_status="Not Started",
            narrative_text="",
            evidence_coverage=0.8,
        )
        assert status == "Not Started"
        assert "narrative" in rationale.lower()

    def test_draft_status_but_blank_narrative_is_not_started(self):
        status, _ = determine_readiness(
            disclosure_status="Draft",
            narrative_text="   ",
            evidence_coverage=0.9,
        )
        assert status == "Not Started"


class TestDraftReadiness:
    def test_draft_below_threshold_stays_draft(self):
        status, rationale = determine_readiness(
            disclosure_status="Draft",
            narrative_text="Some draft text.",
            evidence_coverage=REVIEW_COVERAGE_THRESHOLD - 0.01,
        )
        assert status == "Draft"
        assert "below" in rationale.lower()

    def test_draft_at_threshold_becomes_ready_for_review(self):
        status, rationale = determine_readiness(
            disclosure_status="Draft",
            narrative_text="Narrative complete.",
            evidence_coverage=REVIEW_COVERAGE_THRESHOLD,
        )
        assert status == "Ready for Review"

    def test_draft_above_threshold_is_ready_for_review(self):
        status, _ = determine_readiness(
            disclosure_status="Draft",
            narrative_text="Detailed narrative.",
            evidence_coverage=0.60,
        )
        assert status == "Ready for Review"


class TestInReview:
    def test_in_review_below_approval_threshold_is_blocked(self):
        status, rationale = determine_readiness(
            disclosure_status="In Review",
            narrative_text="Some text.",
            evidence_coverage=APPROVAL_COVERAGE_THRESHOLD - 0.01,
        )
        assert status == "Blocked"
        assert "below" in rationale.lower()

    def test_in_review_at_approval_threshold_is_ready_for_approval(self):
        status, _ = determine_readiness(
            disclosure_status="In Review",
            narrative_text="Complete narrative.",
            evidence_coverage=APPROVAL_COVERAGE_THRESHOLD,
        )
        assert status == "Ready for Approval"

    def test_in_review_above_threshold_is_ready_for_approval(self):
        status, _ = determine_readiness(
            disclosure_status="In Review",
            narrative_text="Solid narrative.",
            evidence_coverage=0.80,
        )
        assert status == "Ready for Approval"


class TestApproved:
    def test_approved_with_critical_gaps_is_blocked(self):
        status, rationale = determine_readiness(
            disclosure_status="Approved",
            narrative_text="Full narrative.",
            evidence_coverage=0.90,
            critical_gap_count=2,
        )
        assert status == "Blocked"
        assert "critical" in rationale.lower()
        assert "2" in rationale

    def test_approved_below_publish_threshold_is_blocked(self):
        status, rationale = determine_readiness(
            disclosure_status="Approved",
            narrative_text="Full narrative.",
            evidence_coverage=PUBLISH_COVERAGE_THRESHOLD - 0.01,
            critical_gap_count=0,
        )
        assert status == "Blocked"
        assert "below" in rationale.lower()

    def test_approved_at_threshold_no_gaps_is_ready_for_publication(self):
        status, rationale = determine_readiness(
            disclosure_status="Approved",
            narrative_text="Full narrative.",
            evidence_coverage=PUBLISH_COVERAGE_THRESHOLD,
            critical_gap_count=0,
        )
        assert status == "Ready for Publication"
        assert "publication" in rationale.lower()

    def test_approved_high_coverage_no_gaps_is_ready_for_publication(self):
        status, _ = determine_readiness(
            disclosure_status="Approved",
            narrative_text="Full narrative.",
            evidence_coverage=0.95,
            critical_gap_count=0,
        )
        assert status == "Ready for Publication"


class TestPublished:
    def test_published_is_already_published(self):
        status, rationale = determine_readiness(
            disclosure_status="Published",
            narrative_text="Complete.",
            evidence_coverage=0.9,
        )
        assert status == "Ready for Publication"
        assert "published" in rationale.lower()


class TestRationale:
    def test_rationale_always_present(self):
        for st in ["Not Started", "Draft", "In Review", "Approved", "Published"]:
            _, rationale = determine_readiness(
                disclosure_status=st,
                narrative_text="Some text.",
                evidence_coverage=0.6,
                critical_gap_count=0,
            )
            assert isinstance(rationale, str)
            assert len(rationale) > 10

    def test_unknown_status_is_blocked(self):
        status, _ = determine_readiness(
            disclosure_status="Cancelled",
            narrative_text="Text.",
            evidence_coverage=0.9,
        )
        assert status == "Blocked"

    def test_critical_gap_count_defaults_to_zero(self):
        status, _ = determine_readiness(
            disclosure_status="Approved",
            narrative_text="Text.",
            evidence_coverage=PUBLISH_COVERAGE_THRESHOLD,
        )
        assert status == "Ready for Publication"
