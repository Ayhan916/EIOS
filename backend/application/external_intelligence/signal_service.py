"""Adverse Risk Signal Service — M34.

Manages ExternalRiskSignals: creation, querying by supplier/country/sector,
and deactivation when a signal is resolved.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.external_intelligence import ExternalRiskSignal

from .event_attribution import derive_esg_category, derive_protected_right


async def create_signal(
    signal: ExternalRiskSignal,
    session: AsyncSession,
) -> ExternalRiskSignal:
    """Persist a new ExternalRiskSignal.

    Auto-derives esg_category and protected_right from signal_type when not
    explicitly provided (deterministic mapping, GAP-10).
    """
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    sig_type_str = (
        signal.signal_type.value if hasattr(signal.signal_type, "value") else signal.signal_type
    )
    if not signal.esg_category:
        signal.esg_category = derive_esg_category(sig_type_str)
    if not signal.protected_right:
        signal.protected_right = derive_protected_right(sig_type_str)

    # Compute frequency: count matching active signals for same scope+type in last 12 months
    from datetime import timedelta

    from infrastructure.persistence.models.external_intelligence import (
        ExternalRiskSignalModel as _M,
    )

    signal.observed_at.replace(tzinfo=None) if signal.observed_at.tzinfo else signal.observed_at
    cutoff_utc = (
        signal.observed_at.astimezone(UTC)
        if signal.observed_at.tzinfo
        else signal.observed_at.replace(tzinfo=UTC)
    )
    twelve_months_ago = cutoff_utc - timedelta(days=365)
    freq_stmt = (
        sa_select(func.count())
        .select_from(_M)
        .where(
            _M.signal_type == sig_type_str,
            _M.is_active.is_(True),
            _M.observed_at >= twelve_months_ago,
        )
    )
    if signal.supplier_id:
        freq_stmt = freq_stmt.where(_M.supplier_id == signal.supplier_id)
    elif signal.country_code:
        freq_stmt = freq_stmt.where(_M.country_code == signal.country_code)
    signal.frequency = (await session.execute(freq_stmt)).scalar_one() or 0

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
        esg_category=s.esg_category,
        protected_right=s.protected_right,
        frequency=s.frequency,
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
        esg_category=getattr(m, "esg_category", None),
        protected_right=getattr(m, "protected_right", None),
        frequency=getattr(m, "frequency", 0) or 0,
    )
