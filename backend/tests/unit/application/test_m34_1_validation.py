"""M34.1 Tests — DatasetValidationService."""

from __future__ import annotations

import hashlib
import json

import pytest

from application.external_intelligence.base_adapter import RawDataset
from application.external_intelligence.validation_service import (
    ValidationResult,
    validate_dataset,
    _recompute_hash,
)
from domain.enums import ExternalSourceName


def _make_raw(records: list[dict], source: str = "world_bank") -> RawDataset:
    return RawDataset(
        source_name=ExternalSourceName(source) if source in [e.value for e in ExternalSourceName] else source,
        source_version="2025-01",
        records=records,
    )


def _good_records(n: int = 60) -> list[dict]:
    return [
        {"country_code": f"C{i:02d}", "governance_score": float(i), "corruption_score": float(i)}
        for i in range(n)
    ]


# ── Passing validation ──────────────────────────────────────────────────────


def test_valid_dataset_passes():
    raw = _make_raw(_good_records(60))
    result = validate_dataset(raw)
    assert result.is_valid is True
    assert result.errors == []


def test_valid_dataset_row_count():
    records = _good_records(60)
    raw = _make_raw(records)
    result = validate_dataset(raw)
    assert result.row_count == 60


# ── Empty dataset ───────────────────────────────────────────────────────────


def test_empty_dataset_invalid():
    raw = _make_raw([])
    result = validate_dataset(raw)
    assert result.is_valid is False
    assert any("empty" in e.lower() for e in result.errors)


# ── Minimum row count ───────────────────────────────────────────────────────


def test_below_minimum_rows_invalid():
    raw = _make_raw(_good_records(10))  # world_bank min is 50
    result = validate_dataset(raw)
    assert result.is_valid is False
    assert any("minimum" in e.lower() or "below" in e.lower() for e in result.errors)


def test_at_minimum_rows_valid():
    raw = _make_raw(_good_records(50))
    result = validate_dataset(raw)
    assert result.is_valid is True


# ── Required fields ─────────────────────────────────────────────────────────


def test_missing_required_field_fails():
    records = [{"country_code": "DE"} for _ in range(60)]  # missing governance_score, corruption_score
    raw = _make_raw(records)
    result = validate_dataset(raw)
    assert result.is_valid is False
    assert any("missing" in e.lower() for e in result.errors)


# ── Duplicates ──────────────────────────────────────────────────────────────


def test_duplicate_rows_high_pct_fails():
    record = {"country_code": "US", "governance_score": 50.0, "corruption_score": 30.0}
    records = [record] * 60  # 100% duplicates
    raw = _make_raw(records)
    result = validate_dataset(raw)
    assert result.is_valid is False
    assert result.duplicate_count > 0


def test_few_duplicate_rows_warning_not_error():
    records = _good_records(60)
    # Add 1 duplicate (< 10%)
    records.append(records[0].copy())
    raw = _make_raw(records)
    result = validate_dataset(raw)
    assert result.duplicate_count == 1
    # 1/61 ≈ 1.6% → warning only, not error
    assert any("duplicate" in w.lower() for w in result.warnings)


# ── Hash consistency ────────────────────────────────────────────────────────


def test_hash_consistency_valid_dataset():
    records = _good_records(60)
    raw = _make_raw(records)
    recomputed = _recompute_hash(records)
    assert raw.dataset_hash == recomputed  # RawDataset.dataset_hash must match


def test_hash_mismatch_fails(monkeypatch):
    records = _good_records(60)
    raw = _make_raw(records)
    # Tamper with the stored hash
    object.__setattr__(raw, "_hash_override", "tampered")

    # Patch dataset_hash property to return tampered value
    original_hash = raw.dataset_hash
    # Rebuild with records that differ
    raw2 = RawDataset(
        source_name=ExternalSourceName.WORLD_BANK,
        source_version="v1",
        records=records,
    )
    # Manually mess up via monkey-patching
    with pytest.MonkeyPatch().context() as m:
        m.setattr(type(raw2), "dataset_hash", property(lambda self: "badhash000"), raising=False)
        result = validate_dataset(raw2)
    assert result.is_valid is False


# ── Source without required fields definition ────────────────────────────────


def test_source_without_required_fields_passes():
    """Sources not in _REQUIRED_FIELDS should pass field check."""
    records = [{"anything": "value"} for _ in range(5)]
    raw = RawDataset(
        source_name="unknown_source",
        source_version="v1",
        records=records,
    )
    result = validate_dataset(raw)
    # No required-field errors (min row threshold still applies for unknown → 1)
    field_errors = [e for e in result.errors if "missing" in e.lower()]
    assert field_errors == []
