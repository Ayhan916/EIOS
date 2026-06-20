"""M35 Questionnaire Service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_assignment(status: str = "assigned") -> MagicMock:
    a = MagicMock()
    a.id = "assign-1"
    a.template_id = "tmpl-1"
    a.template_version = "1.0"
    a.supplier_id = "sup-1"
    a.organization_id = "org-1"
    a.assigned_by_user_id = "user-1"
    a.questionnaire_status = status
    a.due_date = None
    a.assigned_at = datetime.now(UTC)
    a.submitted_at = None
    a.reviewed_at = None
    a.reviewed_by = None
    a.reviewer_comments = ""
    a.score = None
    a.created_at = datetime.now(UTC)
    a.updated_at = datetime.now(UTC)
    return a


class TestAssignQuestionnaire:
    @pytest.mark.asyncio
    async def test_missing_template_raises(self) -> None:
        from application.supplier_portal.questionnaire_service import assign_questionnaire

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await assign_questionnaire(
                template_id="no-such-template",
                supplier_id="sup-1",
                organization_id="org-1",
                assigned_by_user_id="user-1",
                session=session,
            )


class TestSaveAnswer:
    @pytest.mark.asyncio
    async def test_assignment_not_in_editable_status_raises(self) -> None:
        from application.supplier_portal.questionnaire_service import save_answer

        assignment = _make_assignment("submitted")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=assignment)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot edit"):
            await save_answer(
                assignment_id="assign-1",
                question_id="q-1",
                supplier_user_id="u-1",
                supplier_id="sup-1",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_new_answer_created(self) -> None:
        from application.supplier_portal.questionnaire_service import save_answer

        assignment = _make_assignment("assigned")
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        call_count = [0]
        mock_assign_result = MagicMock()
        mock_assign_result.scalar_one_or_none = MagicMock(return_value=assignment)
        # F9: question validation — return a valid question object
        mock_question = MagicMock()
        mock_question.id = "q-1"
        mock_question_result = MagicMock()
        mock_question_result.scalar_one_or_none = MagicMock(return_value=mock_question)
        # existing-answer check — None means create new
        mock_answer_result = MagicMock()
        mock_answer_result.scalar_one_or_none = MagicMock(return_value=None)

        async def execute_side_effect(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_assign_result
            if call_count[0] == 2:
                return mock_question_result
            return mock_answer_result

        session.execute = AsyncMock(side_effect=execute_side_effect)

        answer = await save_answer(
            assignment_id="assign-1",
            question_id="q-1",
            supplier_user_id="u-1",
            supplier_id="sup-1",
            answer_text="Yes",
            session=session,
        )
        session.add.assert_called()
        assert assignment.questionnaire_status == "in_progress"


class TestSubmitQuestionnaire:
    @pytest.mark.asyncio
    async def test_in_progress_transitions_to_submitted(self) -> None:
        from application.supplier_portal.questionnaire_service import submit_questionnaire

        assignment = _make_assignment("in_progress")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=assignment)
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await submit_questionnaire("assign-1", "sup-1", session=session)
        assert result.questionnaire_status == "submitted"

    @pytest.mark.asyncio
    async def test_already_submitted_raises(self) -> None:
        from application.supplier_portal.questionnaire_service import submit_questionnaire

        assignment = _make_assignment("submitted")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=assignment)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot submit"):
            await submit_questionnaire("assign-1", "sup-1", session=session)


class TestReviewAssignment:
    @pytest.mark.asyncio
    async def test_invalid_new_status_raises(self) -> None:
        from application.supplier_portal.questionnaire_service import review_assignment

        session = AsyncMock()
        with pytest.raises(ValueError, match="Invalid review status"):
            await review_assignment(
                assignment_id="assign-1",
                organization_id="org-1",
                reviewed_by="user-1",
                new_status="in_progress",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_not_submitted_raises(self) -> None:
        from application.supplier_portal.questionnaire_service import review_assignment

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await review_assignment(
                assignment_id="assign-1",
                organization_id="org-1",
                reviewed_by="user-1",
                new_status="approved",
                session=session,
            )

    @pytest.mark.asyncio
    async def test_approve_with_score(self) -> None:
        from application.supplier_portal.questionnaire_service import review_assignment

        assignment = _make_assignment("submitted")
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=assignment)
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await review_assignment(
            assignment_id="assign-1",
            organization_id="org-1",
            reviewed_by="user-1",
            new_status="approved",
            score=87.5,
            session=session,
        )
        assert result.questionnaire_status == "approved"
        assert result.score == 87.5
