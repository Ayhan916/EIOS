"""Repository — Company Profiles / CSDDD Threshold Monitor (CSDDD-010)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.threshold_monitor import CompanyProfile
from infrastructure.persistence.models.threshold_monitor import CompanyProfileModel


def _now() -> datetime:
    return datetime.now(UTC)


def _to_domain(m: CompanyProfileModel) -> CompanyProfile:
    return CompanyProfile(
        id=m.id,
        organization_id=m.organization_id,
        fiscal_year=m.fiscal_year,
        employee_count_worldwide=m.employee_count_worldwide,
        net_revenue_eur_millions=m.net_revenue_eur_millions,
        headquarters_country=m.headquarters_country,
        sector=m.sector,
        non_eu_company=m.non_eu_company,
        notes=m.notes,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLCompanyProfileRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def latest(self, organization_id: str) -> CompanyProfile | None:
        stmt = (
            select(CompanyProfileModel)
            .where(CompanyProfileModel.organization_id == organization_id)
            .order_by(CompanyProfileModel.fiscal_year.desc())
            .limit(1)
        )
        m = self._s.execute(stmt).scalar_one_or_none()
        return _to_domain(m) if m else None

    def list_org(self, organization_id: str) -> list[CompanyProfile]:
        stmt = (
            select(CompanyProfileModel)
            .where(CompanyProfileModel.organization_id == organization_id)
            .order_by(CompanyProfileModel.fiscal_year.desc())
        )
        return [_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get_by_year(self, organization_id: str, fiscal_year: int) -> CompanyProfile | None:
        stmt = select(CompanyProfileModel).where(
            CompanyProfileModel.organization_id == organization_id,
            CompanyProfileModel.fiscal_year == fiscal_year,
        )
        m = self._s.execute(stmt).scalar_one_or_none()
        return _to_domain(m) if m else None

    def upsert(
        self,
        organization_id: str,
        fiscal_year: int,
        employee_count_worldwide: int,
        net_revenue_eur_millions: float,
        headquarters_country: str,
        sector: str,
        non_eu_company: bool,
        notes: str,
        created_by: str,
    ) -> CompanyProfile:
        existing = self.get_by_year(organization_id, fiscal_year)
        if existing:
            m = self._s.get(CompanyProfileModel, existing.id)
            m.employee_count_worldwide = employee_count_worldwide
            m.net_revenue_eur_millions = net_revenue_eur_millions
            m.headquarters_country = headquarters_country
            m.sector = sector
            m.non_eu_company = non_eu_company
            m.notes = notes
            m.updated_at = _now()
        else:
            m = CompanyProfileModel(
                id=str(uuid4()),
                organization_id=organization_id,
                fiscal_year=fiscal_year,
                employee_count_worldwide=employee_count_worldwide,
                net_revenue_eur_millions=net_revenue_eur_millions,
                headquarters_country=headquarters_country,
                sector=sector,
                non_eu_company=non_eu_company,
                notes=notes,
                created_by=created_by,
                created_at=_now(),
                updated_at=_now(),
            )
            self._s.add(m)
        self._s.flush()
        return _to_domain(m)
