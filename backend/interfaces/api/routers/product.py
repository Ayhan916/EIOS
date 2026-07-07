"""Product Twin Router — M27 / KAN-101

10 endpoints across 3 sub-resources:
  /products                      — list, create
  /products/{id}                 — get, update, delete (archive)
  /products/{id}/bom             — list, add
  /products/{id}/bom/{item_id}   — delete
  /products/{id}/compliance      — aggregated from BOM materials
  /products/{id}/sustainability  — aggregated PCF from BOM materials
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dpp.service import DPPService
from application.product.service import ProductBOMService, ProductService
from domain.product import ProductStatus, ProductType
from domain.user import User
from infrastructure.kafka.producer import KafkaEventProducer, get_kafka_producer
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_analyst,
    scope_gate,
)
from interfaces.api.schemas.dpp import DPPResponse
from interfaces.api.schemas.product import (
    ProductBOMItemCreate,
    ProductBOMItemResponse,
    ProductComplianceSummary,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductSustainabilitySummary,
    ProductUpdate,
)

router = APIRouter(
    prefix="/products",
    tags=["Product Twin"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("products:read", "products:write")),
    ],
)


# ── Product Core ──────────────────────────────────────────────────────────────


@router.get("", response_model=ProductListResponse)
async def list_products(
    product_type: ProductType | None = Query(default=None),
    product_status: ProductStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=200),
    regulated_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> ProductListResponse:
    svc = ProductService(db, kafka)
    items, total = await svc.list_for_org(
        organization_id=current_user.organization_id,
        product_type=product_type,
        product_status=product_status,
        search=search,
        category=category,
        regulated_only=regulated_only,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(
        items=[ProductResponse.from_model(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_product(
    body: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> ProductResponse:
    svc = ProductService(db, kafka)
    model = await svc.create(
        organization_id=current_user.organization_id,
        name=body.name,
        product_type=body.product_type,
        sku=body.sku,
        internal_code=body.internal_code,
        gtin=body.gtin,
        category=body.category,
        brand=body.brand,
        unit_of_measure=body.unit_of_measure,
        weight_kg=body.weight_kg,
        country_of_manufacture=body.country_of_manufacture,
        is_regulated_product=body.is_regulated_product,
        target_market=body.target_market,
        description=body.description,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return ProductResponse.from_model(model)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> ProductResponse:
    svc = ProductService(db, kafka)
    model = await svc.get(current_user.organization_id, product_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.from_model(model)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_analyst)],
)
async def update_product(
    product_id: str,
    body: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> ProductResponse:
    svc = ProductService(db, kafka)
    data = body.model_dump(exclude_unset=True)
    model = await svc.update(
        current_user.organization_id,
        product_id,
        actor_id=current_user.id,
        **data,
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.commit()
    return ProductResponse.from_model(model)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def archive_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = ProductService(db, kafka)
    deleted = await svc.archive(current_user.organization_id, product_id, actor_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.commit()


# ── BOM ───────────────────────────────────────────────────────────────────────


@router.get("/{product_id}/bom", response_model=list[ProductBOMItemResponse])
async def list_bom(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[ProductBOMItemResponse]:
    svc = ProductBOMService(db, kafka)
    items = await svc.list_bom(current_user.organization_id, product_id)
    return [ProductBOMItemResponse.from_model(m) for m in items]


@router.post(
    "/{product_id}/bom",
    response_model=ProductBOMItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def add_bom_item(
    product_id: str,
    body: ProductBOMItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> ProductBOMItemResponse:
    svc = ProductBOMService(db, kafka)
    model = await svc.add_item(
        organization_id=current_user.organization_id,
        product_id=product_id,
        material_id=body.material_id,
        weight_pct=body.weight_pct,
        quantity=body.quantity,
        unit=body.unit,
        is_substance_of_concern=body.is_substance_of_concern,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return ProductBOMItemResponse.from_model(model)


@router.delete(
    "/{product_id}/bom/{bom_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def delete_bom_item(
    product_id: str,
    bom_item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = ProductBOMService(db, kafka)
    deleted = await svc.delete_item(current_user.organization_id, bom_item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="BOM item not found")
    await db.commit()


# ── Aggregated views ──────────────────────────────────────────────────────────


@router.get(
    "/{product_id}/compliance",
    response_model=list[ProductComplianceSummary],
)
async def get_product_compliance(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[ProductComplianceSummary]:
    svc = ProductBOMService(db, kafka)
    rows = await svc.aggregate_compliance(current_user.organization_id, product_id)
    return [ProductComplianceSummary(**r) for r in rows]


@router.get(
    "/{product_id}/sustainability",
    response_model=ProductSustainabilitySummary,
)
async def get_product_sustainability(
    product_id: str,
    reporting_year: int | None = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> ProductSustainabilitySummary:
    svc = ProductBOMService(db, kafka)
    data = await svc.aggregate_sustainability(
        current_user.organization_id, product_id, reporting_year=reporting_year
    )
    return ProductSustainabilitySummary(**data)


@router.get("/{product_id}/dpp", response_model=list[DPPResponse])
async def list_product_dpps(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[DPPResponse]:
    svc = DPPService(db, kafka)
    items = await svc.list_for_product(current_user.organization_id, product_id)
    return [DPPResponse.from_model(m) for m in items]
