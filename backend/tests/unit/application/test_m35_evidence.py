"""M35 Evidence Service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_submission(status: str = "draft") -> MagicMock:
    sub = MagicMock()
    sub.id = "sub-1"
    sub.evidence_request_id = "req-1"
    sub.supplier_id = "sup-1"
    sub.supplier_user_id = "u-1"
    sub.submission_status = status
    sub.comments = ""
    sub.submitted_at = None
    sub.reviewed_by = None
    sub.reviewed_at = None
    sub.reviewer_comments = ""
    sub.created_at = datetime.now(UTC)
    sub.updated_at = datetime.now(UTC)
    return sub


class TestCreateEvidenceRequest:
    @pytest.mark.asyncio
    async def test_creates_request(self) -> None:
        from application.supplier_portal.evidence_service import create_evidence_request

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        req = await create_evidence_request(
            supplier_id="sup-1",
            organization_id="org-1",
            title="Q4 Carbon Report",
            description="Please upload your 2024 carbon report.",
            created_by_user_id="user-1",
            session=session,
        )
        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert req.title == "Q4 Carbon Report"
        assert req.evidence_status == "open"


class TestSubmitEvidence:
    @pytest.mark.asyncio
    async def test_submit_draft_transitions_to_submitted(self) -> None:
        from application.supplier_portal.evidence_service import submit_evidence

        sub = _make_submission("draft")
        session = AsyncMock()
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none = MagicMock(return_value=sub)
        mock_update_result = MagicMock()

        call_count = [0]

        async def execute_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_sub_result
            return mock_update_result

        session.execute = AsyncMock(side_effect=execute_side_effect)
        session.flush = AsyncMock()

        result = await submit_evidence("sub-1", "sup-1", session=session)
        assert result.submission_status == "submitted"

    @pytest.mark.asyncio
    async def test_already_submitted_raises(self) -> None:
        from application.supplier_portal.evidence_service import submit_evidence

        sub = _make_submission("submitted")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sub)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot submit"):
            await submit_evidence("sub-1", "sup-1", session=session)

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        from application.supplier_portal.evidence_service import submit_evidence

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await submit_evidence("sub-missing", "sup-1", session=session)


class TestReviewSubmission:
    @pytest.mark.asyncio
    async def test_invalid_status_raises(self) -> None:
        from application.supplier_portal.evidence_service import review_submission

        session = AsyncMock()
        with pytest.raises(ValueError, match="Invalid review status"):
            await review_submission(
                submission_id="sub-1",
                organization_id="org-1",
                reviewed_by="reviewer-1",
                new_status="invalid_status",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_accepted_status_propagates(self) -> None:
        from application.supplier_portal.evidence_service import review_submission

        sub = _make_submission("submitted")
        sub.evidence_request_id = "req-1"
        session = AsyncMock()

        call_count = [0]
        mock_sub_result = MagicMock()
        mock_sub_result.scalar_one_or_none = MagicMock(return_value=sub)
        mock_update_result = MagicMock()

        async def execute_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_sub_result
            return mock_update_result

        session.execute = AsyncMock(side_effect=execute_side_effect)
        session.flush = AsyncMock()

        result = await review_submission(
            submission_id="sub-1",
            organization_id="org-1",
            reviewed_by="reviewer-1",
            new_status="accepted",
            session=session,
        )
        assert result.submission_status == "accepted"


class TestAttachFile:
    @pytest.mark.asyncio
    async def test_attach_to_non_draft_raises(self) -> None:
        from application.supplier_portal.evidence_service import attach_file_to_submission

        sub = _make_submission("submitted")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sub)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot add files"):
            await attach_file_to_submission(
                submission_id="sub-1",
                supplier_id="sup-1",
                file_name="report.pdf",
                file_path="/uploads/report.pdf",
                file_size=1024,
                content_type="application/pdf",
                session=session,
            )
