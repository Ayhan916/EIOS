"""
M25 — Supplier Twin Extension Service

Business logic for the five new Supplier Twin dimensions:
locations, contacts, certifications, ownership, ESG metrics.

Publishes domain events to Kafka after every successful mutation.
Session ownership: caller (router) commits; service only flushes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.supplier_extensions import (
    CertificationType,
    ContactRole,
    ESGMetricType,
    ESGRatingProvider,
    LocationType,
    OwnershipType,
)
from infrastructure.kafka.events import DomainEvent
from infrastructure.kafka.producer import KafkaEventProducer
from infrastructure.persistence.models.supplier_extensions import (
    SupplierCertificationModel,
    SupplierContactModel,
    SupplierESGMetricModel,
    SupplierExternalESGRatingModel,
    SupplierLocationModel,
    SupplierOwnershipModel,
)

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> str:
    return str(uuid4())


# ── Locations ─────────────────────────────────────────────────────────────────


class SupplierLocationService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def create(
        self,
        organization_id: str,
        supplier_id: str,
        location_type: LocationType,
        name: str,
        *,
        address: str | None = None,
        city: str | None = None,
        country: str = "",
        postal_code: str | None = None,
        region: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        capacity_description: str | None = None,
        employee_count: int | None = None,
        is_primary: bool = False,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> SupplierLocationModel:
        now = _now()
        model = SupplierLocationModel(
            id=_uid(),
            supplier_id=supplier_id,
            organization_id=organization_id,
            location_type=location_type.value,
            name=name,
            address=address,
            city=city,
            country=country,
            postal_code=postal_code,
            region=region,
            latitude=latitude,
            longitude=longitude,
            capacity_description=capacity_description,
            employee_count=employee_count,
            is_primary=is_primary,
            is_active=True,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()

        await self._kafka.publish_supplier_event(
            DomainEvent.supplier_location_created(
                organization_id=organization_id,
                supplier_id=supplier_id,
                location_id=model.id,
                location_type=location_type.value,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_supplier(
        self, organization_id: str, supplier_id: str
    ) -> list[SupplierLocationModel]:
        stmt = (
            select(SupplierLocationModel)
            .where(
                SupplierLocationModel.organization_id == organization_id,
                SupplierLocationModel.supplier_id == supplier_id,
                SupplierLocationModel.is_active.is_(True),
            )
            .order_by(SupplierLocationModel.is_primary.desc(), SupplierLocationModel.name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, organization_id: str, location_id: str) -> SupplierLocationModel | None:
        model = await self._session.get(SupplierLocationModel, location_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    async def delete(self, organization_id: str, location_id: str) -> bool:
        model = await self.get(organization_id, location_id)
        if model is None:
            return False
        model.is_active = False
        model.updated_at = _now()
        await self._session.flush()
        return True


# ── Contacts ──────────────────────────────────────────────────────────────────


class SupplierContactService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def create(
        self,
        organization_id: str,
        supplier_id: str,
        first_name: str,
        last_name: str,
        *,
        email: str | None = None,
        phone: str | None = None,
        role: ContactRole = ContactRole.OTHER,
        job_title: str | None = None,
        department: str | None = None,
        language: str = "en",
        is_primary: bool = False,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> SupplierContactModel:
        now = _now()
        model = SupplierContactModel(
            id=_uid(),
            supplier_id=supplier_id,
            organization_id=organization_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            role=role.value,
            job_title=job_title,
            department=department,
            language=language,
            is_primary=is_primary,
            is_active=True,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_for_supplier(
        self, organization_id: str, supplier_id: str
    ) -> list[SupplierContactModel]:
        stmt = (
            select(SupplierContactModel)
            .where(
                SupplierContactModel.organization_id == organization_id,
                SupplierContactModel.supplier_id == supplier_id,
                SupplierContactModel.is_active.is_(True),
            )
            .order_by(SupplierContactModel.is_primary.desc(), SupplierContactModel.last_name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, organization_id: str, contact_id: str) -> SupplierContactModel | None:
        model = await self._session.get(SupplierContactModel, contact_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    async def update(
        self,
        organization_id: str,
        contact_id: str,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        role: ContactRole | None = None,
        job_title: str | None = None,
        department: str | None = None,
        is_primary: bool | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> SupplierContactModel | None:
        model = await self.get(organization_id, contact_id)
        if model is None:
            return None
        if first_name is not None:
            model.first_name = first_name
        if last_name is not None:
            model.last_name = last_name
        if email is not None:
            model.email = email
        if phone is not None:
            model.phone = phone
        if role is not None:
            model.role = role.value
        if job_title is not None:
            model.job_title = job_title
        if department is not None:
            model.department = department
        if is_primary is not None:
            model.is_primary = is_primary
        if is_active is not None:
            model.is_active = is_active
        if notes is not None:
            model.notes = notes
        model.updated_at = _now()
        await self._session.flush()
        return model


# ── Certifications ────────────────────────────────────────────────────────────


class SupplierCertificationService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def create(
        self,
        organization_id: str,
        supplier_id: str,
        cert_type: CertificationType,
        *,
        custom_cert_name: str | None = None,
        issuing_body: str | None = None,
        certificate_number: str | None = None,
        scope_description: str | None = None,
        valid_from: date | None = None,
        valid_until: date | None = None,
        evidence_id: str | None = None,
        location_id: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> SupplierCertificationModel:
        now = _now()
        is_expired = valid_until is not None and valid_until < now.date()
        model = SupplierCertificationModel(
            id=_uid(),
            supplier_id=supplier_id,
            organization_id=organization_id,
            cert_type=cert_type.value,
            custom_cert_name=custom_cert_name,
            issuing_body=issuing_body,
            certificate_number=certificate_number,
            scope_description=scope_description,
            valid_from=valid_from,
            valid_until=valid_until,
            is_expired_flag=is_expired,
            is_verified=False,
            evidence_id=evidence_id,
            location_id=location_id,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()

        await self._kafka.publish_supplier_event(
            DomainEvent.supplier_certification_created(
                organization_id=organization_id,
                supplier_id=supplier_id,
                certification_id=model.id,
                cert_type=cert_type.value,
                valid_until=valid_until.isoformat() if valid_until else None,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_supplier(
        self, organization_id: str, supplier_id: str
    ) -> list[SupplierCertificationModel]:
        stmt = (
            select(SupplierCertificationModel)
            .where(
                SupplierCertificationModel.organization_id == organization_id,
                SupplierCertificationModel.supplier_id == supplier_id,
            )
            .order_by(SupplierCertificationModel.cert_type, SupplierCertificationModel.valid_until)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, organization_id: str, cert_id: str) -> SupplierCertificationModel | None:
        model = await self._session.get(SupplierCertificationModel, cert_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model


# ── Ownership ─────────────────────────────────────────────────────────────────


class SupplierOwnershipService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def upsert(
        self,
        organization_id: str,
        supplier_id: str,
        *,
        ownership_type: OwnershipType = OwnershipType.PRIVATE,
        parent_company_name: str | None = None,
        parent_company_country: str | None = None,
        ownership_percentage: float | None = None,
        ultimate_beneficial_owner: str | None = None,
        ubo_country: str | None = None,
        ubo_ownership_pct: float | None = None,
        publicly_listed: bool = False,
        stock_exchange: str | None = None,
        ticker_symbol: str | None = None,
        market_cap_eur: float | None = None,
        lei_code: str | None = None,
        duns_number: str | None = None,
        vat_number: str | None = None,
        registration_number: str | None = None,
        registration_country: str | None = None,
        is_state_owned: bool = False,
        state_ownership_pct: float | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> SupplierOwnershipModel:
        existing = await self.get_for_supplier(organization_id, supplier_id)
        now = _now()

        if existing is None:
            model = SupplierOwnershipModel(
                id=_uid(),
                supplier_id=supplier_id,
                organization_id=organization_id,
                created_at=now,
                updated_at=now,
                created_by=actor_id,
            )
            self._session.add(model)
        else:
            model = existing
            model.updated_at = now
            model.updated_by = actor_id

        model.ownership_type = ownership_type.value
        model.parent_company_name = parent_company_name
        model.parent_company_country = parent_company_country
        model.ownership_percentage = ownership_percentage
        model.ultimate_beneficial_owner = ultimate_beneficial_owner
        model.ubo_country = ubo_country
        model.ubo_ownership_pct = ubo_ownership_pct
        model.publicly_listed = publicly_listed
        model.stock_exchange = stock_exchange
        model.ticker_symbol = ticker_symbol
        model.market_cap_eur = market_cap_eur
        model.lei_code = lei_code
        model.duns_number = duns_number
        model.vat_number = vat_number
        model.registration_number = registration_number
        model.registration_country = registration_country
        model.is_state_owned = is_state_owned
        model.state_ownership_pct = state_ownership_pct
        model.notes = notes

        await self._session.flush()

        await self._kafka.publish_supplier_event(
            DomainEvent.supplier_ownership_updated(
                organization_id=organization_id,
                supplier_id=supplier_id,
                ownership_id=model.id,
                is_state_owned=is_state_owned,
                parent_company_country=parent_company_country,
                actor_id=actor_id,
            )
        )
        return model

    async def get_for_supplier(
        self, organization_id: str, supplier_id: str
    ) -> SupplierOwnershipModel | None:
        stmt = select(SupplierOwnershipModel).where(
            SupplierOwnershipModel.organization_id == organization_id,
            SupplierOwnershipModel.supplier_id == supplier_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


# ── ESG Metrics ───────────────────────────────────────────────────────────────


class SupplierESGMetricService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def record(
        self,
        organization_id: str,
        supplier_id: str,
        reporting_year: int,
        metric_type: ESGMetricType,
        value: float,
        unit: str,
        *,
        reporting_period: str = "ANNUAL",
        custom_metric_name: str | None = None,
        esrs_reference: str | None = None,
        gri_reference: str | None = None,
        data_source: str | None = None,
        is_third_party_verified: bool = False,
        verification_standard: str | None = None,
        evidence_id: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> SupplierESGMetricModel:
        # Upsert: unique constraint on (supplier_id, org_id, year, period, metric_type)
        stmt = select(SupplierESGMetricModel).where(
            SupplierESGMetricModel.organization_id == organization_id,
            SupplierESGMetricModel.supplier_id == supplier_id,
            SupplierESGMetricModel.reporting_year == reporting_year,
            SupplierESGMetricModel.reporting_period == reporting_period,
            SupplierESGMetricModel.metric_type == metric_type.value,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        now = _now()

        if existing is None:
            model = SupplierESGMetricModel(
                id=_uid(),
                supplier_id=supplier_id,
                organization_id=organization_id,
                reporting_year=reporting_year,
                reporting_period=reporting_period,
                metric_type=metric_type.value,
                created_at=now,
                updated_at=now,
                created_by=actor_id,
            )
            self._session.add(model)
        else:
            model = existing
            model.updated_at = now
            model.updated_by = actor_id

        model.custom_metric_name = custom_metric_name
        model.value = value
        model.unit = unit
        model.esrs_reference = esrs_reference
        model.gri_reference = gri_reference
        model.data_source = data_source
        model.is_third_party_verified = is_third_party_verified
        model.verification_standard = verification_standard
        model.evidence_id = evidence_id
        model.notes = notes

        await self._session.flush()

        await self._kafka.publish_supplier_event(
            DomainEvent.supplier_esg_metric_recorded(
                organization_id=organization_id,
                supplier_id=supplier_id,
                metric_id=model.id,
                metric_type=metric_type.value,
                reporting_year=reporting_year,
                value=value,
                unit=unit,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_supplier(
        self,
        organization_id: str,
        supplier_id: str,
        reporting_year: int | None = None,
    ) -> list[SupplierESGMetricModel]:
        stmt = select(SupplierESGMetricModel).where(
            SupplierESGMetricModel.organization_id == organization_id,
            SupplierESGMetricModel.supplier_id == supplier_id,
        )
        if reporting_year is not None:
            stmt = stmt.where(SupplierESGMetricModel.reporting_year == reporting_year)
        stmt = stmt.order_by(
            SupplierESGMetricModel.reporting_year.desc(),
            SupplierESGMetricModel.metric_type,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ── External ESG Ratings (KAN-90) ─────────────────────────────────────────────


class SupplierExternalESGRatingService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def record(
        self,
        organization_id: str,
        supplier_id: str,
        provider: ESGRatingProvider,
        rating_date: date,
        *,
        score: float | None = None,
        max_score: float | None = None,
        score_pct: float | None = None,
        grade: str | None = None,
        percentile: float | None = None,
        peer_group: str | None = None,
        environmental_score: float | None = None,
        social_score: float | None = None,
        governance_score: float | None = None,
        ethics_score: float | None = None,
        sustainable_procurement_score: float | None = None,
        valid_until: date | None = None,
        report_url: str | None = None,
        methodology_version: str | None = None,
        evidence_id: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> SupplierExternalESGRatingModel:
        # Auto-compute score_pct if score + max_score given but pct not provided
        computed_pct = score_pct
        if computed_pct is None and score is not None and max_score and max_score > 0:
            computed_pct = round(score / max_score * 100, 2)

        now = _now()
        model = SupplierExternalESGRatingModel(
            id=_uid(),
            supplier_id=supplier_id,
            organization_id=organization_id,
            provider=provider.value,
            rating_date=rating_date,
            score=score,
            max_score=max_score,
            score_pct=computed_pct,
            grade=grade,
            percentile=percentile,
            peer_group=peer_group,
            environmental_score=environmental_score,
            social_score=social_score,
            governance_score=governance_score,
            ethics_score=ethics_score,
            sustainable_procurement_score=sustainable_procurement_score,
            valid_until=valid_until,
            report_url=report_url,
            methodology_version=methodology_version,
            evidence_id=evidence_id,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()

        await self._kafka.publish_supplier_event(
            DomainEvent.supplier_esg_rating_received(
                organization_id=organization_id,
                supplier_id=supplier_id,
                rating_id=model.id,
                provider=provider.value,
                rating_date=str(rating_date),
                score_pct=computed_pct,
                grade=grade,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_supplier(
        self,
        organization_id: str,
        supplier_id: str,
        provider: ESGRatingProvider | None = None,
    ) -> list[SupplierExternalESGRatingModel]:
        stmt = (
            select(SupplierExternalESGRatingModel)
            .where(
                SupplierExternalESGRatingModel.organization_id == organization_id,
                SupplierExternalESGRatingModel.supplier_id == supplier_id,
            )
            .order_by(
                SupplierExternalESGRatingModel.rating_date.desc(),
                SupplierExternalESGRatingModel.provider,
            )
        )
        if provider is not None:
            stmt = stmt.where(SupplierExternalESGRatingModel.provider == provider.value)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(
        self, organization_id: str, rating_id: str
    ) -> SupplierExternalESGRatingModel | None:
        model = await self._session.get(SupplierExternalESGRatingModel, rating_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    async def delete(self, organization_id: str, rating_id: str) -> bool:
        model = await self.get(organization_id, rating_id)
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True
