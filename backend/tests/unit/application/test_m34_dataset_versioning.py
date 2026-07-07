"""M34 dataset versioning tests.

Ingesting a new version of the same source must:
  1. Mark all ACTIVE records for that source as SUPERSEDED
  2. Insert new dataset with status ACTIVE
  3. Idempotent: ingesting the same hash a second time returns existing record
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.external_intelligence.base_adapter import RawDataset
from application.external_intelligence.dataset_service import (
    get_active_dataset,
    ingest_dataset,
    list_datasets,
)
from domain.enums import DatasetStatus, ExternalSourceName


def _now():
    return datetime.now(UTC)


def _make_raw(source_version="2025-Q1", records=None):
    return RawDataset(
        source_name=ExternalSourceName.WORLD_BANK,
        source_version=source_version,
        records=records or [{"country": "DE", "score": 85}],
        description="World Bank",
    )


def _make_dataset_model(dataset_hash="hash123", dataset_status="active"):
    m = MagicMock()
    m.id = "ds-001"
    m.status = "Active"
    m.version = 1
    m.owner = None
    m.created_by = None
    m.updated_by = None
    m.created_at = _now()
    m.updated_at = _now()
    m.source_name = "world_bank"
    m.source_version = "2025-Q1"
    m.dataset_hash = dataset_hash
    m.imported_at = _now()
    m.row_count = 1
    m.dataset_status = dataset_status
    m.description = "World Bank"
    return m


# ── ingest_dataset ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ingest_creates_new_dataset():
    """Fresh source — no prior active → creates new ACTIVE dataset."""
    raw = _make_raw()
    session = AsyncMock()
    # First call: check existing by hash → None
    # Second call: check active by source → None
    no_result = MagicMock()
    no_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=no_result)
    session.flush = AsyncMock()

    dataset = await ingest_dataset(raw, session)
    assert dataset is not None
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_same_hash_is_idempotent():
    """Ingesting same hash twice returns existing record without re-inserting."""
    raw = _make_raw()
    session = AsyncMock()
    existing = _make_dataset_model(dataset_hash=raw.dataset_hash)

    found = MagicMock()
    found.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=found)

    dataset = await ingest_dataset(raw, session)
    assert dataset.dataset_hash == raw.dataset_hash
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_new_version_supersedes_active():
    """New version of same source → prior ACTIVE becomes SUPERSEDED."""
    raw_v2 = _make_raw(source_version="2025-Q2", records=[{"country": "DE", "score": 90}])
    session = AsyncMock()

    # First execute: check existing by source+version → None (new version)
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None

    # Second execute: find active datasets → list with prior active
    prior_active = _make_dataset_model(dataset_hash="old_hash", dataset_status="active")
    has_active = MagicMock()
    has_active.scalars.return_value.all.return_value = [prior_active]

    session.execute = AsyncMock(side_effect=[no_existing, has_active])
    session.flush = AsyncMock()

    dataset = await ingest_dataset(raw_v2, session)
    assert dataset is not None
    # Prior active model should have been updated to superseded
    assert prior_active.dataset_status == DatasetStatus.SUPERSEDED.value


# ── get_active_dataset ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_active_dataset_returns_active():
    active = _make_dataset_model(dataset_status="active")
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = active
    session.execute = AsyncMock(return_value=result)

    ds = await get_active_dataset(ExternalSourceName.WORLD_BANK, session)
    assert ds is not None
    assert ds.dataset_status == "active"


@pytest.mark.asyncio
async def test_get_active_dataset_none_when_missing():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    ds = await get_active_dataset(ExternalSourceName.WORLD_BANK, session)
    assert ds is None


# ── list_datasets ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_datasets_returns_all():
    models = [
        _make_dataset_model(dataset_hash="h1", dataset_status="active"),
        _make_dataset_model(dataset_hash="h2", dataset_status="superseded"),
    ]
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = models
    session.execute = AsyncMock(return_value=result)

    datasets = await list_datasets(session)
    assert len(datasets) == 2


@pytest.mark.asyncio
async def test_list_datasets_filtered_by_status():
    active = _make_dataset_model(dataset_hash="h1", dataset_status="active")
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [active]
    session.execute = AsyncMock(return_value=result)

    datasets = await list_datasets(session, status="active")
    assert len(datasets) == 1
    assert datasets[0].dataset_status == "active"
