"""Repositories for CSDDD-002 DD-Governance (Art. 7)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.dd_policy import CoCAcceptance, CodeOfConduct, DDPolicy
from domain.enums import DDPolicyStatus
from infrastructure.persistence.models.dd_policy import (
    CoCAcceptanceModel,
    CodeOfConductModel,
    DDPolicyModel,
)
from infrastructure.persistence.repositories.base import BaseRepository


class SQLDDPolicyRepository(BaseRepository[DDPolicy, DDPolicyModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DDPolicyModel)

    def _to_model(self, e: DDPolicy) -> DDPolicyModel:
        now = datetime.now(UTC)
        return DDPolicyModel(
            id=e.id,
            organization_id=e.organization_id,
            title=e.title,
            policy_status=e.policy_status.value
            if hasattr(e.policy_status, "value")
            else e.policy_status,
            content_text=e.content_text,
            file_url=e.file_url,
            approved_by=e.approved_by,
            approved_role=e.approved_role,
            valid_from=e.valid_from,
            published_at=e.published_at,
            next_review_due=e.next_review_due,
            is_public=e.is_public,
            public_token=e.public_token,
            policy_version=e.policy_version,
            parent_policy_id=e.parent_policy_id,
            status=e.status.value if hasattr(e.status, "value") else e.status,
            version=e.version,
            owner=e.owner,
            created_by=e.created_by,
            updated_by=e.updated_by,
            created_at=e.created_at or now,
            updated_at=e.updated_at or now,
        )

    def _to_domain(self, m: DDPolicyModel) -> DDPolicy:
        return DDPolicy(
            id=m.id,
            organization_id=m.organization_id,
            title=m.title,
            policy_status=DDPolicyStatus(m.policy_status),
            content_text=m.content_text,
            file_url=m.file_url,
            approved_by=m.approved_by,
            approved_role=m.approved_role,
            valid_from=m.valid_from,
            published_at=m.published_at,
            next_review_due=m.next_review_due,
            is_public=m.is_public,
            public_token=m.public_token,
            policy_version=m.policy_version,
            parent_policy_id=m.parent_policy_id,
            status=m.status,
            version=m.version,
            owner=m.owner,
            created_by=m.created_by,
            updated_by=m.updated_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def list_by_org(self, organization_id: str) -> list[DDPolicy]:
        stmt = (
            select(DDPolicyModel)
            .where(DDPolicyModel.organization_id == organization_id)
            .order_by(DDPolicyModel.policy_version.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_active(self, organization_id: str) -> DDPolicy | None:
        stmt = (
            select(DDPolicyModel)
            .where(
                DDPolicyModel.organization_id == organization_id,
                DDPolicyModel.policy_status == "active",
            )
            .order_by(DDPolicyModel.policy_version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def get_by_public_token(self, token: str) -> DDPolicy | None:
        stmt = select(DDPolicyModel).where(
            DDPolicyModel.public_token == token,
            DDPolicyModel.is_public == True,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_domain(m) if m else None


class SQLCodeOfConductRepository(BaseRepository[CodeOfConduct, CodeOfConductModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CodeOfConductModel)

    def _to_model(self, e: CodeOfConduct) -> CodeOfConductModel:
        now = datetime.now(UTC)
        return CodeOfConductModel(
            id=e.id,
            organization_id=e.organization_id,
            title=e.title,
            content_text=e.content_text,
            file_url=e.file_url,
            coc_version=e.coc_version,
            valid_from=e.valid_from,
            acceptance_validity_months=e.acceptance_validity_months,
            is_active=e.is_active,
            linked_policy_id=e.linked_policy_id,
            status=e.status.value if hasattr(e.status, "value") else e.status,
            version=e.version,
            owner=e.owner,
            created_by=e.created_by,
            updated_by=e.updated_by,
            created_at=e.created_at or now,
            updated_at=e.updated_at or now,
        )

    def _to_domain(self, m: CodeOfConductModel) -> CodeOfConduct:
        return CodeOfConduct(
            id=m.id,
            organization_id=m.organization_id,
            title=m.title,
            content_text=m.content_text,
            file_url=m.file_url,
            coc_version=m.coc_version,
            valid_from=m.valid_from,
            acceptance_validity_months=m.acceptance_validity_months,
            is_active=m.is_active,
            linked_policy_id=m.linked_policy_id,
            status=m.status,
            version=m.version,
            owner=m.owner,
            created_by=m.created_by,
            updated_by=m.updated_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def get_active(self, organization_id: str) -> CodeOfConduct | None:
        stmt = (
            select(CodeOfConductModel)
            .where(
                CodeOfConductModel.organization_id == organization_id,
                CodeOfConductModel.is_active == True,  # noqa: E712
            )
            .order_by(CodeOfConductModel.coc_version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_domain(m) if m else None

    async def list_by_org(self, organization_id: str) -> list[CodeOfConduct]:
        stmt = (
            select(CodeOfConductModel)
            .where(CodeOfConductModel.organization_id == organization_id)
            .order_by(CodeOfConductModel.coc_version.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]


class SQLCoCAcceptanceRepository(BaseRepository[CoCAcceptance, CoCAcceptanceModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CoCAcceptanceModel)

    def _to_model(self, e: CoCAcceptance) -> CoCAcceptanceModel:
        now = datetime.now(UTC)
        return CoCAcceptanceModel(
            id=e.id,
            organization_id=e.organization_id,
            coc_id=e.coc_id,
            supplier_id=e.supplier_id,
            coc_version=e.coc_version,
            accepted_at=e.accepted_at,
            accepted_by_name=e.accepted_by_name,
            ip_hash=e.ip_hash,
            expires_at=e.expires_at,
            status=e.status.value if hasattr(e.status, "value") else e.status,
            version=e.version,
            owner=e.owner,
            created_by=e.created_by,
            updated_by=e.updated_by,
            created_at=e.created_at or now,
            updated_at=e.updated_at or now,
        )

    def _to_domain(self, m: CoCAcceptanceModel) -> CoCAcceptance:
        return CoCAcceptance(
            id=m.id,
            organization_id=m.organization_id,
            coc_id=m.coc_id,
            supplier_id=m.supplier_id,
            coc_version=m.coc_version,
            accepted_at=m.accepted_at,
            accepted_by_name=m.accepted_by_name,
            ip_hash=m.ip_hash,
            expires_at=m.expires_at,
            status=m.status,
            version=m.version,
            owner=m.owner,
            created_by=m.created_by,
            updated_by=m.updated_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def list_by_coc(self, coc_id: str, organization_id: str) -> list[CoCAcceptance]:
        stmt = (
            select(CoCAcceptanceModel)
            .where(
                CoCAcceptanceModel.coc_id == coc_id,
                CoCAcceptanceModel.organization_id == organization_id,
            )
            .order_by(CoCAcceptanceModel.accepted_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_for_supplier(self, supplier_id: str, coc_id: str) -> CoCAcceptance | None:
        stmt = (
            select(CoCAcceptanceModel)
            .where(
                CoCAcceptanceModel.supplier_id == supplier_id,
                CoCAcceptanceModel.coc_id == coc_id,
            )
            .order_by(CoCAcceptanceModel.accepted_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_domain(m) if m else None
