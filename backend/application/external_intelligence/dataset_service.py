"""External Dataset Management Service — M34.

Responsible for ingesting, versioning, and cataloguing external datasets.
Datasets are immutable once stored — a new version creates a new record,
and the previous version is marked SUPERSEDED.

All datasets carry a SHA-256 hash of their canonical content, enabling
tamper detection and historical reproducibility.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import DatasetStatus, EntityStatus
from domain.external_intelligence import ExternalDataset

from .base_adapter import RawDataset

logger = structlog.get_logger(__name__)


async def ingest_dataset(
    raw: RawDataset,
    session: AsyncSession,
) -> ExternalDataset:
    """Persist a RawDataset as a versioned ExternalDataset.

    If a dataset with the same source_name and source_version already exists,
    it is returned as-is (idempotent). Otherwise, the previous ACTIVE dataset
    for the same source is marked SUPERSEDED before the new one is created.
    """
    from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel

    # Idempotency: same source + version already ingested?
    existing_stmt = select(ExternalDatasetModel).where(
        ExternalDatasetModel.source_name == raw.source_name,
        ExternalDatasetModel.source_version == raw.source_version,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        logger.info(
            "dataset_already_ingested",
            source=raw.source_name,
            version=raw.source_version,
            id=existing.id,
        )
        return _model_to_domain(existing)

    # Supersede previous active dataset for this source
    prev_stmt = select(ExternalDatasetModel).where(
        ExternalDatasetModel.source_name == raw.source_name,
        ExternalDatasetModel.dataset_status == DatasetStatus.ACTIVE,
    )
    prev_rows = (await session.execute(prev_stmt)).scalars().all()
    for prev in prev_rows:
        prev.dataset_status = DatasetStatus.SUPERSEDED
        prev.updated_at = datetime.now(UTC)
        session.add(prev)

    dataset = ExternalDataset(
        source_name=raw.source_name,
        source_version=raw.source_version,
        dataset_hash=raw.dataset_hash,
        imported_at=datetime.now(UTC),
        row_count=raw.row_count,
        dataset_status=DatasetStatus.ACTIVE,
        description=raw.description,
        status=EntityStatus.ACTIVE,
    )
    model = _domain_to_model(dataset)
    session.add(model)
    await session.flush()

    logger.info(
        "dataset_ingested",
        source=raw.source_name,
        version=raw.source_version,
        rows=raw.row_count,
        hash=raw.dataset_hash[:16],
    )
    return dataset


async def get_active_dataset(
    source_name: str,
    session: AsyncSession,
) -> ExternalDataset | None:
    """Return the currently ACTIVE dataset for a given source."""
    from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel

    stmt = select(ExternalDatasetModel).where(
        ExternalDatasetModel.source_name == source_name,
        ExternalDatasetModel.dataset_status == DatasetStatus.ACTIVE,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return _model_to_domain(row) if row else None


async def list_datasets(
    session: AsyncSession,
    source_name: str | None = None,
    status: str | None = None,
) -> list[ExternalDataset]:
    """List all datasets, optionally filtered by source or status."""
    from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel

    stmt = select(ExternalDatasetModel).order_by(ExternalDatasetModel.imported_at.desc())
    if source_name:
        stmt = stmt.where(ExternalDatasetModel.source_name == source_name)
    if status:
        stmt = stmt.where(ExternalDatasetModel.dataset_status == status)

    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


def _domain_to_model(d: ExternalDataset):
    from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel

    return ExternalDatasetModel(
        id=d.id,
        status=d.status.value if hasattr(d.status, "value") else d.status,
        version=d.version,
        owner=d.owner,
        created_by=d.created_by,
        updated_by=d.updated_by,
        created_at=d.created_at,
        updated_at=d.updated_at,
        source_name=d.source_name,
        source_version=d.source_version,
        dataset_hash=d.dataset_hash,
        imported_at=d.imported_at,
        row_count=d.row_count,
        dataset_status=d.dataset_status.value
        if hasattr(d.dataset_status, "value")
        else d.dataset_status,
        description=d.description,
    )


def _model_to_domain(m) -> ExternalDataset:
    return ExternalDataset(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        source_name=m.source_name,
        source_version=m.source_version,
        dataset_hash=m.dataset_hash,
        imported_at=m.imported_at,
        row_count=m.row_count or 0,
        dataset_status=m.dataset_status,
        description=m.description or "",
    )
