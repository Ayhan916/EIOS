"""Unit tests for M45.1.1 RLS context helper.

Tests cover:
  - async_set_rls_context executes SET LOCAL with correct org_id
  - async_set_rls_context is a no-op when org_id is None or empty
  - async_clear_rls_context executes SET LOCAL with empty string
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from shared.rls import async_clear_rls_context, async_set_rls_context


class TestAsyncSetRLSContext:
    @pytest.mark.asyncio
    async def test_sets_org_id_on_session(self) -> None:
        session = AsyncMock()
        await async_set_rls_context(session, "org-abc-123")
        session.execute.assert_called_once()
        call_args = session.execute.call_args
        # Second positional arg is the params dict
        assert call_args[0][1] == {"org_id": "org-abc-123"}

    @pytest.mark.asyncio
    async def test_no_op_when_org_id_is_none(self) -> None:
        session = AsyncMock()
        await async_set_rls_context(session, None)
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_op_when_org_id_is_empty_string(self) -> None:
        session = AsyncMock()
        await async_set_rls_context(session, "")
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_different_org_ids_use_different_params(self) -> None:
        session = AsyncMock()
        await async_set_rls_context(session, "org-1")
        params_1 = session.execute.call_args[0][1]
        session.execute.reset_mock()

        await async_set_rls_context(session, "org-2")
        params_2 = session.execute.call_args[0][1]

        assert params_1["org_id"] == "org-1"
        assert params_2["org_id"] == "org-2"


class TestAsyncClearRLSContext:
    @pytest.mark.asyncio
    async def test_clears_via_set_local(self) -> None:
        session = AsyncMock()
        await async_clear_rls_context(session)
        session.execute.assert_called_once()
        # Verify it sends the CLEAR sql (no params dict expected)
        sql_obj = session.execute.call_args[0][0]
        assert "app.current_org_id" in str(sql_obj)
