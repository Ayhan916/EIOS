"""BaseLiveConnector — M34.1 / M34.2.

Standard interface all external data source connectors must implement.
Each connector is responsible for:
  fetch()     — retrieve raw records from the external source
  normalize() — transform raw records into a typed RawDataset
  validate()  — check schema integrity, required fields, duplicates
  ingest()    — persist via the M34 dataset versioning pipeline

The run() method orchestrates all four steps, records a ConnectorRun,
and wraps the pipeline in exponential-backoff retry logic.

M34.2 hardening:
  - H1: result.success is False when validation_errors is non-empty (quarantined)
  - H2/M3: validate_dataset() called before ingest; result persisted
  - H4: DB-backed concurrency guard (status='running' lock)
  - M2: trigger_source passed through to connector_runs
  - M4: dataset_refresh_total always incremented (success and failure)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset

logger = structlog.get_logger(__name__)

_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 2.0


@dataclass
class ConnectorRunResult:
    """Outcome of a single connector execution."""

    connector_name: str
    connector_version: str
    started_at: datetime
    completed_at: datetime
    runtime_seconds: float
    dataset_hash: str | None = None
    dataset_id: str | None = None
    row_count: int = 0
    success: bool = False
    error_message: str | None = None
    retry_count: int = 0
    validation_errors: list[str] = field(default_factory=list)


async def run_with_retry(
    coro_factory,
    max_retries: int = _MAX_RETRIES,
    base_delay: float = _BASE_DELAY_SECONDS,
    connector_name: str = "unknown",
) -> Any:
    """Execute an async coroutine factory with exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(max(max_retries, 1)):
        try:
            return await coro_factory()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "connector_retry",
                    connector=connector_name,
                    attempt=attempt + 1,
                    delay_seconds=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "connector_failed_all_retries",
                    connector=connector_name,
                    attempts=max_retries,
                    error=str(exc),
                )
    raise last_error  # type: ignore[misc]


class BaseLiveConnector(ABC):
    """Abstract base class every M34.1 live connector must implement."""

    connector_name: str
    connector_version: str = "1.0"
    refresh_cadence_hours: int = 24 * 30

    @abstractmethod
    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Fetch raw records from the external source."""

    @abstractmethod
    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Transform raw records into a normalised RawDataset."""

    def validate(self, raw: RawDataset) -> list[str]:
        """Return validation error strings (empty list = valid).

        Subclasses may override to add source-specific checks.
        """
        errors: list[str] = []
        if raw.row_count == 0:
            errors.append("Dataset is empty — no records ingested")
        seen: set[str] = set()
        import json
        for record in raw.records:
            key = json.dumps(record, sort_keys=True, default=str)
            if key in seen:
                errors.append(f"Duplicate record detected: {key[:80]}")
                break
            seen.add(key)
        return errors

    async def ingest(
        self,
        session: Any,
        client: Any | None = None,
    ) -> tuple[Any, list[str]]:
        """Full pipeline: fetch → validate → normalize → persist.

        H2: Calls validation_service.validate_dataset() before ingest.
        M3: Persists ValidationResult to dataset_validation_results.

        Returns:
            (ExternalDataset, validation_errors) — dataset is QUARANTINED
            if validation_errors is non-empty.
        """
        from application.external_intelligence.dataset_service import ingest_dataset
        from application.external_intelligence.validation_service import (
            validate_dataset,
            validate_and_persist_result,
        )
        from domain.enums import DatasetStatus

        import httpx

        _client = client
        _own_client = False
        if _client is None:
            _client = httpx.AsyncClient(timeout=30.0)
            _own_client = True

        try:
            raw_records = await self.fetch(_client)
            raw = self.normalize(raw_records)

            # H2: full validation service check
            pre_validation = validate_dataset(raw)
            errors = pre_validation.errors

            # Merge with connector-specific checks
            connector_errors = self.validate(raw)
            for e in connector_errors:
                if e not in errors:
                    errors.append(e)

            if errors:
                raw.description = f"[QUARANTINED] {raw.description}. Errors: {'; '.join(errors)}"
                logger.warning(
                    "connector_validation_failed",
                    connector=self.connector_name,
                    error_count=len(errors),
                    errors=errors[:3],
                )

            dataset = await ingest_dataset(raw, session)

            # M3: persist validation result
            pre_validation.errors = errors
            pre_validation.is_valid = len(errors) == 0
            await validate_and_persist_result(pre_validation, dataset.id, session)

            if errors:
                dataset.dataset_status = DatasetStatus.QUARANTINED
                from infrastructure.persistence.models.external_intelligence import ExternalDatasetModel
                from sqlalchemy import update
                stmt = (
                    update(ExternalDatasetModel)
                    .where(ExternalDatasetModel.id == dataset.id)
                    .values(dataset_status=DatasetStatus.QUARANTINED.value)
                )
                await session.execute(stmt)

            return dataset, errors
        finally:
            if _own_client:
                await _client.aclose()

    async def run(
        self,
        session: Any,
        client: Any | None = None,
        max_retries: int = _MAX_RETRIES,
        trigger_source: str = "scheduler",
    ) -> ConnectorRunResult:
        """Execute with retry, concurrency guard, and record the outcome.

        H4: Acquires a DB-backed running lock before starting; releases on completion.
        M2: Passes trigger_source to the connector_runs audit record.
        M4: Always increments dataset_refresh_total regardless of outcome.
        """
        from application.external_intelligence.metrics import ext_counters

        started_at = datetime.now(UTC)

        # H4: concurrency guard — abort if already running
        existing_run_id = await _check_concurrent_run(self.connector_name, session)
        if existing_run_id:
            logger.warning(
                "connector_already_running",
                connector=self.connector_name,
                existing_run_id=existing_run_id,
            )
            completed_at = datetime.now(UTC)
            return ConnectorRunResult(
                connector_name=self.connector_name,
                connector_version=self.connector_version,
                started_at=started_at,
                completed_at=completed_at,
                runtime_seconds=(completed_at - started_at).total_seconds(),
                success=False,
                error_message="Connector already running",
            )

        # H4: acquire running lock
        run_lock_id = await _acquire_running_lock(
            self.connector_name, self.connector_version, started_at, trigger_source, session
        )

        async def _attempt():
            return await self.ingest(session, client)

        error_msg: str | None = None
        dataset = None
        validation_errors: list[str] = []
        retry_count = 0

        try:
            for attempt in range(max(max_retries, 1)):
                try:
                    dataset, validation_errors = await _attempt()
                    retry_count = attempt
                    break
                except Exception as exc:
                    if attempt < max(max_retries, 1) - 1:
                        delay = _BASE_DELAY_SECONDS * (2 ** attempt)
                        logger.warning(
                            "connector_retry",
                            connector=self.connector_name,
                            attempt=attempt + 1,
                            delay=delay,
                            error=str(exc),
                        )
                        await asyncio.sleep(delay)
                        retry_count = attempt + 1
                    else:
                        raise
        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                "connector_run_failed",
                connector=self.connector_name,
                error=error_msg,
            )

        completed_at = datetime.now(UTC)
        runtime = (completed_at - started_at).total_seconds()

        # H1: success requires dataset, no error, AND no validation errors (not quarantined)
        is_success = (
            dataset is not None
            and error_msg is None
            and not validation_errors
        )

        # M4: always increment total; failures also increment failed_total
        ext_counters.record_dataset_refresh(self.connector_name, success=is_success)
        if not is_success:
            ext_counters.record_connector_failure(self.connector_name)
        ext_counters.record_connector_runtime(self.connector_name, runtime)

        result = ConnectorRunResult(
            connector_name=self.connector_name,
            connector_version=self.connector_version,
            started_at=started_at,
            completed_at=completed_at,
            runtime_seconds=runtime,
            dataset_hash=dataset.dataset_hash if dataset else None,
            dataset_id=dataset.id if dataset else None,
            row_count=dataset.row_count if dataset else 0,
            success=is_success,
            error_message=error_msg,
            retry_count=retry_count,
            validation_errors=validation_errors,
        )

        await _record_run(result, session, trigger_source=trigger_source, run_lock_id=run_lock_id)
        return result


async def _check_concurrent_run(connector_name: str, session: Any) -> str | None:
    """Return the ID of an in-progress run if one exists, else None."""
    from infrastructure.persistence.models.connector_run import ConnectorRunModel
    from sqlalchemy import select

    stmt = (
        select(ConnectorRunModel)
        .where(
            ConnectorRunModel.connector_name == connector_name,
            ConnectorRunModel.status == "running",
        )
        .limit(1)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    return row.id if row else None


async def _acquire_running_lock(
    connector_name: str,
    connector_version: str,
    started_at: datetime,
    trigger_source: str,
    session: Any,
) -> str:
    """Insert a status='running' row and return its ID."""
    import uuid
    from infrastructure.persistence.models.connector_run import ConnectorRunModel

    lock_id = str(uuid.uuid4())
    model = ConnectorRunModel(
        id=lock_id,
        connector_name=connector_name,
        connector_version=connector_version,
        status="running",
        started_at=started_at,
        completed_at=None,
        runtime_seconds=None,
        dataset_id=None,
        error_message=None,
        row_count=0,
        retry_count=0,
        validation_errors_json="[]",
        trigger_source=trigger_source,
        initiated_by_user_id=None,
        created_at=started_at,
        updated_at=started_at,
    )
    session.add(model)
    try:
        await session.flush()
    except Exception:
        pass
    return lock_id


async def _record_run(
    result: ConnectorRunResult,
    session: Any,
    trigger_source: str = "scheduler",
    run_lock_id: str | None = None,
) -> None:
    """Update the running lock row to final status (or insert if lock failed)."""
    from infrastructure.persistence.models.connector_run import ConnectorRunModel
    from domain.enums import ConnectorStatus
    import json

    status = ConnectorStatus.HEALTHY if result.success else ConnectorStatus.FAILED
    if result.success and result.retry_count > 0:
        status = ConnectorStatus.DEGRADED

    if run_lock_id:
        from sqlalchemy import update
        stmt = (
            update(ConnectorRunModel)
            .where(ConnectorRunModel.id == run_lock_id)
            .values(
                status=status.value,
                completed_at=result.completed_at,
                runtime_seconds=result.runtime_seconds,
                dataset_id=result.dataset_id or None,
                dataset_hash=result.dataset_hash or None,
                row_count=result.row_count,
                retry_count=result.retry_count,
                error_message=result.error_message or None,
                validation_errors_json=json.dumps(result.validation_errors),
                trigger_source=trigger_source,
                updated_at=result.completed_at,
            )
        )
        try:
            await session.execute(stmt)
            await session.flush()
        except Exception:
            pass
    else:
        import uuid
        model = ConnectorRunModel(
            id=str(uuid.uuid4()),
            connector_name=result.connector_name,
            connector_version=result.connector_version,
            status=status.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            runtime_seconds=result.runtime_seconds,
            dataset_id=result.dataset_id or None,
            error_message=result.error_message or None,
            row_count=result.row_count,
            retry_count=result.retry_count,
            validation_errors_json=json.dumps(result.validation_errors),
            trigger_source=trigger_source,
            initiated_by_user_id=None,
            created_at=result.started_at,
            updated_at=result.completed_at,
        )
        session.add(model)
        try:
            await session.flush()
        except Exception:
            pass
