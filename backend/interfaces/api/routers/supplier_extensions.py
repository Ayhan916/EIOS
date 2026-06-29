"""
M25 — Supplier Twin Extensions API Router (KAN-85–89)

Sub-resources of the Supplier entity:
  GET/POST   /suppliers/{id}/locations
  GET/DELETE /suppliers/{id}/locations/{location_id}
  GET/POST   /suppliers/{id}/contacts
  GET        /suppliers/{id}/contacts/{contact_id}
  GET/POST   /suppliers/{id}/certifications
  GET        /suppliers/{id}/certifications/{cert_id}
  GET/PUT    /suppliers/{id}/ownership
  GET/POST   /suppliers/{id}/esg-metrics
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.supplier_twin.service import (
    SupplierCertificationService,
    SupplierContactService,
    SupplierESGMetricService,
    SupplierExternalESGRatingService,
    SupplierLocationService,
    SupplierOwnershipService,
)
from domain.supplier_extensions import (
    CertificationType,
    ContactRole,
    ESGMetricType,
    ESGRatingProvider,
    LocationType,
    OwnershipType,
)
from infrastructure.kafka.producer import KafkaEventProducer, get_kafka_producer
from infrastructure.persistence.models.supplier import SupplierModel
from interfaces.api.deps import (
    get_current_user,
    get_db,
    require_analyst,
    scope_gate,
)
from interfaces.api.schemas.supplier_extensions import (
    ExternalESGRatingCreate,
    ExternalESGRatingResponse,
    SupplierCertificationCreate,
    SupplierCertificationResponse,
    SupplierContactCreate,
    SupplierContactResponse,
    SupplierContactUpdate,
    SupplierESGMetricRecord,
    SupplierESGMetricResponse,
    SupplierLocationCreate,
    SupplierLocationResponse,
    SupplierLocationUpdate,
    SupplierOwnershipResponse,
    SupplierOwnershipUpsert,
)
from domain.user import User

router = APIRouter(
    prefix="/suppliers",
    tags=["supplier-twin"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("suppliers:read", "suppliers:write")),
    ],
)


async def _assert_supplier_access(
    supplier_id: str,
    organization_id: str,
    db: AsyncSession,
) -> SupplierModel:
    model = await db.get(SupplierModel, supplier_id)
    if model is None or model.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return model


# ── Locations ─────────────────────────────────────────────────────────────────

@router.get("/{supplier_id}/locations", response_model=list[SupplierLocationResponse])
async def list_locations(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[SupplierLocationResponse]:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierLocationService(db, kafka)
    models = await svc.list_for_supplier(current_user.organization_id or "", supplier_id)
    return [SupplierLocationResponse.model_validate(m) for m in models]


@router.post(
    "/{supplier_id}/locations",
    response_model=SupplierLocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_location(
    supplier_id: str,
    body: SupplierLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierLocationResponse:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierLocationService(db, kafka)
    model = await svc.create(
        organization_id=current_user.organization_id or "",
        supplier_id=supplier_id,
        location_type=body.location_type,
        name=body.name,
        address=body.address,
        city=body.city,
        country=body.country,
        postal_code=body.postal_code,
        region=body.region,
        latitude=body.latitude,
        longitude=body.longitude,
        capacity_description=body.capacity_description,
        employee_count=body.employee_count,
        is_primary=body.is_primary,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return SupplierLocationResponse.model_validate(model)


@router.get("/{supplier_id}/locations/{location_id}", response_model=SupplierLocationResponse)
async def get_location(
    supplier_id: str,
    location_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierLocationResponse:
    svc = SupplierLocationService(db, kafka)
    model = await svc.get(current_user.organization_id or "", location_id)
    if model is None or model.supplier_id != supplier_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return SupplierLocationResponse.model_validate(model)


@router.delete(
    "/{supplier_id}/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def delete_location(
    supplier_id: str,
    location_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    svc = SupplierLocationService(db, kafka)
    deleted = await svc.delete(current_user.organization_id or "", location_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    await db.commit()


# ── Contacts ──────────────────────────────────────────────────────────────────

@router.get("/{supplier_id}/contacts", response_model=list[SupplierContactResponse])
async def list_contacts(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[SupplierContactResponse]:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierContactService(db, kafka)
    models = await svc.list_for_supplier(current_user.organization_id or "", supplier_id)
    return [SupplierContactResponse.from_model(m) for m in models]


@router.post(
    "/{supplier_id}/contacts",
    response_model=SupplierContactResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_contact(
    supplier_id: str,
    body: SupplierContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierContactResponse:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierContactService(db, kafka)
    model = await svc.create(
        organization_id=current_user.organization_id or "",
        supplier_id=supplier_id,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        job_title=body.job_title,
        department=body.department,
        language=body.language,
        is_primary=body.is_primary,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return SupplierContactResponse.from_model(model)


@router.put(
    "/{supplier_id}/contacts/{contact_id}",
    response_model=SupplierContactResponse,
    dependencies=[Depends(require_analyst)],
)
async def update_contact(
    supplier_id: str,
    contact_id: str,
    body: SupplierContactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierContactResponse:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierContactService(db, kafka)
    model = await svc.update(
        organization_id=current_user.organization_id or "",
        contact_id=contact_id,
        **body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    await db.commit()
    return SupplierContactResponse.from_model(model)


# ── Certifications ────────────────────────────────────────────────────────────

@router.get("/{supplier_id}/certifications", response_model=list[SupplierCertificationResponse])
async def list_certifications(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[SupplierCertificationResponse]:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierCertificationService(db, kafka)
    models = await svc.list_for_supplier(current_user.organization_id or "", supplier_id)
    return [SupplierCertificationResponse.from_model(m) for m in models]


@router.post(
    "/{supplier_id}/certifications",
    response_model=SupplierCertificationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_certification(
    supplier_id: str,
    body: SupplierCertificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierCertificationResponse:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierCertificationService(db, kafka)
    model = await svc.create(
        organization_id=current_user.organization_id or "",
        supplier_id=supplier_id,
        cert_type=body.cert_type,
        custom_cert_name=body.custom_cert_name,
        issuing_body=body.issuing_body,
        certificate_number=body.certificate_number,
        scope_description=body.scope_description,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        evidence_id=body.evidence_id,
        location_id=body.location_id,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return SupplierCertificationResponse.from_model(model)


# ── Ownership ─────────────────────────────────────────────────────────────────

@router.get("/{supplier_id}/ownership", response_model=SupplierOwnershipResponse | None)
async def get_ownership(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierOwnershipResponse | None:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierOwnershipService(db, kafka)
    model = await svc.get_for_supplier(current_user.organization_id or "", supplier_id)
    if model is None:
        return None
    return SupplierOwnershipResponse.model_validate(model)


@router.put(
    "/{supplier_id}/ownership",
    response_model=SupplierOwnershipResponse,
    dependencies=[Depends(require_analyst)],
)
async def upsert_ownership(
    supplier_id: str,
    body: SupplierOwnershipUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierOwnershipResponse:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierOwnershipService(db, kafka)
    model = await svc.upsert(
        organization_id=current_user.organization_id or "",
        supplier_id=supplier_id,
        **body.model_dump(),
        actor_id=current_user.id,
    )
    await db.commit()
    return SupplierOwnershipResponse.model_validate(model)


# ── ESG Metrics ───────────────────────────────────────────────────────────────

@router.get("/{supplier_id}/esg-metrics", response_model=list[SupplierESGMetricResponse])
async def list_esg_metrics(
    supplier_id: str,
    reporting_year: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[SupplierESGMetricResponse]:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierESGMetricService(db, kafka)
    models = await svc.list_for_supplier(
        current_user.organization_id or "", supplier_id, reporting_year
    )
    return [SupplierESGMetricResponse.model_validate(m) for m in models]


@router.post(
    "/{supplier_id}/esg-metrics",
    response_model=SupplierESGMetricResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def record_esg_metric(
    supplier_id: str,
    body: SupplierESGMetricRecord,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> SupplierESGMetricResponse:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierESGMetricService(db, kafka)
    model = await svc.record(
        organization_id=current_user.organization_id or "",
        supplier_id=supplier_id,
        reporting_year=body.reporting_year,
        metric_type=body.metric_type,
        value=body.value,
        unit=body.unit,
        reporting_period=body.reporting_period,
        custom_metric_name=body.custom_metric_name,
        esrs_reference=body.esrs_reference,
        gri_reference=body.gri_reference,
        data_source=body.data_source,
        is_third_party_verified=body.is_third_party_verified,
        verification_standard=body.verification_standard,
        evidence_id=body.evidence_id,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return SupplierESGMetricResponse.model_validate(model)


# ── External ESG Ratings (KAN-90) ─────────────────────────────────────────────

@router.get("/{supplier_id}/esg-ratings", response_model=list[ExternalESGRatingResponse])
async def list_esg_ratings(
    supplier_id: str,
    provider: ESGRatingProvider | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> list[ExternalESGRatingResponse]:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierExternalESGRatingService(db, kafka)
    models = await svc.list_for_supplier(
        current_user.organization_id or "", supplier_id, provider
    )
    return [ExternalESGRatingResponse.from_model(m) for m in models]


@router.post(
    "/{supplier_id}/esg-ratings",
    response_model=ExternalESGRatingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_esg_rating(
    supplier_id: str,
    body: ExternalESGRatingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> ExternalESGRatingResponse:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierExternalESGRatingService(db, kafka)
    model = await svc.record(
        organization_id=current_user.organization_id or "",
        supplier_id=supplier_id,
        provider=body.provider,
        rating_date=body.rating_date,
        score=body.score,
        max_score=body.max_score,
        score_pct=body.score_pct,
        grade=body.grade,
        percentile=body.percentile,
        peer_group=body.peer_group,
        environmental_score=body.environmental_score,
        social_score=body.social_score,
        governance_score=body.governance_score,
        ethics_score=body.ethics_score,
        sustainable_procurement_score=body.sustainable_procurement_score,
        valid_until=body.valid_until,
        report_url=body.report_url,
        methodology_version=body.methodology_version,
        evidence_id=body.evidence_id,
        notes=body.notes,
        actor_id=current_user.id,
    )
    await db.commit()
    return ExternalESGRatingResponse.from_model(model)


@router.delete(
    "/{supplier_id}/esg-ratings/{rating_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_analyst)],
)
async def delete_esg_rating(
    supplier_id: str,
    rating_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kafka: KafkaEventProducer = Depends(get_kafka_producer),
) -> None:
    await _assert_supplier_access(supplier_id, current_user.organization_id or "", db)
    svc = SupplierExternalESGRatingService(db, kafka)
    deleted = await svc.delete(current_user.organization_id or "", rating_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")
    await db.commit()
