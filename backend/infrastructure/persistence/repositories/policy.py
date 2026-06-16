from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.policy import Policy
from infrastructure.persistence.models.policy import PolicyModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLPolicyRepository(BaseRepository[Policy, PolicyModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PolicyModel)

    def _to_model(self, entity: Policy) -> PolicyModel:
        return PolicyModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            title=entity.title,
            description=entity.description,
            policy_type=entity.policy_type,
            effective_date=entity.effective_date,
            expiry_date=entity.expiry_date,
            approved_by=entity.approved_by,
        )

    def _to_domain(self, model: PolicyModel) -> Policy:
        return Policy(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            title=model.title,
            description=model.description,
            policy_type=model.policy_type,
            effective_date=model.effective_date,
            expiry_date=model.expiry_date,
            approved_by=model.approved_by,
        )
