"""Adverse Risk Signal Service — M34.

Manages ExternalRiskSignals: creation, querying by supplier/country/sector,
and deactivation when a signal is resolved.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus
from domain.external_intelligence import ExternalRiskSignal


async def create_signal(
    signal: ExternalRiskSignal,
    session: AsyncSession,
) -> ExternalRiskSignal:
    """Persist a new ExternalRiskSignal."""
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel

    model = _domain_to_model(signal)
    session.add(model)
    await session.flush()
    return signal


async def list_signals_for_supplier(
    supplier_id: str,
    organization_id: str,
    session: AsyncSession,
    active_only: bool = True,
) -> list[ExternalRiskSignal]:
    """Return all risk signals linked to a supplier."""
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel

    stmt = select(ExternalRiskSignalModel).where(
        ExternalRiskSignalModel.supplier_id == supplier_id,
        ExternalRiskSignalModel.organization_id == organization_id,
    )
    if active_only:
        stmt = stmt.where(ExternalRiskSignalModel.is_active.is_(True))

    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


async def list_signals_for_country(
    country_code: str,
    session: AsyncSession,
    active_only: bool = True,
) -> list[ExternalRiskSignal]:
    """Return all risk signals for a country (global-level signals)."""
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel

    stmt = select(ExternalRiskSignalModel).where(
        ExternalRiskSignalModel.country_code == country_code.upper(),
    )
    if active_only:
        stmt = stmt.where(ExternalRiskSignalModel.is_active.is_(True))

    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


async def list_active_signals(
    session: AsyncSession,
    signal_type: str | None = None,
    severity: str | None = None,
    organization_id: str | None = None,
    limit: int = 100,
) -> list[ExternalRiskSignal]:
    """List active signals with optional filters."""
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel

    stmt = (
        select(ExternalRiskSignalModel)
        .where(ExternalRiskSignalModel.is_active.is_(True))
        .order_by(ExternalRiskSignalModel.observed_at.desc())
        .limit(limit)
    )
    if signal_type:
        stmt = stmt.where(ExternalRiskSignalModel.signal_type == signal_type)
    if severity:
        stmt = stmt.where(ExternalRiskSignalModel.severity == severity)
    if organization_id:
        stmt = stmt.where(ExternalRiskSignalModel.organization_id == organization_id)

    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


def _domain_to_model(s: ExternalRiskSignal):
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel
    return ExternalRiskSignalModel(
        id=s.id,
        status=s.status.value if hasattr(s.status, "value") else s.status,
        version=s.version,
        owner=s.owner,
        created_by=s.created_by,
        updated_by=s.updated_by,
        created_at=s.created_at,
        updated_at=s.updated_at,
        signal_type=s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type,
        severity=s.severity.value if hasattr(s.severity, "value") else s.severity,
        description=s.description,
        source_name=s.source_name,
        source_version=s.source_version,
        observed_at=s.observed_at,
        dataset_id=s.dataset_id or None,
        country_code=s.country_code or "",
        sector_code=s.sector_code or "",
        supplier_id=s.supplier_id or "",
        organization_id=s.organization_id or "",
        is_active=s.is_active,
    )


def _model_to_domain(m) -> ExternalRiskSignal:
    return ExternalRiskSignal(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        signal_type=m.signal_type,
        severity=m.severity,
        description=m.description,
        source_name=m.source_name,
        source_version=m.source_version,
        observed_at=m.observed_at,
        dataset_id=m.dataset_id or "",
        country_code=m.country_code or "",
        sector_code=m.sector_code or "",
        supplier_id=m.supplier_id or "",
        organization_id=m.organization_id or "",
        is_active=bool(m.is_active),
    )
