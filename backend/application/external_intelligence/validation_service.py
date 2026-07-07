"""Dataset Validation Service — M34.1.

Validates ExternalDatasets before activation. Invalid or suspect datasets
are quarantined and never made ACTIVE.

Checks:
  - Empty dataset (row_count == 0)
  - Missing required fields per source type
  - Duplicate rows (canonical JSON comparison)
  - Hash consistency (recomputed hash must match stored hash)
  - Minimum row count thresholds per source
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from application.external_intelligence.base_adapter import RawDataset
from application.external_intelligence.metrics import ext_counters

logger = structlog.get_logger(__name__)

_MIN_ROW_COUNTS: dict[str, int] = {
    "world_bank": 50,
    "transparency_international": 30,
    "ilo": 10,
    "unicef": 10,
    "un_sanctions": 1,
    "eu_sanctions": 1,
    "sector_esg_benchmark": 1,
    "sector_risk_classification": 1,
}

_REQUIRED_FIELDS: dict[str, set[str]] = {
    "world_bank": {"country_code", "governance_score", "corruption_score"},
    "transparency_international": {"country_code", "corruption_score"},
    "ilo": {"country_code", "labour_rights_score"},
    "unicef": {"country_code", "human_rights_score"},
    "un_sanctions": {"signal_type", "description"},
    "eu_sanctions": {"signal_type", "description"},
}


@dataclass
class ValidationResult:
    """Outcome of validating a RawDataset before ingestion."""

    dataset_id: str
    source_name: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    duplicate_count: int = 0
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def validate_dataset(raw: RawDataset) -> ValidationResult:
    """Validate a RawDataset. Returns a ValidationResult with errors/warnings.

    This is a pure function — no DB access. Call before ingest_dataset().
    """
    errors: list[str] = []
    warnings: list[str] = []
    source = raw.source_name if isinstance(raw.source_name, str) else raw.source_name.value

    # ── 1. Empty check ────────────────────────────────────────────────────────
    if raw.row_count == 0:
        errors.append("Dataset is empty — no records received from source")

    # ── 2. Minimum row count ──────────────────────────────────────────────────
    min_rows = _MIN_ROW_COUNTS.get(source, 1)
    if 0 < raw.row_count < min_rows:
        errors.append(f"Row count {raw.row_count} below minimum {min_rows} for source '{source}'")

    # ── 3. Required fields ────────────────────────────────────────────────────
    required = _REQUIRED_FIELDS.get(source, set())
    if required and raw.records:
        for idx, record in enumerate(raw.records[:20]):
            missing = required - set(record.keys())
            if missing:
                errors.append(f"Record {idx} missing required fields: {sorted(missing)}")
                break

    # ── 4. Duplicate detection ────────────────────────────────────────────────
    seen: set[str] = set()
    duplicate_count = 0
    for record in raw.records:
        key = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        if key in seen:
            duplicate_count += 1
        else:
            seen.add(key)

    if duplicate_count > 0:
        pct = duplicate_count / max(raw.row_count, 1) * 100
        if pct > 10:
            errors.append(f"{duplicate_count} duplicate records ({pct:.0f}% of dataset)")
        else:
            warnings.append(f"{duplicate_count} duplicate records detected")

    # ── 5. Hash consistency ───────────────────────────────────────────────────
    recomputed = _recompute_hash(raw.records)
    if recomputed != raw.dataset_hash:
        errors.append(
            f"Hash mismatch — stored={raw.dataset_hash[:16]}… recomputed={recomputed[:16]}…"
        )

    is_valid = len(errors) == 0
    if not is_valid:
        ext_counters.record_validation_failure(quarantined=True)
        logger.warning(
            "dataset_validation_failed",
            source=source,
            errors=errors,
            warnings=warnings,
        )
    elif warnings:
        logger.info("dataset_validation_warnings", source=source, warnings=warnings)

    return ValidationResult(
        dataset_id="",  # assigned after ingestion
        source_name=source,
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        row_count=raw.row_count,
        duplicate_count=duplicate_count,
    )


async def validate_and_persist_result(
    validation: ValidationResult,
    dataset_id: str,
    session,
) -> None:
    """Persist a ValidationResult to dataset_validation_results table."""
    import uuid

    from infrastructure.persistence.models.connector_run import DatasetValidationResultModel

    validation.dataset_id = dataset_id
    model = DatasetValidationResultModel(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        is_valid=validation.is_valid,
        errors_json=json.dumps(validation.errors),
        warnings_json=json.dumps(validation.warnings),
        row_count=validation.row_count,
        duplicate_count=validation.duplicate_count,
        validated_at=validation.validated_at,
        created_at=validation.validated_at,
        updated_at=validation.validated_at,
    )
    session.add(model)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("validation_result_persist_failed", error=str(exc))


def _recompute_hash(records: list[dict]) -> str:
    """Recompute the canonical hash of a list of records."""
    row_strings = sorted(
        json.dumps(r, sort_keys=True, separators=(",", ":"), default=str) for r in records
    )
    canonical = json.dumps(row_strings, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
