"""M34 dataset hash integrity tests.

Dataset hash is SHA-256 of canonical JSON of raw records.
Changing any field must produce a different hash.
Order of records must not matter (sorted by canonical JSON).
"""

import hashlib
import json
import pytest

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName


def _canonical_hash(records: list[dict]) -> str:
    payload = sorted(
        [json.dumps(r, sort_keys=True, separators=(",", ":"), default=str) for r in records]
    )
    data = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


# ── RawDataset.dataset_hash ────────────────────────────────────────────────────

class TestDatasetHash:
    def _make(self, records):
        return RawDataset(
            source_name=ExternalSourceName.WORLD_BANK,
            source_version="2025-Q1",
            records=records,
            description="Test dataset",
        )

    def test_hash_is_64_hex_chars(self):
        ds = self._make([{"country": "DE", "score": 85}])
        assert len(ds.dataset_hash) == 64
        assert all(c in "0123456789abcdef" for c in ds.dataset_hash)

    def test_same_records_same_hash(self):
        records = [{"country": "DE", "score": 85}, {"country": "FR", "score": 70}]
        h1 = self._make(records).dataset_hash
        h2 = self._make(records).dataset_hash
        assert h1 == h2

    def test_different_records_different_hash(self):
        r1 = [{"country": "DE", "score": 85}]
        r2 = [{"country": "DE", "score": 90}]  # changed score
        assert self._make(r1).dataset_hash != self._make(r2).dataset_hash

    def test_order_independent(self):
        r_forward = [{"country": "DE", "score": 85}, {"country": "FR", "score": 70}]
        r_reversed = [{"country": "FR", "score": 70}, {"country": "DE", "score": 85}]
        assert self._make(r_forward).dataset_hash == self._make(r_reversed).dataset_hash

    def test_empty_records_has_stable_hash(self):
        ds = self._make([])
        assert len(ds.dataset_hash) == 64

    def test_adding_record_changes_hash(self):
        r1 = [{"country": "DE", "score": 85}]
        r2 = [{"country": "DE", "score": 85}, {"country": "FR", "score": 70}]
        assert self._make(r1).dataset_hash != self._make(r2).dataset_hash

    def test_key_rename_changes_hash(self):
        r1 = [{"country": "DE", "score": 85}]
        r2 = [{"Country": "DE", "score": 85}]  # capital C — different key
        assert self._make(r1).dataset_hash != self._make(r2).dataset_hash

    def test_hash_matches_manual_calculation(self):
        records = [{"country": "DE", "score": 85}]
        ds = self._make(records)
        expected = _canonical_hash(records)
        assert ds.dataset_hash == expected

    def test_row_count_from_records(self):
        records = [{"a": 1}, {"a": 2}, {"a": 3}]
        ds = self._make(records)
        assert ds.row_count == 3

    def test_empty_row_count(self):
        ds = self._make([])
        assert ds.row_count == 0
