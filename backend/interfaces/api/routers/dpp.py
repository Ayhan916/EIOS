"""Digital Product Passport Router — M28 / KAN-94

8 endpoints:
  GET  /dpp                              — list DPPs for org
  POST /dpp                              — create DPP (draft)
  GET  /dpp/{id}                         — get by internal id
  PUT  /dpp/{id}                         — update fields
  POST /dpp/{id}/refresh                 — refresh snapshot from twins
  POST /dpp/{id}/publish                 — publish (ACTIVE + disclosed_at)
  DELETE /dpp/{id}                       — withdraw
  GET  /dpp/passport/{uid}              — public lookup by passport UID

  Plus on product router: GET /products/{id}/dpp  (registered in product.py)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dpp.service import DPPService
from domain.dpp import DPPFormat, DPPStatus
from domain.user import User
from infrastructure.kafka.producer import KafkaEventProducer, get_kafka_producer
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_analyst,
    scope_gate,
)
from interfaces.api.schemas.dpp import (
    DPPCreate,
    DPPListResponse,
    DPPResponse,
    DPPUpdate,
)

router = APIRouter(
    prefix="/dpp",
    tags=["Digital Product Passport"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("products:read", "products:write")),
    ],
)


@router.get("", response_model=DPPListResponse)
async def list_dpps(
    dpp_status: DPPStatus | None = Query(default=None),
    format: DPPFormat | None = Query(default=None),
    product_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> DPPListResponse:
    svc = DPPService(db, kafka)
    items, total = await svc.list_for_org(
        organization_id=current_user.organization_id,
        dpp_status=dpp_status,
        format=format,
        product_id=product_id,
        limit=limit,
        offset=offset,
    )
    return DPPListResponse(
        items=[DPPResponse.from_model(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=DPPResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_dpp(
    body: DPPCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> DPPResponse:
    svc = DPPService(db, kafka)
    model = await svc.create(
        organization_id=current_user.organization_id,
        product_id=body.product_id,
        format=body.format,
        product_category=body.product_category,
        battery_chemistry=body.battery_chemistry,
        capacity_wh=body.capacity_wh,
        nominal_voltage_v=body.nominal_voltage_v,
        declared_capacity_cycles=body.declared_capacity_cycles,
        carbon_footprint_kg_co2e=body.carbon_footprint_kg_co2e,
        carbon_footprint_source=body.carbon_footprint_source,
        recycled_content_pct=body.recycled_content_pct,
        renewable_content_pct=body.renewable_content_pct,
        manufacturer_name=body.manufacturer_name,
        manufacturer_country=body.manufacturer_country,
        manufacturing_date=body.manufacturing_date,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        evidence_id=body.evidence_id,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return DPPResponse.from_model(model)


@router.get("/passport/{passport_uid}", response_model=DPPResponse)
async def get_dpp_by_uid(
    passport_uid: str,
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> DPPResponse:
    """Public endpoint — no auth required; only returns disclosed DPPs."""
    svc = DPPService(db, kafka)
    model = await svc.get_by_uid(passport_uid)
    if model is None:
        raise HTTPException(status_code=404, detail="Digital Product Passport not found")
    return DPPResponse.from_model(model)


@router.get("/{dpp_id}", response_model=DPPResponse)
async def get_dpp(
    dpp_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> DPPResponse:
    svc = DPPService(db, kafka)
    model = await svc.get(current_user.organization_id, dpp_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Digital Product Passport not found")
    return DPPResponse.from_model(model)


@router.put(
    "/{dpp_id}",
    response_model=DPPResponse,
    dependencies=[Depends(require_analyst)],
)
async def update_dpp(
    dpp_id: str,
    body: DPPUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> DPPResponse:
    svc = DPPService(db, kafka)
    data = body.model_dump(exclude_unset=True)
    model = await svc.update(current_user.organization_id, dpp_id, actor_id=current_user.id, **data)
    if model is None:
        raise HTTPException(status_code=404, detail="Digital Product Passport not found")
    await db.commit()
    return DPPResponse.from_model(model)


@router.post(
    "/{dpp_id}/refresh",
    response_model=DPPResponse,
    dependencies=[Depends(require_analyst)],
)
async def refresh_snapshot(
    dpp_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> DPPResponse:
    """Recompute substances_of_concern_count, non_compliant_regulations_count,
    and auto-fill PCF from material LCA data."""
    svc = DPPService(db, kafka)
    model = await svc.refresh_snapshot(
        current_user.organization_id, dpp_id, actor_id=current_user.id
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Digital Product Passport not found")
    await db.commit()
    return DPPResponse.from_model(model)


@router.post(
    "/{dpp_id}/publish",
    response_model=DPPResponse,
    dependencies=[Depends(require_analyst)],
)
async def publish_dpp(
    dpp_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> DPPResponse:
    """Refresh snapshot, set status=ACTIVE, stamp disclosed_at."""
    svc = DPPService(db, kafka)
    model = await svc.publish(current_user.organization_id, dpp_id, actor_id=current_user.id)
    if model is None:
        raise HTTPException(status_code=404, detail="Digital Product Passport not found")
    await db.commit()
    return DPPResponse.from_model(model)


@router.delete(
    "/{dpp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def withdraw_dpp(
    dpp_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = DPPService(db, kafka)
    withdrawn = await svc.withdraw(current_user.organization_id, dpp_id, actor_id=current_user.id)
    if not withdrawn:
        raise HTTPException(status_code=404, detail="Digital Product Passport not found")
    await db.commit()
