"""Repositories for CSDDD-001 Stakeholder Engagement (Art. 13)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import ConsultationBarrier, ConsultationFormat, StakeholderType
from domain.stakeholder import Stakeholder, StakeholderConsultation, StakeholderFeedback
from infrastructure.persistence.models.stakeholder import (
    StakeholderConsultationModel,
    StakeholderFeedbackModel,
    StakeholderModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


def _loads(value: str | None) -> list:
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []


def _dumps(value: list) -> str:
    return json.dumps(value)


class SQLStakeholderRepository(BaseRepository[Stakeholder, StakeholderModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StakeholderModel)

    def _to_model(self, e: Stakeholder) -> StakeholderModel:
        now = datetime.now(UTC)
        return StakeholderModel(
            id=e.id,
            organization_id=e.organization_id,
            name=e.name,
            stakeholder_type=e.stakeholder_type.value if hasattr(e.stakeholder_type, "value") else e.stakeholder_type,
            contact_email=e.contact_email,
            language=e.language,
            activity_chain_ids=_dumps(e.activity_chain_ids),
            regions=_dumps(e.regions),
            risk_topics=_dumps(e.risk_topics),
            justification=e.justification,
            status=e.status.value if hasattr(e.status, "value") else e.status,
            version=e.version,
            owner=e.owner,
            created_by=e.created_by,
            updated_by=e.updated_by,
            created_at=e.created_at or now,
            updated_at=e.updated_at or now,
        )

    def _to_domain(self, m: StakeholderModel) -> Stakeholder:
        return Stakeholder(
            id=m.id,
            organization_id=m.organization_id,
            name=m.name,
            stakeholder_type=StakeholderType(m.stakeholder_type),
            contact_email=m.contact_email,
            language=m.language,
            activity_chain_ids=_loads(m.activity_chain_ids),
            regions=_loads(m.regions),
            risk_topics=_loads(m.risk_topics),
            justification=m.justification,
            status=m.status,
            version=m.version,
            owner=m.owner,
            created_by=m.created_by,
            updated_by=m.updated_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def list_by_org(
        self,
        organization_id: str,
        *,
        stakeholder_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Stakeholder]:
        stmt = select(StakeholderModel).where(StakeholderModel.organization_id == organization_id)
        if stakeholder_type:
            stmt = stmt.where(StakeholderModel.stakeholder_type == stakeholder_type)
        stmt = stmt.order_by(StakeholderModel.name.asc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def count_by_org(self, organization_id: str) -> int:
        stmt = select(func.count()).where(StakeholderModel.organization_id == organization_id)
        return (await self._session.execute(stmt)).scalar_one()


class SQLStakeholderConsultationRepository(
    BaseRepository[StakeholderConsultation, StakeholderConsultationModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StakeholderConsultationModel)

    def _to_model(self, e: StakeholderConsultation) -> StakeholderConsultationModel:
        now = datetime.now(UTC)
        return StakeholderConsultationModel(
            id=e.id,
            organization_id=e.organization_id,
            stakeholder_ids=_dumps(e.stakeholder_ids),
            consultation_date=e.consultation_date,
            format=e.format.value if hasattr(e.format, "value") else e.format,
            topics=_dumps(e.topics),
            description=e.description,
            outcomes=e.outcomes,
            barrier=e.barrier.value if hasattr(e.barrier, "value") else e.barrier,
            barrier_notes=e.barrier_notes,
            linked_risk_id=e.linked_risk_id,
            linked_finding_id=e.linked_finding_id,
            linked_cap_id=e.linked_cap_id,
            status=e.status.value if hasattr(e.status, "value") else e.status,
            version=e.version,
            owner=e.owner,
            created_by=e.created_by,
            updated_by=e.updated_by,
            created_at=e.created_at or now,
            updated_at=e.updated_at or now,
        )

    def _to_domain(self, m: StakeholderConsultationModel) -> StakeholderConsultation:
        return StakeholderConsultation(
            id=m.id,
            organization_id=m.organization_id,
            stakeholder_ids=_loads(m.stakeholder_ids),
            consultation_date=m.consultation_date,
            format=ConsultationFormat(m.format),
            topics=_loads(m.topics),
            description=m.description,
            outcomes=m.outcomes,
            barrier=ConsultationBarrier(m.barrier),
            barrier_notes=m.barrier_notes,
            linked_risk_id=m.linked_risk_id,
            linked_finding_id=m.linked_finding_id,
            linked_cap_id=m.linked_cap_id,
            status=m.status,
            version=m.version,
            owner=m.owner,
            created_by=m.created_by,
            updated_by=m.updated_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def list_by_org(
        self,
        organization_id: str,
        *,
        stakeholder_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StakeholderConsultation]:
        stmt = select(StakeholderConsultationModel).where(
            StakeholderConsultationModel.organization_id == organization_id
        )
        if stakeholder_id:
            stmt = stmt.where(
                StakeholderConsultationModel.stakeholder_ids.contains(stakeholder_id)
            )
        stmt = stmt.order_by(StakeholderConsultationModel.consultation_date.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def count_by_org(self, organization_id: str) -> int:
        stmt = select(func.count()).where(
            StakeholderConsultationModel.organization_id == organization_id
        )
        return (await self._session.execute(stmt)).scalar_one()


class SQLStakeholderFeedbackRepository(
    BaseRepository[StakeholderFeedback, StakeholderFeedbackModel]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StakeholderFeedbackModel)

    def _to_model(self, e: StakeholderFeedback) -> StakeholderFeedbackModel:
        now = datetime.now(UTC)
        return StakeholderFeedbackModel(
            id=e.id,
            consultation_id=e.consultation_id,
            organization_id=e.organization_id,
            risk_assessment=e.risk_assessment,
            affected_rights=_dumps(e.affected_rights),
            description=e.description,
            wants_contact=e.wants_contact,
            submitted_by_email=e.submitted_by_email,
            submitted_by_name=e.submitted_by_name,
            submitter_ip=e.submitter_ip,
            status=e.status.value if hasattr(e.status, "value") else e.status,
            version=e.version,
            owner=e.owner,
            created_by=e.created_by,
            updated_by=e.updated_by,
            created_at=e.created_at or now,
            updated_at=e.updated_at or now,
        )

    def _to_domain(self, m: StakeholderFeedbackModel) -> StakeholderFeedback:
        return StakeholderFeedback(
            id=m.id,
            consultation_id=m.consultation_id,
            organization_id=m.organization_id,
            risk_assessment=m.risk_assessment,
            affected_rights=_loads(m.affected_rights),
            description=m.description,
            wants_contact=m.wants_contact,
            submitted_by_email=m.submitted_by_email,
            submitted_by_name=m.submitted_by_name,
            submitter_ip=m.submitter_ip,
            status=m.status,
            version=m.version,
            owner=m.owner,
            created_by=m.created_by,
            updated_by=m.updated_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def list_by_consultation(self, consultation_id: str) -> list[StakeholderFeedback]:
        stmt = (
            select(StakeholderFeedbackModel)
            .where(StakeholderFeedbackModel.consultation_id == consultation_id)
            .order_by(StakeholderFeedbackModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]
