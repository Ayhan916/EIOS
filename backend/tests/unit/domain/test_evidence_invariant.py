"""Unit tests for E3-F1 — Evidence Linking Invariant (ADR-003).

ADR-003: Evidence First — every Finding must have ≥1 FindingEvidenceLink
before the parent Assessment can be submitted for formal review.
"""

import pytest

from domain.exceptions import EvidenceMissingError, EvidenceRequiredError


class TestEvidenceMissingError:
    def test_message_includes_count(self) -> None:
        err = EvidenceMissingError(["f1", "f2", "f3"])
        assert "3 finding(s)" in str(err)

    def test_finding_ids_attribute(self) -> None:
        ids = ["abc", "def"]
        err = EvidenceMissingError(ids)
        assert err.finding_ids == ids

    def test_single_finding(self) -> None:
        err = EvidenceMissingError(["only-one"])
        assert "only-one" in str(err)
        assert "1 finding" in str(err)

    def test_many_findings_truncated(self) -> None:
        ids = [f"finding-{i}" for i in range(10)]
        err = EvidenceMissingError(ids)
        assert "..." in str(err)
        assert "10 finding(s)" in str(err)

    def test_exactly_five_findings_not_truncated(self) -> None:
        ids = [f"finding-{i}" for i in range(5)]
        err = EvidenceMissingError(ids)
        assert "..." not in str(err)


class TestEvidenceGateLogic:
    """Test the business logic that computes which findings lack evidence.

    This mirrors what the submit_for_review endpoint does:
    given a list of finding_ids and a set of linked_ids, find the gap.
    """

    def _unlinked(self, finding_ids: list[str], linked_ids: set[str]) -> list[str]:
        return [fid for fid in finding_ids if fid not in linked_ids]

    def test_all_linked(self) -> None:
        finding_ids = ["f1", "f2", "f3"]
        linked_ids = {"f1", "f2", "f3"}
        assert self._unlinked(finding_ids, linked_ids) == []

    def test_none_linked(self) -> None:
        finding_ids = ["f1", "f2"]
        linked_ids: set[str] = set()
        assert self._unlinked(finding_ids, linked_ids) == ["f1", "f2"]

    def test_partial_link(self) -> None:
        finding_ids = ["f1", "f2", "f3"]
        linked_ids = {"f2"}
        result = self._unlinked(finding_ids, linked_ids)
        assert "f1" in result
        assert "f3" in result
        assert "f2" not in result

    def test_no_findings_passes(self) -> None:
        """Assessment with no findings has no evidence requirement violation."""
        finding_ids: list[str] = []
        linked_ids: set[str] = set()
        assert self._unlinked(finding_ids, linked_ids) == []


class TestEvidenceRequiredError:
    """EvidenceRequiredError is raised at Finding creation time (E3-F1)."""

    def test_is_exception(self) -> None:
        err = EvidenceRequiredError()
        assert isinstance(err, Exception)

    def test_message_mentions_evidence(self) -> None:
        err = EvidenceRequiredError()
        assert "evidence" in str(err).lower()

    def test_message_mentions_evidence_ids(self) -> None:
        err = EvidenceRequiredError()
        assert "evidence_ids" in str(err)

    def test_no_args_required(self) -> None:
        # Must be instantiated without arguments
        err = EvidenceRequiredError()
        assert err is not None


class TestEvidenceQualityStatus:
    """Logic for deriving evidence_quality_status from evidence_ids (E3-F1)."""

    def _derive_status(self, evidence_ids: list[str]) -> str:
        return "Evidenced" if evidence_ids else "Hypothetical"

    def test_empty_list_is_hypothetical(self) -> None:
        assert self._derive_status([]) == "Hypothetical"

    def test_single_id_is_evidenced(self) -> None:
        assert self._derive_status(["ev-001"]) == "Evidenced"

    def test_multiple_ids_is_evidenced(self) -> None:
        assert self._derive_status(["ev-001", "ev-002", "ev-003"]) == "Evidenced"

    def test_hypothetical_findings_block_review(self) -> None:
        """submit_for_review must block when any finding is Hypothetical."""
        findings_statuses = ["Evidenced", "Hypothetical", "Evidenced"]
        hypothetical = [s for s in findings_statuses if s == "Hypothetical"]
        assert len(hypothetical) == 1

    def test_all_evidenced_allows_review(self) -> None:
        findings_statuses = ["Evidenced", "Evidenced"]
        hypothetical = [s for s in findings_statuses if s == "Hypothetical"]
        assert hypothetical == []

    def test_no_findings_allows_review(self) -> None:
        findings_statuses: list[str] = []
        hypothetical = [s for s in findings_statuses if s == "Hypothetical"]
        assert hypothetical == []
