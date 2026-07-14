"""Unit tests for E4-F2 — Assessment Immutability Gate (ADR-014).

These tests verify that:
1. ImmutableEntityError carries the expected attributes.
2. The repository save() guard blocks mutations of APPROVED assessments.
3. The APPROVED → ARCHIVED transition is the only permitted write.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.assessment import Assessment
from domain.enums import ReviewStatus
from domain.exceptions import ImmutableEntityError
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.repositories.assessment import SQLAssessmentRepository


class TestImmutableEntityError:
    def test_message_contains_entity_info(self) -> None:
        err = ImmutableEntityError("Assessment", "abc-123")
        assert "Assessment" in str(err)
        assert "abc-123" in str(err)

    def test_attributes_are_set(self) -> None:
        err = ImmutableEntityError("Assessment", "xyz-999")
        assert err.entity_type == "Assessment"
        assert err.entity_id == "xyz-999"


class TestAssessmentRepositoryImmutabilityGuard:
    """Tests for SQLAssessmentRepository.save() immutability check."""

    def _make_repo(self, current_review_status: str | None) -> SQLAssessmentRepository:
        """Return a repository with a mocked session that returns a model with the given status."""
        session = MagicMock()
        if current_review_status is not None:
            existing_model = MagicMock(spec=AssessmentModel)
            existing_model.review_status = current_review_status
            session.get = AsyncMock(return_value=existing_model)
        else:
            session.get = AsyncMock(return_value=None)

        # super().save() path — not reached in the blocking cases
        session.merge = AsyncMock(return_value=MagicMock(spec=AssessmentModel))
        session.flush = AsyncMock()
        return SQLAssessmentRepository(session)

    def _make_assessment(self, new_review_status: ReviewStatus) -> Assessment:
        a = Assessment(title="Test", description="D")
        a.id = "entity-id-001"
        a.review_status = new_review_status
        return a

    @pytest.mark.asyncio
    async def test_approved_assessment_raises_on_content_change(self) -> None:
        repo = self._make_repo(ReviewStatus.APPROVED.value)
        assessment = self._make_assessment(ReviewStatus.APPROVED)  # no status change

        with pytest.raises(ImmutableEntityError) as exc_info:
            await repo.save(assessment)

        assert exc_info.value.entity_id == "entity-id-001"

    @pytest.mark.asyncio
    async def test_approved_to_archived_is_permitted(self) -> None:
        """APPROVED → ARCHIVED is the only allowed write on an approved assessment."""
        repo = self._make_repo(ReviewStatus.APPROVED.value)
        assessment = self._make_assessment(ReviewStatus.ARCHIVED)

        # Should not raise — super().save() will be called
        # We patch _to_model and _to_domain to avoid needing real ORM objects
        repo._to_model = MagicMock(return_value=MagicMock(spec=AssessmentModel))
        repo._to_domain = MagicMock(return_value=assessment)

        result = await repo.save(assessment)
        assert result is assessment

    @pytest.mark.asyncio
    async def test_approved_to_draft_is_blocked(self) -> None:
        repo = self._make_repo(ReviewStatus.APPROVED.value)
        assessment = self._make_assessment(ReviewStatus.DRAFT)

        with pytest.raises(ImmutableEntityError):
            await repo.save(assessment)

    @pytest.mark.asyncio
    async def test_approved_to_in_review_is_blocked(self) -> None:
        repo = self._make_repo(ReviewStatus.APPROVED.value)
        assessment = self._make_assessment(ReviewStatus.IN_REVIEW)

        with pytest.raises(ImmutableEntityError):
            await repo.save(assessment)

    @pytest.mark.asyncio
    async def test_draft_assessment_is_not_blocked(self) -> None:
        """Non-approved assessments save without restrictions."""
        repo = self._make_repo(ReviewStatus.DRAFT.value)
        assessment = self._make_assessment(ReviewStatus.IN_REVIEW)

        repo._to_model = MagicMock(return_value=MagicMock(spec=AssessmentModel))
        repo._to_domain = MagicMock(return_value=assessment)

        result = await repo.save(assessment)
        assert result is assessment

    @pytest.mark.asyncio
    async def test_new_assessment_without_id_is_not_blocked(self) -> None:
        """New entities (no ID yet) bypass the guard entirely."""
        repo = self._make_repo(None)
        assessment = Assessment(title="New", description="D")
        # assessment.id is None by default

        repo._to_model = MagicMock(return_value=MagicMock(spec=AssessmentModel))
        repo._to_domain = MagicMock(return_value=assessment)

        result = await repo.save(assessment)
        assert result is assessment
