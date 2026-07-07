"""Repository for CorrectiveActionPlan (GAP-20).

organization_id is MANDATORY on every query — never omit.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.corrective_action_plan import CorrectiveActionPlan
from domain.enums import EntityStatus
from infrastructure.persistence.models.corrective_action_plan import CorrectiveActionPlanModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLCAPRepository(BaseRepository[CorrectiveActionPlan, CorrectiveActionPlanModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CorrectiveActionPlanModel)

    def _to_model(self, d: CorrectiveActionPlan) -> CorrectiveActionPlanModel:
        return CorrectiveActionPlanModel(
            id=d.id,
            status=d.status.value if hasattr(d.status, "value") else d.status,
            version=d.version,
            owner=d.owner,
            created_by=d.created_by,
            updated_by=d.updated_by,
            created_at=d.created_at,
            updated_at=d.updated_at,
            finding_id=d.finding_id,
            organization_id=d.organization_id,
            title=d.title,
            description=d.description,
            responsible_party=d.responsible_party,
            deadline=d.deadline,
            cap_status=d.cap_status,
            evidence_note=d.evidence_note,
            evidence_file_url=d.evidence_file_url,
            evidence_submitted_at=d.evidence_submitted_at,
            verification_note=d.verification_note,
            verified_by_user_id=d.verified_by_user_id,
            verified_at=d.verified_at,
            insufficient_reason=d.insufficient_reason,
            closed_at=d.closed_at,
            closed_by_user_id=d.closed_by_user_id,
        )

    def _to_domain(self, m: CorrectiveActionPlanModel) -> CorrectiveActionPlan:
        return CorrectiveActionPlan(
            id=m.id,
            status=EntityStatus(m.status),
            version=m.version,
            owner=m.owner or "",
            created_by=m.created_by or "",
            updated_by=m.updated_by or "",
            created_at=m.created_at or datetime.now(UTC),
            updated_at=m.updated_at or datetime.now(UTC),
            finding_id=m.finding_id,
            organization_id=m.organization_id,
            title=m.title,
            description=m.description,
            responsible_party=m.responsible_party,
            deadline=m.deadline,
            cap_status=m.cap_status,
            evidence_note=m.evidence_note,
            evidence_file_url=m.evidence_file_url,
            evidence_submitted_at=m.evidence_submitted_at,
            verification_note=m.verification_note,
            verified_by_user_id=m.verified_by_user_id,
            verified_at=m.verified_at,
            insufficient_reason=m.insufficient_reason,
            closed_at=m.closed_at,
            closed_by_user_id=m.closed_by_user_id,
        )

    async def save(self, cap: CorrectiveActionPlan) -> CorrectiveActionPlan:
        existing = await self._session.get(CorrectiveActionPlanModel, cap.id)
        m = self._to_model(cap)
        if existing is None:
            self._session.add(m)
        else:
            for attr, val in vars(m).items():
                if not attr.startswith("_"):
                    setattr(existing, attr, val)
            m = existing
        await self._session.flush()
        return self._to_domain(m)

    async def get_by_id(self, cap_id: str, org_id: str) -> CorrectiveActionPlan | None:
        m = await self._session.get(CorrectiveActionPlanModel, cap_id)
        if m is None or m.organization_id != org_id:
            return None
        return self._to_domain(m)

    async def get_by_finding(self, finding_id: str, org_id: str) -> CorrectiveActionPlan | None:
        stmt = (
            select(CorrectiveActionPlanModel)
            .where(
                CorrectiveActionPlanModel.finding_id == finding_id,
                CorrectiveActionPlanModel.organization_id == org_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def list_for_org(
        self,
        org_id: str,
        *,
        cap_status: str | None = None,
        limit: int = 100,
    ) -> list[CorrectiveActionPlan]:
        stmt = select(CorrectiveActionPlanModel).where(
            CorrectiveActionPlanModel.organization_id == org_id
        )
        if cap_status:
            stmt = stmt.where(CorrectiveActionPlanModel.cap_status == cap_status)
        stmt = stmt.order_by(
            CorrectiveActionPlanModel.deadline.asc().nullslast(),
            CorrectiveActionPlanModel.created_at.desc(),
        ).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def kpis(self, org_id: str) -> dict:
        """Returns: open, overdue, verified, closed, total, completion_rate."""
        from datetime import date as _date

        stmt = select(
            CorrectiveActionPlanModel.cap_status,
            CorrectiveActionPlanModel.deadline,
        ).where(CorrectiveActionPlanModel.organization_id == org_id)
        rows = (await self._session.execute(stmt)).all()

        today = _date.today()
        total = len(rows)
        closed_count = sum(1 for r in rows if r.cap_status == "CLOSED")
        verified_count = sum(1 for r in rows if r.cap_status == "VERIFIED")
        open_count = sum(1 for r in rows if r.cap_status not in ("CLOSED", "VERIFIED"))
        overdue_count = sum(
            1
            for r in rows
            if r.cap_status not in ("CLOSED", "VERIFIED")
            and r.deadline is not None
            and r.deadline < today
        )
        done = closed_count + verified_count
        completion_rate = done / total if total else 0.0

        return {
            "total": total,
            "open": open_count,
            "overdue": overdue_count,
            "verified": verified_count,
            "closed": closed_count,
            "completion_rate": round(completion_rate, 4),
        }
