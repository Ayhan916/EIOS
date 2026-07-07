"""Unit tests for M31.1 entity ownership resolver."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.compliance.entity_ownership import resolve_entity_org_id


class TestResolveEntityOrgId:
    """Tests for entity ownership resolution via assessment JOIN."""

    def _make_session(self, scalar_result) -> MagicMock:
        """Return a mock AsyncSession that yields scalar_result from execute()."""
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=scalar_result)
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        return session

    @pytest.mark.asyncio
    async def test_finding_returns_org_id_when_found(self):
        session = self._make_session("org-abc")
        result = await resolve_entity_org_id(session, "finding", "finding-1")
        assert result == "org-abc"

    @pytest.mark.asyncio
    async def test_finding_returns_none_when_not_found(self):
        session = self._make_session(None)
        result = await resolve_entity_org_id(session, "finding", "unknown-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_risk_returns_org_id_when_found(self):
        session = self._make_session("org-xyz")
        result = await resolve_entity_org_id(session, "risk", "risk-1")
        assert result == "org-xyz"

    @pytest.mark.asyncio
    async def test_risk_returns_none_when_not_found(self):
        session = self._make_session(None)
        result = await resolve_entity_org_id(session, "risk", "unknown-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_recommendation_returns_org_id_when_found(self):
        session = self._make_session("org-abc")
        result = await resolve_entity_org_id(session, "recommendation", "rec-1")
        assert result == "org-abc"

    @pytest.mark.asyncio
    async def test_recommendation_returns_none_when_not_found(self):
        session = self._make_session(None)
        result = await resolve_entity_org_id(session, "recommendation", "unknown-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_unsupported_entity_type_returns_none(self):
        session = self._make_session("org-abc")
        result = await resolve_entity_org_id(session, "evidence", "ev-1")
        assert result is None
        # Should not even call execute for unsupported types
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_ownership_mismatch_detected_by_caller(self):
        """Simulate cross-org attempt: entity is in org-b, caller is org-a."""
        session = self._make_session("org-b")
        entity_org = await resolve_entity_org_id(session, "finding", "finding-from-org-b")
        caller_org = "org-a"
        assert entity_org != caller_org  # caller should raise 403

    @pytest.mark.asyncio
    async def test_same_org_passes(self):
        """Simulate successful ownership check: same org."""
        session = self._make_session("org-a")
        entity_org = await resolve_entity_org_id(session, "finding", "finding-from-org-a")
        caller_org = "org-a"
        assert entity_org == caller_org

    @pytest.mark.asyncio
    async def test_empty_entity_id_returns_none(self):
        session = self._make_session(None)
        result = await resolve_entity_org_id(session, "risk", "")
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_called_once_per_resolution(self):
        session = self._make_session("org-1")
        await resolve_entity_org_id(session, "finding", "f-1")
        session.execute.assert_called_once()
