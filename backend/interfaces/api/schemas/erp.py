"""API Schemas — ERP Integration Layer (M6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ERPConnectorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    adapter_type: str = Field(..., description="SAP_ODATA | ORACLE_REST | REST | CSV")
    description: str | None = None
    base_url: str | None = None
    secret_reference_id: str | None = None
    auth_scheme: str = Field(default="NONE", description="BASIC | BEARER | OAUTH2 | NONE")
    schedule_cron: str | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    config_json: str | None = None


class ERPConnectorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    base_url: str | None = None
    secret_reference_id: str | None = None
    auth_scheme: str | None = None
    connector_status: str | None = None
    schedule_cron: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    config_json: str | None = None


class ERPConnectorResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None
    adapter_type: str
    base_url: str | None
    secret_reference_id: str | None
    auth_scheme: str
    connector_status: str
    schedule_cron: str | None
    last_sync_at: datetime | None
    last_sync_status: str | None
    timeout_seconds: int
    config_json: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, m: Any) -> "ERPConnectorResponse":
        return cls(
            id=m.id,
            organization_id=m.organization_id,
            name=m.name,
            description=m.description,
            adapter_type=m.adapter_type,
            base_url=m.base_url,
            secret_reference_id=m.secret_reference_id,
            auth_scheme=m.auth_scheme,
            connector_status=m.connector_status,
            schedule_cron=m.schedule_cron,
            last_sync_at=m.last_sync_at,
            last_sync_status=m.last_sync_status,
            timeout_seconds=m.timeout_seconds,
            config_json=m.config_json,
            created_by=m.created_by,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


class ERPConnectorListResponse(BaseModel):
    items: list[ERPConnectorResponse]
    total: int
    limit: int
    offset: int


class ERPSyncJobResponse(BaseModel):
    id: str
    organization_id: str
    connector_id: str
    direction: str
    entity_type: str
    job_status: str
    trigger_source: str
    records_fetched: int
    records_created: int
    records_updated: int
    records_failed: int
    error_message: str | None
    error_details_json: str | None
    started_at: datetime | None
    completed_at: datetime | None
    runtime_seconds: str | None
    initiated_by: str | None
    created_at: datetime

    @classmethod
    def from_model(cls, m: Any) -> "ERPSyncJobResponse":
        return cls(
            id=m.id,
            organization_id=m.organization_id,
            connector_id=m.connector_id,
            direction=m.direction,
            entity_type=m.entity_type,
            job_status=m.job_status,
            trigger_source=m.trigger_source,
            records_fetched=m.records_fetched,
            records_created=m.records_created,
            records_updated=m.records_updated,
            records_failed=m.records_failed,
            error_message=m.error_message,
            error_details_json=m.error_details_json,
            started_at=m.started_at,
            completed_at=m.completed_at,
            runtime_seconds=m.runtime_seconds,
            initiated_by=m.initiated_by,
            created_at=m.created_at,
        )


class ERPSyncJobListResponse(BaseModel):
    items: list[ERPSyncJobResponse]
    total: int
    limit: int
    offset: int


class ERPFieldMappingUpsert(BaseModel):
    entity_type: str = Field(..., description="Material | Product | BOM | DPP")
    erp_field: str = Field(..., min_length=1, max_length=300)
    eios_field: str = Field(..., min_length=1, max_length=300)
    transform_fn: str | None = Field(default=None, description="trim | uppercase | lowercase | date_iso | float_parse | skip")
    is_required: bool = False
    default_value: str | None = None
    notes: str | None = None


class ERPFieldMappingResponse(BaseModel):
    id: str
    organization_id: str
    connector_id: str
    entity_type: str
    erp_field: str
    eios_field: str
    transform_fn: str | None
    is_required: str
    default_value: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, m: Any) -> "ERPFieldMappingResponse":
        return cls(
            id=m.id,
            organization_id=m.organization_id,
            connector_id=m.connector_id,
            entity_type=m.entity_type,
            erp_field=m.erp_field,
            eios_field=m.eios_field,
            transform_fn=m.transform_fn,
            is_required=m.is_required,
            default_value=m.default_value,
            notes=m.notes,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


class ERPSyncTriggerRequest(BaseModel):
    direction: str = Field(default="INBOUND", description="INBOUND | OUTBOUND")
    entity_type: str = Field(default="Material", description="Material | BOM | DPP")
    # For CSV adapter: inline CSV content
    materials_csv: str | None = None
    bom_csv: str | None = None
