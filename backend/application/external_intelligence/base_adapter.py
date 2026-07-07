"""Abstract base class for external data source adapters — M34.

Each external source (World Bank, TI-CPI, ILO, etc.) implements this
interface. The adapter is responsible for fetching or loading raw data
and returning it in a normalised, source-attributed structure.

Adapters are stateless — they receive configuration at call time and
return data without persisting anything.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class RawDataset:
    """Normalised output from any external adapter."""

    source_name: str
    source_version: str
    records: list[dict] = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    description: str = ""

    @property
    def dataset_hash(self) -> str:
        """SHA-256 of sorted canonical JSON strings of all records.

        Order-independent: the list is sorted before hashing so that
        ingesting the same records in different orderings yields the
        same hash.
        """
        row_strings = sorted(
            json.dumps(r, sort_keys=True, separators=(",", ":"), default=str) for r in self.records
        )
        canonical = json.dumps(row_strings, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @property
    def row_count(self) -> int:
        return len(self.records)


class BaseExternalAdapter(ABC):
    """Interface every external source adapter must implement."""

    source_name: str  # Must be an ExternalSourceName value

    @abstractmethod
    async def fetch(self, version: str = "latest") -> RawDataset:
        """Fetch and normalise data from the external source.

        Args:
            version: Dataset version identifier (e.g. "2024-Q1").
                     Use "latest" to request the most recent available data.

        Returns:
            RawDataset with source attribution, hash, and normalised records.
        """
