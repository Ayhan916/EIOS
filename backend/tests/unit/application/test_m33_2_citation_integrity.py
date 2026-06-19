"""M33.2 — Citation Integrity Framework Tests.

Verifies:
- Citation hash determinism
- VERIFIED status when object exists in correct tenant
- DELETED status when object is missing
- DELETED (not exposed) for cross-tenant objects
- Unknown citation types treated as DELETED
All DB calls are mocked.
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.copilot.citation_integrity import _citation_hash, verify_citations
from domain.enums import CitationIntegrityStatus


def _make_session(row_result) -> AsyncMock:
    """Build a mock session that returns row_result from scalar queries."""
    session = AsyncMock()
    mock_exec_result = MagicMock()
    mock_exec_result.mappings.return_value.first.return_value = row_result
    session.execute = AsyncMock(return_value=mock_exec_result)
    return session


class TestCitationHash:
    def test_hash_is_deterministic(self):
        h1 = _citation_hash("Supplier", "s-123", "org-1")
        h2 = _citation_hash("Supplier", "s-123", "org-1")
        assert h1 == h2

    def test_hash_is_sha256_length(self):
        h = _citation_hash("Supplier", "s-123", "org-1")
        assert len(h) == 64

    def test_different_type_different_hash(self):
        h1 = _citation_hash("Supplier", "x-1", "org-1")
        h2 = _citation_hash("Finding", "x-1", "org-1")
        assert h1 != h2

    def test_different_org_different_hash(self):
        h1 = _citation_hash("Supplier", "s-1", "org-A")
        h2 = _citation_hash("Supplier", "s-1", "org-B")
        assert h1 != h2

    def test_hash_matches_sha256_of_payload(self):
        payload = "Supplier:s-1:org-1"
        expected = hashlib.sha256(payload.encode()).hexdigest()
        assert _citation_hash("Supplier", "s-1", "org-1") == expected


class TestVerifiedStatus:
    @pytest.mark.asyncio
    async def test_existing_same_tenant_object_is_verified(self):
        row = {"id": "s-1", "organization_id": "org-1", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        citations = [{"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"s-1": "Supplier"}, "org-1", session)
        assert len(records) == 1
        assert records[0].integrity_status == CitationIntegrityStatus.VERIFIED
        assert records[0].citation_snapshot["id"] == "s-1"

    @pytest.mark.asyncio
    async def test_verified_record_has_snapshot(self):
        row = {"id": "s-1", "organization_id": "org-1", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        citations = [{"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"s-1": "Supplier"}, "org-1", session)
        assert records[0].citation_snapshot["organization_id"] == "org-1"


class TestDeletedStatus:
    @pytest.mark.asyncio
    async def test_missing_object_is_deleted(self):
        session = _make_session(None)  # Object not found in DB
        citations = [{"citation_type": "Supplier", "object_id": "nonexistent", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"nonexistent": "Supplier"}, "org-1", session)
        assert len(records) == 1
        assert records[0].integrity_status == CitationIntegrityStatus.DELETED
        assert records[0].citation_snapshot == {}

    @pytest.mark.asyncio
    async def test_cross_tenant_object_is_deleted(self):
        """Object belongs to org-B but requester is org-A — must return DELETED, not VERIFIED."""
        row = {"id": "s-1", "organization_id": "org-B", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        citations = [{"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"s-1": "Supplier"}, "org-A", session)
        assert records[0].integrity_status == CitationIntegrityStatus.DELETED
        # Snapshot must NOT expose cross-tenant data
        assert records[0].citation_snapshot == {}

    @pytest.mark.asyncio
    async def test_cross_tenant_object_does_not_reveal_existence(self):
        """Status must be DELETED (not stale or 'wrong_tenant') to avoid information leakage."""
        row = {"id": "s-1", "organization_id": "org-other", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        citations = [{"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"s-1": "Supplier"}, "org-requester", session)
        assert records[0].integrity_status == CitationIntegrityStatus.DELETED


class TestUnknownCitationType:
    @pytest.mark.asyncio
    async def test_unknown_type_returns_deleted(self):
        session = AsyncMock()  # Should not be called
        citations = [{"citation_type": "UnknownEntity", "object_id": "u-1", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"u-1": "UnknownEntity"}, "org-1", session)
        assert len(records) == 1
        assert records[0].integrity_status == CitationIntegrityStatus.DELETED


class TestCitationIntegrityFields:
    @pytest.mark.asyncio
    async def test_record_has_message_id(self):
        row = {"id": "s-1", "organization_id": "org-1", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        citations = [{"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"}]
        records = await verify_citations("msg-abc", citations, {"s-1": "Supplier"}, "org-1", session)
        assert records[0].message_id == "msg-abc"

    @pytest.mark.asyncio
    async def test_record_has_citation_hash(self):
        row = {"id": "s-1", "organization_id": "org-1", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        citations = [{"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"s-1": "Supplier"}, "org-1", session)
        expected_hash = _citation_hash("Supplier", "s-1", "org-1")
        assert records[0].citation_hash == expected_hash

    @pytest.mark.asyncio
    async def test_multiple_citations_produce_multiple_records(self):
        row = {"id": "x", "organization_id": "org-1", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        citations = [
            {"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"},
            {"citation_type": "Finding", "object_id": "f-1", "relevance": "retrieved"},
        ]
        records = await verify_citations(
            "msg-1", citations, {"s-1": "Supplier", "f-1": "Finding"}, "org-1", session
        )
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_empty_citations_returns_empty_list(self):
        session = AsyncMock()
        records = await verify_citations("msg-1", [], {}, "org-1", session)
        assert records == []

    @pytest.mark.asyncio
    async def test_verified_at_is_set(self):
        from datetime import UTC, datetime
        row = {"id": "s-1", "organization_id": "org-1", "updated_at": "2026-01-01T00:00:00Z"}
        session = _make_session(row)
        before = datetime.now(UTC)
        citations = [{"citation_type": "Supplier", "object_id": "s-1", "relevance": "explicit"}]
        records = await verify_citations("msg-1", citations, {"s-1": "Supplier"}, "org-1", session)
        after = datetime.now(UTC)
        assert before <= records[0].verified_at <= after
