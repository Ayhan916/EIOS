"""Country Risk Intelligence Service — M34.

Builds and queries CountryRiskProfiles from ingested external datasets.
Profiles are derived from multiple sources and weighted into a single
overall_risk_score. Source attribution is preserved on every profile.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import CountryRiskLevel, EntityStatus
from domain.external_intelligence import CountryRiskProfile

_RISK_THRESHOLDS = {
    CountryRiskLevel.LOW: 25.0,
    CountryRiskLevel.MODERATE: 50.0,
    CountryRiskLevel.HIGH: 75.0,
}


def compute_overall_risk(
    governance: float,
    corruption: float,
    labour_rights: float,
    environmental: float,
    human_rights: float,
) -> tuple[float, str]:
    """Compute overall risk score (0–100) and level from component scores."""
    score = (governance + corruption + labour_rights + environmental + human_rights) / 5.0
    score = max(0.0, min(100.0, score))

    if score < _RISK_THRESHOLDS[CountryRiskLevel.LOW]:
        level = CountryRiskLevel.LOW
    elif score < _RISK_THRESHOLDS[CountryRiskLevel.MODERATE]:
        level = CountryRiskLevel.MODERATE
    elif score < _RISK_THRESHOLDS[CountryRiskLevel.HIGH]:
        level = CountryRiskLevel.HIGH
    else:
        level = CountryRiskLevel.CRITICAL

    return round(score, 2), level.value


async def upsert_country_risk_profile(
    profile: CountryRiskProfile,
    session: AsyncSession,
) -> CountryRiskProfile:
    """Insert or update a CountryRiskProfile."""
    from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel

    existing_stmt = select(CountryRiskProfileModel).where(
        CountryRiskProfileModel.country_code == profile.country_code,
        CountryRiskProfileModel.dataset_id == profile.dataset_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        return _model_to_domain(existing)

    model = _domain_to_model(profile)
    session.add(model)
    await session.flush()
    return profile


async def get_country_risk(
    country_code: str,
    session: AsyncSession,
    dataset_id: str | None = None,
) -> CountryRiskProfile | None:
    """Get the most recent CountryRiskProfile for a country."""
    from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel

    stmt = (
        select(CountryRiskProfileModel)
        .where(CountryRiskProfileModel.country_code == country_code.upper())
        .order_by(CountryRiskProfileModel.created_at.desc())
    )
    if dataset_id:
        stmt = stmt.where(CountryRiskProfileModel.dataset_id == dataset_id)

    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    return _model_to_domain(row[0])


async def list_country_risks(
    session: AsyncSession,
    risk_level: str | None = None,
    limit: int = 200,
) -> list[CountryRiskProfile]:
    """List country risk profiles, optionally filtered by risk level."""
    from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel

    stmt = (
        select(CountryRiskProfileModel)
        .order_by(CountryRiskProfileModel.overall_risk_score.desc())
        .limit(limit)
    )
    if risk_level:
        stmt = stmt.where(CountryRiskProfileModel.risk_level == risk_level)

    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


def _domain_to_model(p: CountryRiskProfile):
    from infrastructure.persistence.models.external_intelligence import CountryRiskProfileModel
    return CountryRiskProfileModel(
        id=p.id,
        status=p.status.value if hasattr(p.status, "value") else p.status,
        version=p.version,
        owner=p.owner,
        created_by=p.created_by,
        updated_by=p.updated_by,
        created_at=p.created_at,
        updated_at=p.updated_at,
        country_code=p.country_code,
        country_name=p.country_name,
        dataset_id=p.dataset_id,
        governance_score=p.governance_score,
        corruption_score=p.corruption_score,
        labour_rights_score=p.labour_rights_score,
        environmental_risk_score=p.environmental_risk_score,
        human_rights_score=p.human_rights_score,
        sanctions_status=p.sanctions_status,
        overall_risk_score=p.overall_risk_score,
        risk_level=p.risk_level,
        source_name=p.source_name,
        source_version=p.source_version,
        data_date=p.data_date,
    )


def _model_to_domain(m) -> CountryRiskProfile:
    return CountryRiskProfile(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        country_code=m.country_code,
        country_name=m.country_name,
        dataset_id=m.dataset_id,
        governance_score=m.governance_score or 0.0,
        corruption_score=m.corruption_score or 0.0,
        labour_rights_score=m.labour_rights_score or 0.0,
        environmental_risk_score=m.environmental_risk_score or 0.0,
        human_rights_score=m.human_rights_score or 0.0,
        sanctions_status=m.sanctions_status or "none",
        overall_risk_score=m.overall_risk_score or 0.0,
        risk_level=m.risk_level or CountryRiskLevel.LOW,
        source_name=m.source_name or "",
        source_version=m.source_version or "",
        data_date=m.data_date or "",
    )
