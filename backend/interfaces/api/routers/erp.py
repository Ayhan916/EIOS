"""ERP Integration Layer Router — M6

9 endpoints:
  GET  /erp/connectors                           — list connectors
  POST /erp/connectors                           — create connector
  GET  /erp/connectors/{id}                      — get connector
  PUT  /erp/connectors/{id}                      — update connector
  DELETE /erp/connectors/{id}                    — deactivate connector
  POST /erp/connectors/{id}/sync                 — trigger manual sync
  GET  /erp/connectors/{id}/jobs                 — list sync jobs for connector
  GET  /erp/connectors/{id}/mappings             — list field mappings
  POST /erp/connectors/{id}/mappings             — upsert field mapping
  DELETE /erp/connectors/{id}/mappings/{mid}     — delete field mapping
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.erp.connector_service import ERPConnectorService
from application.erp.sync_service import ERPSyncService
from interfaces.api.deps import get_current_user, get_db, require_analyst, scope_gate
from domain.user import User
from interfaces.api.schemas.erp import (
    ERPConnectorCreate,
    ERPConnectorListResponse,
    ERPConnectorResponse,
    ERPConnectorUpdate,
    ERPFieldMappingResponse,
    ERPFieldMappingUpsert,
    ERPSyncJobListResponse,
    ERPSyncJobResponse,
    ERPSyncTriggerRequest,
)

router = APIRouter(
    prefix="/erp",
    tags=["ERP Integration"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("erp:read", "erp:write")),
    ],
)


@router.get("/connectors", response_model=ERPConnectorListResponse)
async def list_connectors(
    adapter_type: str | None = Query(default=None),
    connector_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ERPConnectorListResponse:
    svc = ERPConnectorService(db)
    items, total = await svc.list_for_org(
        organization_id=current_user.organization_id,
        adapter_type=adapter_type,
        connector_status=connector_status,
        limit=limit,
        offset=offset,
    )
    return ERPConnectorListResponse(
        items=[ERPConnectorResponse.from_model(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/connectors",
    response_model=ERPConnectorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_connector(
    body: ERPConnectorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ERPConnectorResponse:
    svc = ERPConnectorService(db)
    model = await svc.create(
        organization_id=current_user.organization_id,
        name=body.name,
        adapter_type=body.adapter_type,
        description=body.description,
        base_url=body.base_url,
        secret_reference_id=body.secret_reference_id,
        auth_scheme=body.auth_scheme,
        schedule_cron=body.schedule_cron,
        timeout_seconds=body.timeout_seconds,
        config_json=body.config_json,
        actor_id=current_user.id,
    )
    await db.commit()
    return ERPConnectorResponse.from_model(model)


@router.get("/connectors/{connector_id}", response_model=ERPConnectorResponse)
async def get_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ERPConnectorResponse:
    svc = ERPConnectorService(db)
    model = await svc.get(current_user.organization_id, connector_id)
    if model is None:
        raise HTTPException(status_code=404, detail="ERP connector not found")
    return ERPConnectorResponse.from_model(model)


@router.put(
    "/connectors/{connector_id}",
    response_model=ERPConnectorResponse,
    dependencies=[Depends(require_analyst)],
)
async def update_connector(
    connector_id: str,
    body: ERPConnectorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ERPConnectorResponse:
    svc = ERPConnectorService(db)
    data = body.model_dump(exclude_unset=True)
    model = await svc.update(
        current_user.organization_id, connector_id, actor_id=current_user.id, **data
    )
    if model is None:
        raise HTTPException(status_code=404, detail="ERP connector not found")
    await db.commit()
    return ERPConnectorResponse.from_model(model)


@router.delete(
    "/connectors/{connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def deactivate_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = ERPConnectorService(db)
    ok = await svc.deactivate(
        current_user.organization_id, connector_id, actor_id=current_user.id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="ERP connector not found")
    await db.commit()


@router.post(
    "/connectors/{connector_id}/sync",
    response_model=ERPSyncJobResponse,
    dependencies=[Depends(require_analyst)],
)
async def trigger_sync(
    connector_id: str,
    body: ERPSyncTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ERPSyncJobResponse:
    """Trigger a manual sync. Uses CSV adapter for now (REST requires live ERP)."""
    conn_svc = ERPConnectorService(db)
    connector = await conn_svc.get(current_user.organization_id, connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail="ERP connector not found")
    if connector.connector_status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Connector is not ACTIVE")

    # Build adapter based on connector type
    if connector.adapter_type == "CSV":
        from application.erp.adapters.csv_adapter import CsvERPAdapter
        adapter = CsvERPAdapter(
            materials_csv=body.materials_csv or "",
            bom_csv=body.bom_csv or "",
        )
    else:
        from application.erp.adapters.rest import RestERPAdapter
        adapter = RestERPAdapter(
            base_url=connector.base_url or "http://localhost",
            timeout_seconds=connector.timeout_seconds,
        )

    sync_svc = ERPSyncService(db)

    if body.direction == "OUTBOUND":
        job = await sync_svc.run_outbound_sync(
            organization_id=current_user.organization_id,
            connector_id=connector_id,
            adapter=adapter,
            actor_id=current_user.id,
        )
    else:
        job = await sync_svc.run_inbound_sync(
            organization_id=current_user.organization_id,
            connector_id=connector_id,
            adapter=adapter,
            entity_type=body.entity_type,
            actor_id=current_user.id,
        )

    return ERPSyncJobResponse.from_model(job)


@router.get("/connectors/{connector_id}/jobs", response_model=ERPSyncJobListResponse)
async def list_sync_jobs(
    connector_id: str,
    job_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ERPSyncJobListResponse:
    svc = ERPSyncService(db)
    items, total = await svc.list_jobs(
        organization_id=current_user.organization_id,
        connector_id=connector_id,
        job_status=job_status,
        limit=limit,
        offset=offset,
    )
    return ERPSyncJobListResponse(
        items=[ERPSyncJobResponse.from_model(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/connectors/{connector_id}/mappings", response_model=list[ERPFieldMappingResponse])
async def list_field_mappings(
    connector_id: str,
    entity_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ERPFieldMappingResponse]:
    svc = ERPConnectorService(db)
    items = await svc.list_field_mappings(
        current_user.organization_id, connector_id, entity_type
    )
    return [ERPFieldMappingResponse.from_model(m) for m in items]


@router.post(
    "/connectors/{connector_id}/mappings",
    response_model=ERPFieldMappingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def upsert_field_mapping(
    connector_id: str,
    body: ERPFieldMappingUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ERPFieldMappingResponse:
    svc = ERPConnectorService(db)
    model = await svc.upsert_field_mapping(
        organization_id=current_user.organization_id,
        connector_id=connector_id,
        entity_type=body.entity_type,
        erp_field=body.erp_field,
        eios_field=body.eios_field,
        transform_fn=body.transform_fn,
        is_required=body.is_required,
        default_value=body.default_value,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return ERPFieldMappingResponse.from_model(model)


@router.delete(
    "/connectors/{connector_id}/mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def delete_field_mapping(
    connector_id: str,
    mapping_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = ERPConnectorService(db)
    ok = await svc.delete_field_mapping(current_user.organization_id, mapping_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Field mapping not found")
    await db.commit()
