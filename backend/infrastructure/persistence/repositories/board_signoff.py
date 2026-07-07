"""Repositories — Board Sign-off Trail (CSDDD Art. 22)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.board_signoff import BoardDecision, BoardSignoffRequest
from domain.enums import BoardSignoffStatus
from infrastructure.persistence.models.board_signoff import (
    BoardDecisionModel,
    BoardSignoffRequestModel,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _request_to_domain(m: BoardSignoffRequestModel) -> BoardSignoffRequest:
    return BoardSignoffRequest(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        signoff_type=m.signoff_type,
        entity_type=m.entity_type,
        entity_id=m.entity_id,
        description=m.description,
        status=m.status,
        requested_by=m.requested_by,
        requested_at=m.requested_at,
        due_date=m.due_date,
        approved_at=m.approved_at,
        approved_by=m.approved_by,
        approved_by_role=m.approved_by_role,
        rejection_reason=m.rejection_reason,
        document_ref=m.document_ref,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _decision_to_domain(m: BoardDecisionModel) -> BoardDecision:
    return BoardDecision(
        id=m.id,
        organization_id=m.organization_id,
        request_id=m.request_id,
        decision=m.decision,
        decided_by=m.decided_by,
        decided_by_role=m.decided_by_role,
        comment=m.comment,
        decided_at=m.decided_at,
    )


class SQLBoardSignoffRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_org(
        self,
        organization_id: str,
        status: str | None = None,
        signoff_type: str | None = None,
    ) -> list[BoardSignoffRequest]:
        stmt = select(BoardSignoffRequestModel).where(
            BoardSignoffRequestModel.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(BoardSignoffRequestModel.status == status)
        if signoff_type:
            stmt = stmt.where(BoardSignoffRequestModel.signoff_type == signoff_type)
        stmt = stmt.order_by(BoardSignoffRequestModel.created_at.desc())
        return [_request_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, request_id: str, organization_id: str) -> BoardSignoffRequest | None:
        m = self._s.get(BoardSignoffRequestModel, request_id)
        if not m or m.organization_id != organization_id:
            return None
        return _request_to_domain(m)

    def create(
        self,
        organization_id: str,
        title: str,
        signoff_type: str,
        description: str,
        entity_type: str | None,
        entity_id: str | None,
        requested_by: str,
        due_date: datetime | None,
        document_ref: str | None,
    ) -> BoardSignoffRequest:
        m = BoardSignoffRequestModel(
            id=str(uuid4()),
            organization_id=organization_id,
            title=title,
            signoff_type=signoff_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            status=BoardSignoffStatus.PENDING.value,
            requested_by=requested_by,
            requested_at=_now(),
            due_date=due_date,
            approved_at=None,
            approved_by=None,
            approved_by_role=None,
            rejection_reason=None,
            document_ref=document_ref,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(m)
        self._s.flush()
        return _request_to_domain(m)

    def approve(
        self,
        request_id: str,
        organization_id: str,
        approved_by: str,
        approved_by_role: str,
        comment: str | None,
    ) -> BoardSignoffRequest | None:
        """HUMAN BOARD MEMBER / ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen.
        Records formal board approval per CSDDD Art. 22 Abs. 1."""
        m = self._s.get(BoardSignoffRequestModel, request_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = BoardSignoffStatus.APPROVED.value
        m.approved_at = _now()
        m.approved_by = approved_by
        m.approved_by_role = approved_by_role
        m.updated_at = _now()
        self._s.add(
            BoardDecisionModel(
                id=str(uuid4()),
                organization_id=organization_id,
                request_id=request_id,
                decision="approved",
                decided_by=approved_by,
                decided_by_role=approved_by_role,
                comment=comment,
                decided_at=_now(),
            )
        )
        self._s.flush()
        return _request_to_domain(m)

    def reject(
        self,
        request_id: str,
        organization_id: str,
        rejected_by: str,
        rejected_by_role: str,
        reason: str,
    ) -> BoardSignoffRequest | None:
        """HUMAN BOARD MEMBER / ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
        m = self._s.get(BoardSignoffRequestModel, request_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = BoardSignoffStatus.REJECTED.value
        m.rejection_reason = reason
        m.updated_at = _now()
        self._s.add(
            BoardDecisionModel(
                id=str(uuid4()),
                organization_id=organization_id,
                request_id=request_id,
                decision="rejected",
                decided_by=rejected_by,
                decided_by_role=rejected_by_role,
                comment=reason,
                decided_at=_now(),
            )
        )
        self._s.flush()
        return _request_to_domain(m)

    def withdraw(self, request_id: str, organization_id: str) -> BoardSignoffRequest | None:
        m = self._s.get(BoardSignoffRequestModel, request_id)
        if not m or m.organization_id != organization_id:
            return None
        m.status = BoardSignoffStatus.WITHDRAWN.value
        m.updated_at = _now()
        self._s.flush()
        return _request_to_domain(m)

    def decisions(self, request_id: str, organization_id: str) -> list[BoardDecision]:
        stmt = (
            select(BoardDecisionModel)
            .where(
                BoardDecisionModel.request_id == request_id,
                BoardDecisionModel.organization_id == organization_id,
            )
            .order_by(BoardDecisionModel.decided_at.desc())
        )
        return [_decision_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def dashboard(self, organization_id: str) -> dict:
        all_r = self.list_org(organization_id)
        pending = [r for r in all_r if r.status == BoardSignoffStatus.PENDING.value]
        approved = [r for r in all_r if r.status == BoardSignoffStatus.APPROVED.value]
        rejected = [r for r in all_r if r.status == BoardSignoffStatus.REJECTED.value]
        overdue = [r for r in pending if r.due_date and r.due_date < _now()]
        return {
            "total": len(all_r),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "overdue": len(overdue),
            "approval_rate_pct": round(
                (len(approved) / (len(approved) + len(rejected)) * 100)
                if (approved or rejected)
                else 0.0,
                1,
            ),
        }
