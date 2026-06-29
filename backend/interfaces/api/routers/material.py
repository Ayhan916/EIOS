"""Material Twin Router — M26 / KAN-91–97

18 endpoints across 5 sub-resources:
  /materials                          — list, create
  /materials/{id}                     — get, update, delete (archive)
  /materials/{id}/composition         — list, add
  /materials/{id}/composition/{cid}   — delete
  /materials/{id}/sourcing            — list, add
  /materials/{id}/sourcing/{sid}      — delete
  /materials/{id}/compliance          — list, upsert
  /materials/{id}/compliance/{fid}    — delete
  /materials/{id}/sustainability      — list, upsert
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.material.service import (
    MaterialComplianceService,
    MaterialCompositionService,
    MaterialService,
    MaterialSourcingService,
    MaterialSustainabilityService,
)
from domain.material import ComplianceRegulation, ComplianceStatus, MaterialStatus, MaterialType, SourcingRisk
from infrastructure.kafka.producer import KafkaEventProducer, get_kafka_producer
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_analyst,
    scope_gate,
)
from domain.user import User
from interfaces.api.schemas.material import (
    MaterialCompositionCreate,
    MaterialCompositionResponse,
    MaterialComplianceResponse,
    MaterialComplianceUpsert,
    MaterialCreate,
    MaterialListResponse,
    MaterialResponse,
    MaterialSourcingCreate,
    MaterialSourcingResponse,
    MaterialSustainabilityResponse,
    MaterialSustainabilityUpsert,
    MaterialUpdate,
)

router = APIRouter(
    prefix="/materials",
    tags=["Material Twin"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("materials:read", "materials:write")),
    ],
)


# ── Material Core ─────────────────────────────────────────────────────────────

@router.get("", response_model=MaterialListResponse)
async def list_materials(
    material_type: MaterialType | None = Query(default=None),
    material_status: MaterialStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    crm_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialListResponse:
    svc = MaterialService(db, kafka)
    items, total = await svc.list_for_org(
        organization_id=current_user.organization_id,
        material_type=material_type,
        material_status=material_status,
        search=search,
        crm_only=crm_only,
        limit=limit,
        offset=offset,
    )
    return MaterialListResponse(
        items=[MaterialResponse.from_model(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_material(
    body: MaterialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialResponse:
    svc = MaterialService(db, kafka)
    model = await svc.create(
        organization_id=current_user.organization_id,
        name=body.name,
        material_type=body.material_type,
        internal_code=body.internal_code,
        cas_number=body.cas_number,
        ec_number=body.ec_number,
        iupac_name=body.iupac_name,
        molecular_formula=body.molecular_formula,
        hs_code=body.hs_code,
        un_number=body.un_number,
        ghs_hazard_class=body.ghs_hazard_class,
        unit_of_measure=body.unit_of_measure,
        weight_per_unit_kg=body.weight_per_unit_kg,
        country_of_origin=body.country_of_origin,
        is_critical_raw_material=body.is_critical_raw_material,
        recycled_content_pct=body.recycled_content_pct,
        description=body.description,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return MaterialResponse.from_model(model)


@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialResponse:
    svc = MaterialService(db, kafka)
    model = await svc.get(current_user.organization_id, material_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return MaterialResponse.from_model(model)


@router.put(
    "/{material_id}",
    response_model=MaterialResponse,
    dependencies=[Depends(require_analyst)],
)
async def update_material(
    material_id: str,
    body: MaterialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialResponse:
    svc = MaterialService(db, kafka)
    data = body.model_dump(exclude_unset=True)
    model = await svc.update(
        current_user.organization_id,
        material_id,
        actor_id=current_user.id,
        **data,
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Material not found")
    await db.commit()
    return MaterialResponse.from_model(model)


@router.delete(
    "/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def archive_material(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = MaterialService(db, kafka)
    deleted = await svc.archive(current_user.organization_id, material_id, actor_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Material not found")
    await db.commit()


# ── Composition / BOM ─────────────────────────────────────────────────────────

@router.get("/{material_id}/composition", response_model=list[MaterialCompositionResponse])
async def list_composition(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[MaterialCompositionResponse]:
    svc = MaterialCompositionService(db, kafka)
    items = await svc.list_for_material(current_user.organization_id, material_id)
    return [MaterialCompositionResponse.from_model(m) for m in items]


@router.post(
    "/{material_id}/composition",
    response_model=MaterialCompositionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def add_composition(
    material_id: str,
    body: MaterialCompositionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialCompositionResponse:
    svc = MaterialCompositionService(db, kafka)
    model = await svc.add(
        organization_id=current_user.organization_id,
        parent_material_id=material_id,
        child_material_id=body.child_material_id,
        weight_pct=body.weight_pct,
        quantity=body.quantity,
        unit=body.unit,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return MaterialCompositionResponse.from_model(model)


@router.delete(
    "/{material_id}/composition/{composition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def delete_composition(
    material_id: str,
    composition_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = MaterialCompositionService(db, kafka)
    deleted = await svc.delete(current_user.organization_id, composition_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Composition entry not found")
    await db.commit()


# ── Sourcing ──────────────────────────────────────────────────────────────────

@router.get("/{material_id}/sourcing", response_model=list[MaterialSourcingResponse])
async def list_sourcing(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[MaterialSourcingResponse]:
    svc = MaterialSourcingService(db, kafka)
    items = await svc.list_for_material(current_user.organization_id, material_id)
    return [MaterialSourcingResponse.from_model(m) for m in items]


@router.post(
    "/{material_id}/sourcing",
    response_model=MaterialSourcingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def add_sourcing(
    material_id: str,
    body: MaterialSourcingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialSourcingResponse:
    svc = MaterialSourcingService(db, kafka)
    model = await svc.add(
        organization_id=current_user.organization_id,
        material_id=material_id,
        supplier_id=body.supplier_id,
        country_of_origin=body.country_of_origin,
        annual_volume=body.annual_volume,
        unit=body.unit,
        price_per_unit_eur=body.price_per_unit_eur,
        is_primary=body.is_primary,
        lead_time_days=body.lead_time_days,
        sourcing_risk=body.sourcing_risk,
        certification_required=body.certification_required,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return MaterialSourcingResponse.from_model(model)


@router.delete(
    "/{material_id}/sourcing/{sourcing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def delete_sourcing(
    material_id: str,
    sourcing_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = MaterialSourcingService(db, kafka)
    deleted = await svc.delete(current_user.organization_id, sourcing_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sourcing record not found")
    await db.commit()


# ── Compliance Flags ──────────────────────────────────────────────────────────

@router.get("/{material_id}/compliance", response_model=list[MaterialComplianceResponse])
async def list_compliance(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[MaterialComplianceResponse]:
    svc = MaterialComplianceService(db, kafka)
    items = await svc.list_for_material(current_user.organization_id, material_id)
    return [MaterialComplianceResponse.from_model(m) for m in items]


@router.post(
    "/{material_id}/compliance",
    response_model=MaterialComplianceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def upsert_compliance(
    material_id: str,
    body: MaterialComplianceUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialComplianceResponse:
    svc = MaterialComplianceService(db, kafka)
    model = await svc.upsert(
        organization_id=current_user.organization_id,
        material_id=material_id,
        regulation=body.regulation,
        compliance_status=body.compliance_status,
        custom_regulation_name=body.custom_regulation_name,
        assessed_at=body.assessed_at,
        valid_until=body.valid_until,
        assessor=body.assessor,
        evidence_id=body.evidence_id,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return MaterialComplianceResponse.from_model(model)


@router.delete(
    "/{material_id}/compliance/{flag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def delete_compliance_flag(
    material_id: str,
    flag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = MaterialComplianceService(db, kafka)
    deleted = await svc.delete(current_user.organization_id, flag_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Compliance flag not found")
    await db.commit()


# ── Sustainability Metrics ────────────────────────────────────────────────────

@router.get("/{material_id}/sustainability", response_model=list[MaterialSustainabilityResponse])
async def list_sustainability(
    material_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[MaterialSustainabilityResponse]:
    svc = MaterialSustainabilityService(db, kafka)
    items = await svc.list_for_material(current_user.organization_id, material_id)
    return [MaterialSustainabilityResponse.from_model(m) for m in items]


@router.post(
    "/{material_id}/sustainability",
    response_model=MaterialSustainabilityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def upsert_sustainability(
    material_id: str,
    body: MaterialSustainabilityUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> MaterialSustainabilityResponse:
    svc = MaterialSustainabilityService(db, kafka)
    model = await svc.upsert(
        organization_id=current_user.organization_id,
        material_id=material_id,
        reporting_year=body.reporting_year,
        carbon_footprint_kg_co2e_per_kg=body.carbon_footprint_kg_co2e_per_kg,
        carbon_scope=body.carbon_scope,
        water_footprint_l_per_kg=body.water_footprint_l_per_kg,
        energy_mj_per_kg=body.energy_mj_per_kg,
        energy_renewable_pct=body.energy_renewable_pct,
        recycled_content_pct=body.recycled_content_pct,
        recyclability_pct=body.recyclability_pct,
        biodegradable=body.biodegradable,
        data_source=body.data_source,
        is_third_party_verified=body.is_third_party_verified,
        verification_standard=body.verification_standard,
        evidence_id=body.evidence_id,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return MaterialSustainabilityResponse.from_model(model)
