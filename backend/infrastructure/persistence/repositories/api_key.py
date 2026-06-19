from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.api_key import ApiKey
from domain.enums import EntityStatus
from infrastructure.persistence.models.api_key import ApiKeyModel
from infrastructure.persistence.repositories.base import BaseRepository


class SQLApiKeyRepository(BaseRepository[ApiKey, ApiKeyModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ApiKeyModel)

    def _to_model(self, entity: ApiKey) -> ApiKeyModel:
        return ApiKeyModel(
            id=entity.id,
            status=entity.status.value,
            version=entity.version,
            owner=entity.owner,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            organization_id=entity.organization_id,
            service_account_id=entity.service_account_id,
            name=entity.name,
            description=entity.description,
            key_hash=entity.key_hash,
            key_prefix=entity.key_prefix,
            scopes=entity.scopes,
            is_active=entity.is_active,
            last_used_at=entity.last_used_at,
            requests_total=entity.requests_total,
            requests_this_minute=entity.requests_this_minute,
            minute_window_start=entity.minute_window_start,
            requests_this_hour=entity.requests_this_hour,
            hour_window_start=entity.hour_window_start,
            rate_limit_per_minute=entity.rate_limit_per_minute,
            rate_limit_per_hour=entity.rate_limit_per_hour,
            revoked_at=entity.revoked_at,
            revoked_by=entity.revoked_by,
        )

    def _to_domain(self, model: ApiKeyModel) -> ApiKey:
        return ApiKey(
            id=model.id,
            status=EntityStatus(model.status),
            version=model.version,
            owner=model.owner,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            organization_id=model.organization_id,
            service_account_id=model.service_account_id,
            name=model.name,
            description=model.description,
            key_hash=model.key_hash,
            key_prefix=model.key_prefix,
            scopes=list(model.scopes or []),
            is_active=model.is_active,
            last_used_at=model.last_used_at,
            requests_total=model.requests_total,
            requests_this_minute=model.requests_this_minute,
            minute_window_start=model.minute_window_start,
            requests_this_hour=model.requests_this_hour,
            hour_window_start=model.hour_window_start,
            rate_limit_per_minute=model.rate_limit_per_minute,
            rate_limit_per_hour=model.rate_limit_per_hour,
            revoked_at=model.revoked_at,
            revoked_by=model.revoked_by,
        )

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        row = (
            await self._session.execute(
                select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
            )
        ).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_for_org(self, organization_id: str) -> list[ApiKey]:
        rows = (
            await self._session.execute(
                select(ApiKeyModel)
                .where(ApiKeyModel.organization_id == organization_id)
                .order_by(ApiKeyModel.created_at.desc())
            )
        ).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def increment_usage(
        self,
        key_id: str,
        now: datetime,
        minute_window_start: datetime,
        hour_window_start: datetime,
    ) -> None:
        """Atomically update usage counters for rate limiting."""
        await self._session.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(
                last_used_at=now,
                requests_total=ApiKeyModel.requests_total + 1,
                requests_this_minute=ApiKeyModel.requests_this_minute + 1,
                minute_window_start=minute_window_start,
                requests_this_hour=ApiKeyModel.requests_this_hour + 1,
                hour_window_start=hour_window_start,
            )
        )

    async def reset_minute_window(self, key_id: str, now: datetime) -> None:
        await self._session.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(requests_this_minute=1, minute_window_start=now)
        )

    async def reset_hour_window(self, key_id: str, now: datetime) -> None:
        await self._session.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(requests_this_hour=1, hour_window_start=now)
        )

    async def atomic_increment_and_get_counts(
        self, key_id: str, now: datetime
    ) -> tuple[int, int]:
        """Atomically increment usage counters (resetting expired windows) and return
        (new_minute_count, new_hour_count).

        Single UPDATE with window-reset logic expressed in SQL, so concurrent requests
        cannot observe the same pre-increment count.

        Limitations: window reset and increment are atomic per row; extremely high
        concurrency (>100 req/s on one key) may still occasionally under-count due to
        PostgreSQL's MVCC snapshot isolation. Use Redis for true atomicity at scale.
        """
        min_cutoff = now - timedelta(seconds=60)
        hr_cutoff = now - timedelta(hours=1)

        new_min = case(
            (
                (ApiKeyModel.minute_window_start.is_(None))
                | (ApiKeyModel.minute_window_start < min_cutoff),
                1,
            ),
            else_=ApiKeyModel.requests_this_minute + 1,
        )
        new_hr = case(
            (
                (ApiKeyModel.hour_window_start.is_(None))
                | (ApiKeyModel.hour_window_start < hr_cutoff),
                1,
            ),
            else_=ApiKeyModel.requests_this_hour + 1,
        )
        new_min_start = case(
            (
                (ApiKeyModel.minute_window_start.is_(None))
                | (ApiKeyModel.minute_window_start < min_cutoff),
                now,
            ),
            else_=ApiKeyModel.minute_window_start,
        )
        new_hr_start = case(
            (
                (ApiKeyModel.hour_window_start.is_(None))
                | (ApiKeyModel.hour_window_start < hr_cutoff),
                now,
            ),
            else_=ApiKeyModel.hour_window_start,
        )

        result = await self._session.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(
                last_used_at=now,
                requests_total=ApiKeyModel.requests_total + 1,
                requests_this_minute=new_min,
                minute_window_start=new_min_start,
                requests_this_hour=new_hr,
                hour_window_start=new_hr_start,
            )
            .returning(
                ApiKeyModel.requests_this_minute,
                ApiKeyModel.requests_this_hour,
            )
        )
        row = result.one()
        return int(row.requests_this_minute), int(row.requests_this_hour)
