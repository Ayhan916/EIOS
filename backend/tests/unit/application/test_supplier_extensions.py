"""Unit tests — Supplier Twin Extensions (M25 / KAN-85–89)."""

from __future__ import annotations

from datetime import date, datetime, UTC

from domain.supplier_extensions import (
    CertificationType,
    ContactRole,
    ESGMetricType,
    LocationType,
    OwnershipType,
    SupplierCertification,
    SupplierContact,
    SupplierESGMetric,
    SupplierLocation,
    SupplierOwnership,
)
from infrastructure.kafka.events import DomainEvent, SupplierEventType


# ── Domain Entity Tests ───────────────────────────────────────────────────────

class TestSupplierLocation:
    def test_create_plant(self) -> None:
        loc = SupplierLocation(
            supplier_id="s1",
            organization_id="org1",
            location_type=LocationType.PLANT,
            name="Main Manufacturing Plant",
            country="DE",
        )
        assert loc.location_type == LocationType.PLANT
        assert loc.country == "DE"
        assert loc.is_active is True
        assert loc.is_primary is False

    def test_all_location_types_valid(self) -> None:
        for lt in LocationType:
            loc = SupplierLocation(
                supplier_id="s1",
                organization_id="org1",
                location_type=lt,
                name=f"Test {lt.value}",
            )
            assert loc.location_type == lt


class TestSupplierCertification:
    def test_expired_cert_detected(self) -> None:
        cert = SupplierCertification(
            supplier_id="s1",
            organization_id="org1",
            cert_type=CertificationType.ISO_14001,
            valid_until=date(2020, 1, 1),
        )
        assert cert.is_expired is True
        assert cert.days_until_expiry is not None
        assert cert.days_until_expiry < 0

    def test_valid_cert_not_expired(self) -> None:
        cert = SupplierCertification(
            supplier_id="s1",
            organization_id="org1",
            cert_type=CertificationType.IATF_16949,
            valid_until=date(2099, 12, 31),
        )
        assert cert.is_expired is False
        assert cert.days_until_expiry is not None
        assert cert.days_until_expiry > 0

    def test_no_expiry_date(self) -> None:
        cert = SupplierCertification(
            supplier_id="s1",
            organization_id="org1",
            cert_type=CertificationType.SA8000,
        )
        assert cert.is_expired is False
        assert cert.days_until_expiry is None

    def test_all_cert_types_valid(self) -> None:
        for ct in CertificationType:
            cert = SupplierCertification(
                supplier_id="s1",
                organization_id="org1",
                cert_type=ct,
            )
            assert cert.cert_type == ct


class TestSupplierOwnership:
    def test_state_owned_supplier(self) -> None:
        own = SupplierOwnership(
            supplier_id="s1",
            organization_id="org1",
            ownership_type=OwnershipType.STATE_OWNED,
            is_state_owned=True,
            state_ownership_pct=100.0,
            parent_company_country="CN",
        )
        assert own.is_state_owned is True
        assert own.state_ownership_pct == 100.0

    def test_publicly_listed_supplier(self) -> None:
        own = SupplierOwnership(
            supplier_id="s1",
            organization_id="org1",
            ownership_type=OwnershipType.PUBLIC,
            publicly_listed=True,
            stock_exchange="NYSE",
            ticker_symbol="ACME",
            lei_code="5493001KJTIIGC8Y1R12",
        )
        assert own.publicly_listed is True
        assert own.lei_code == "5493001KJTIIGC8Y1R12"


class TestSupplierESGMetric:
    def test_energy_metric(self) -> None:
        metric = SupplierESGMetric(
            supplier_id="s1",
            organization_id="org1",
            reporting_year=2024,
            metric_type=ESGMetricType.ENERGY_RENEWABLE_PCT,
            value=45.2,
            unit="%",
            esrs_reference="E1-5",
        )
        assert metric.value == 45.2
        assert metric.esrs_reference == "E1-5"
        assert metric.is_third_party_verified is False

    def test_social_metric(self) -> None:
        metric = SupplierESGMetric(
            supplier_id="s1",
            organization_id="org1",
            reporting_year=2024,
            metric_type=ESGMetricType.INJURY_RATE_PER_1M_HOURS,
            value=0.8,
            unit="per 1M hours",
            esrs_reference="S1-14",
            is_third_party_verified=True,
        )
        assert metric.metric_type == ESGMetricType.INJURY_RATE_PER_1M_HOURS
        assert metric.is_third_party_verified is True


# ── Kafka Event Tests ─────────────────────────────────────────────────────────

class TestDomainEvents:
    def test_location_created_event_serializes(self) -> None:
        event = DomainEvent.supplier_location_created(
            organization_id="org1",
            supplier_id="sup1",
            location_id="loc1",
            location_type="PLANT",
            actor_id="user1",
        )
        assert event.event_type == SupplierEventType.LOCATION_CREATED
        assert event.aggregate_type == "Supplier"
        assert event.aggregate_id == "sup1"
        assert event.organization_id == "org1"
        assert event.payload["location_type"] == "PLANT"

        payload_bytes = event.to_json()
        assert isinstance(payload_bytes, bytes)
        assert b"supplier.location.created" in payload_bytes
        assert b"PLANT" in payload_bytes

    def test_certification_event_serializes(self) -> None:
        event = DomainEvent.supplier_certification_created(
            organization_id="org1",
            supplier_id="sup1",
            certification_id="cert1",
            cert_type="ISO_14001",
            valid_until="2027-12-31",
        )
        assert event.event_type == SupplierEventType.CERTIFICATION_CREATED
        payload_bytes = event.to_json()
        assert b"ISO_14001" in payload_bytes
        assert b"2027-12-31" in payload_bytes

    def test_esg_metric_event_serializes(self) -> None:
        event = DomainEvent.supplier_esg_metric_recorded(
            organization_id="org1",
            supplier_id="sup1",
            metric_id="m1",
            metric_type="ENERGY_RENEWABLE_PCT",
            reporting_year=2024,
            value=45.2,
            unit="%",
        )
        assert event.payload["value"] == 45.2
        assert event.payload["reporting_year"] == 2024

    def test_ownership_event_serializes(self) -> None:
        event = DomainEvent.supplier_ownership_updated(
            organization_id="org1",
            supplier_id="sup1",
            ownership_id="own1",
            is_state_owned=True,
            parent_company_country="CN",
        )
        assert event.payload["is_state_owned"] is True
        assert event.payload["parent_company_country"] == "CN"

    def test_event_has_unique_id(self) -> None:
        e1 = DomainEvent.supplier_location_created("o", "s", "l", "PLANT")
        e2 = DomainEvent.supplier_location_created("o", "s", "l", "PLANT")
        assert e1.event_id != e2.event_id


# ── External ESG Rating Tests (KAN-90) ────────────────────────────────────────

from domain.supplier_extensions import ESGRatingProvider, ExternalESGRating


class TestExternalESGRating:
    def test_ecovadis_rating_with_grade(self) -> None:
        rating = ExternalESGRating(
            supplier_id="s1",
            organization_id="org1",
            provider=ESGRatingProvider.ECOVADIS,
            rating_date=date(2024, 3, 15),
            score=62.0,
            max_score=100.0,
            score_pct=62.0,
            grade="GOLD",
            percentile=82.0,
            peer_group="Automotive Components",
            environmental_score=65.0,
            social_score=60.0,
            governance_score=58.0,
            valid_until=date(2025, 3, 15),
        )
        assert rating.provider == ESGRatingProvider.ECOVADIS
        assert rating.score_pct == 62.0
        assert rating.grade == "GOLD"
        assert rating.percentile == 82.0

    def test_msci_rating_letter_grade(self) -> None:
        rating = ExternalESGRating(
            supplier_id="s1",
            organization_id="org1",
            provider=ESGRatingProvider.MSCI,
            rating_date=date(2024, 1, 10),
            grade="AA",
            score_pct=78.5,
        )
        assert rating.provider == ESGRatingProvider.MSCI
        assert rating.grade == "AA"
        assert rating.score is None
        assert rating.max_score is None

    def test_expired_rating_detected(self) -> None:
        rating = ExternalESGRating(
            supplier_id="s1",
            organization_id="org1",
            provider=ESGRatingProvider.SUSTAINALYTICS,
            rating_date=date(2021, 6, 1),
            valid_until=date(2022, 6, 1),
            score_pct=45.0,
        )
        assert rating.is_expired is True
        assert rating.days_until_expiry is not None
        assert rating.days_until_expiry < 0

    def test_no_expiry_date_never_expired(self) -> None:
        rating = ExternalESGRating(
            supplier_id="s1",
            organization_id="org1",
            provider=ESGRatingProvider.CDP,
            rating_date=date(2024, 11, 1),
            grade="CDP_A",
        )
        assert rating.is_expired is False
        assert rating.days_until_expiry is None

    def test_kafka_event_for_rating(self) -> None:
        from infrastructure.kafka.events import DomainEvent, SupplierEventType
        event = DomainEvent.supplier_esg_rating_received(
            organization_id="org1",
            supplier_id="sup1",
            rating_id="r1",
            provider="ECOVADIS",
            rating_date="2024-03-15",
            score_pct=62.0,
            grade="GOLD",
        )
        assert event.event_type == SupplierEventType.ESG_RATING_RECEIVED
        assert event.payload["provider"] == "ECOVADIS"
        assert event.payload["score_pct"] == 62.0
        assert event.payload["grade"] == "GOLD"
        payload_bytes = event.to_json()
        assert b"esg_rating.received" in payload_bytes
        assert b"ECOVADIS" in payload_bytes

    def test_all_providers_valid(self) -> None:
        for p in ESGRatingProvider:
            r = ExternalESGRating(
                supplier_id="s1",
                organization_id="org1",
                provider=p,
                rating_date=date(2024, 1, 1),
            )
            assert r.provider == p
