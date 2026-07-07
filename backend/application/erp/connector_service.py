"""ERP Connector Service — M6

CRUD for ERPConnectorModel and ERPFieldMappingModel.
Session ownership: caller (router) commits; service only flushes.
organization_id is a MANDATORY filter on every DB query.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.erp import (
    ERPConnectorModel,
    ERPFieldMappingModel,
)

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> str:
    return str(uuid4())


class ERPConnectorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        organization_id: str,
        name: str,
        adapter_type: str,
        *,
        description: str | None = None,
        base_url: str | None = None,
        secret_reference_id: str | None = None,
        auth_scheme: str = "NONE",
        schedule_cron: str | None = None,
        timeout_seconds: int = 30,
        config_json: str | None = None,
        actor_id: str | None = None,
    ) -> ERPConnectorModel:
        now = _now()
        model = ERPConnectorModel(
            id=_uid(),
            organization_id=organization_id,
            name=name,
            description=description,
            adapter_type=adapter_type,
            base_url=base_url,
            secret_reference_id=secret_reference_id,
            auth_scheme=auth_scheme,
            connector_status="ACTIVE",
            schedule_cron=schedule_cron,
            timeout_seconds=timeout_seconds,
            config_json=config_json,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get(self, organization_id: str, connector_id: str) -> ERPConnectorModel | None:
        model = await self._session.get(ERPConnectorModel, connector_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    async def list_for_org(
        self,
        organization_id: str,
        adapter_type: str | None = None,
        connector_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ERPConnectorModel], int]:
        stmt = select(ERPConnectorModel).where(
            ERPConnectorModel.organization_id == organization_id,
        )
        if adapter_type:
            stmt = stmt.where(ERPConnectorModel.adapter_type == adapter_type)
        if connector_status:
            stmt = stmt.where(ERPConnectorModel.connector_status == connector_status)

        count_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()
        stmt = stmt.order_by(ERPConnectorModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def update(
        self,
        organization_id: str,
        connector_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        base_url: str | None = None,
        secret_reference_id: str | None = None,
        auth_scheme: str | None = None,
        connector_status: str | None = None,
        schedule_cron: str | None = None,
        timeout_seconds: int | None = None,
        config_json: str | None = None,
        actor_id: str | None = None,
    ) -> ERPConnectorModel | None:
        model = await self.get(organization_id, connector_id)
        if model is None:
            return None
        if name is not None:
            model.name = name
        if description is not None:
            model.description = description
        if base_url is not None:
            model.base_url = base_url
        if secret_reference_id is not None:
            model.secret_reference_id = secret_reference_id
        if auth_scheme is not None:
            model.auth_scheme = auth_scheme
        if connector_status is not None:
            model.connector_status = connector_status
        if schedule_cron is not None:
            model.schedule_cron = schedule_cron
        if timeout_seconds is not None:
            model.timeout_seconds = timeout_seconds
        if config_json is not None:
            model.config_json = config_json
        model.updated_by = actor_id
        model.updated_at = _now()
        await self._session.flush()
        return model

    async def deactivate(
        self, organization_id: str, connector_id: str, actor_id: str | None = None
    ) -> bool:
        model = await self.get(organization_id, connector_id)
        if model is None:
            return False
        model.connector_status = "INACTIVE"
        model.updated_by = actor_id
        model.updated_at = _now()
        await self._session.flush()
        return True

    # ── Field Mappings ─────────────────────────────────────────────────────────

    async def upsert_field_mapping(
        self,
        organization_id: str,
        connector_id: str,
        entity_type: str,
        erp_field: str,
        eios_field: str,
        *,
        transform_fn: str | None = None,
        is_required: bool = False,
        default_value: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> ERPFieldMappingModel:
        stmt = select(ERPFieldMappingModel).where(
            ERPFieldMappingModel.organization_id == organization_id,
            ERPFieldMappingModel.connector_id == connector_id,
            ERPFieldMappingModel.entity_type == entity_type,
            ERPFieldMappingModel.erp_field == erp_field,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        now = _now()

        if existing:
            existing.eios_field = eios_field
            existing.transform_fn = transform_fn
            existing.is_required = str(is_required)
            existing.default_value = default_value
            existing.notes = notes
            existing.updated_at = now
            await self._session.flush()
            return existing

        mapping = ERPFieldMappingModel(
            id=_uid(),
            organization_id=organization_id,
            connector_id=connector_id,
            entity_type=entity_type,
            erp_field=erp_field,
            eios_field=eios_field,
            transform_fn=transform_fn,
            is_required=str(is_required),
            default_value=default_value,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._session.add(mapping)
        await self._session.flush()
        return mapping

    async def list_field_mappings(
        self, organization_id: str, connector_id: str, entity_type: str | None = None
    ) -> list[ERPFieldMappingModel]:
        stmt = select(ERPFieldMappingModel).where(
            ERPFieldMappingModel.organization_id == organization_id,
            ERPFieldMappingModel.connector_id == connector_id,
        )
        if entity_type:
            stmt = stmt.where(ERPFieldMappingModel.entity_type == entity_type)
        stmt = stmt.order_by(ERPFieldMappingModel.entity_type, ERPFieldMappingModel.erp_field)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_field_mapping(self, organization_id: str, mapping_id: str) -> bool:
        model = await self._session.get(ERPFieldMappingModel, mapping_id)
        if model is None or model.organization_id != organization_id:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True
