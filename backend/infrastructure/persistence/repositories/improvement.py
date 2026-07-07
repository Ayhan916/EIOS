"""Repository for ImprovementProposal (GAP-05)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.improvement import ImprovementProposal
from infrastructure.persistence.models.improvement import ImprovementProposalModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLImprovementRepository(BaseRepository[ImprovementProposal, ImprovementProposalModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ImprovementProposalModel)

    def _to_model(self, d: ImprovementProposal) -> ImprovementProposalModel:
        return ImprovementProposalModel(
            id=d.id,
            status=d.status.value if hasattr(d.status, "value") else d.status,
            version=d.version,
            owner=d.owner,
            created_by=d.created_by,
            updated_by=d.updated_by,
            created_at=d.created_at,
            updated_at=d.updated_at,
            weakness_type=d.weakness_type,
            affected_module=d.affected_module,
            current_value=d.current_value,
            target_value=d.target_value,
            expected_impact=d.expected_impact,
            priority_score=d.priority_score,
            title=d.title,
            description=d.description,
            suggested_action=d.suggested_action,
            approval_status=d.approval_status,
            approved_by_user_id=d.approved_by_user_id,
            approved_at=d.approved_at,
            rejected_by_user_id=d.rejected_by_user_id,
            rejected_at=d.rejected_at,
            reject_reason=d.reject_reason,
            before_evaluation_run_id=d.before_evaluation_run_id,
            after_evaluation_run_id=d.after_evaluation_run_id,
            verified_improvement=d.verified_improvement,
            verified_at=d.verified_at,
        )

    def _to_domain(self, m: ImprovementProposalModel) -> ImprovementProposal:
        return ImprovementProposal(
            id=m.id,
            status=EntityStatus(m.status),
            version=m.version,
            owner=m.owner or "",
            created_by=m.created_by or "",
            updated_by=m.updated_by or "",
            created_at=m.created_at or datetime.now(UTC),
            updated_at=m.updated_at or datetime.now(UTC),
            weakness_type=m.weakness_type,
            affected_module=m.affected_module,
            current_value=m.current_value,
            target_value=m.target_value,
            expected_impact=m.expected_impact,
            priority_score=m.priority_score,
            title=m.title,
            description=m.description,
            suggested_action=m.suggested_action,
            approval_status=m.approval_status,
            approved_by_user_id=m.approved_by_user_id,
            approved_at=m.approved_at,
            rejected_by_user_id=m.rejected_by_user_id,
            rejected_at=m.rejected_at,
            reject_reason=m.reject_reason,
            before_evaluation_run_id=m.before_evaluation_run_id,
            after_evaluation_run_id=m.after_evaluation_run_id,
            verified_improvement=m.verified_improvement,
            verified_at=m.verified_at,
        )

    async def save(self, proposal: ImprovementProposal) -> ImprovementProposal:
        existing = await self._session.get(ImprovementProposalModel, proposal.id)
        m = self._to_model(proposal)
        if existing is None:
            self._session.add(m)
        else:
            for attr, val in vars(m).items():
                if not attr.startswith("_"):
                    setattr(existing, attr, val)
            m = existing
        await self._session.flush()
        return self._to_domain(m)

    async def get_by_id(self, proposal_id: str) -> ImprovementProposal | None:
        m = await self._session.get(ImprovementProposalModel, proposal_id)
        return self._to_domain(m) if m else None

    async def list_all(
        self,
        *,
        status_filter: str | None = None,
        limit: int = 50,
    ) -> list[ImprovementProposal]:
        stmt = select(ImprovementProposalModel).order_by(
            ImprovementProposalModel.priority_score.desc(),
            ImprovementProposalModel.created_at.desc(),
        )
        if status_filter:
            stmt = stmt.where(ImprovementProposalModel.approval_status == status_filter)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def count_by_status(self) -> dict[str, int]:
        result = await self._session.execute(select(ImprovementProposalModel.approval_status))
        counts: dict[str, int] = {}
        for row in result.scalars().all():
            counts[row] = counts.get(row, 0) + 1
        return counts
