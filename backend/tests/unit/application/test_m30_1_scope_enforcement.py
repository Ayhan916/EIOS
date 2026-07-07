"""
M30.1 Unit Tests — Scope Enforcement

Tests for scope_gate and require_scope FastAPI dependencies.
No I/O, no DB, no network.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from interfaces.api.deps import require_scope, scope_gate


def _make_request(*, api_scopes: list[str] | None, method: str = "GET") -> Any:
    """Build a minimal mock FastAPI Request with state configured."""
    req = MagicMock()
    req.method = method
    req.state.api_scopes = api_scopes
    # Simulate API key presence for api_key_id state
    req.state.api_key_id = "key-123" if api_scopes is not None else None
    return req


def _make_user() -> Any:
    return MagicMock()


# ── scope_gate ────────────────────────────────────────────────────────────────


class TestScopeGate:
    """scope_gate is a router-level dependency factory."""

    async def _call(
        self,
        read_scope: str,
        write_scope: str | None = None,
        *,
        method: str = "GET",
        api_scopes: list[str] | None,
    ) -> None:
        gate = scope_gate(read_scope, write_scope)
        req = _make_request(api_scopes=api_scopes, method=method)
        user = _make_user()
        # Patch get_current_user dependency inside _check
        with patch("interfaces.api.deps.get_current_user", return_value=user):
            await gate(request=req, _=user)

    @pytest.mark.asyncio
    async def test_jwt_user_passes_read(self) -> None:
        """JWT users (api_scopes=None) always pass scope_gate."""
        await self._call("assessments:read", "assessments:write", api_scopes=None)

    @pytest.mark.asyncio
    async def test_jwt_user_passes_write(self) -> None:
        await self._call("assessments:read", "assessments:write", method="POST", api_scopes=None)

    @pytest.mark.asyncio
    async def test_api_key_correct_read_scope(self) -> None:
        await self._call("assessments:read", "assessments:write", api_scopes=["assessments:read"])

    @pytest.mark.asyncio
    async def test_api_key_correct_write_scope_on_post(self) -> None:
        await self._call(
            "assessments:read",
            "assessments:write",
            method="POST",
            api_scopes=["assessments:write"],
        )

    @pytest.mark.asyncio
    async def test_api_key_missing_read_scope_is_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await self._call("assessments:read", api_scopes=["suppliers:read"])
        assert exc_info.value.status_code == 403
        assert "assessments:read" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_api_key_missing_write_scope_on_post_is_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await self._call(
                "assessments:read",
                "assessments:write",
                method="POST",
                api_scopes=["assessments:read"],
            )
        assert exc_info.value.status_code == 403
        assert "assessments:write" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_api_key_with_only_read_scope_can_get(self) -> None:
        """Read scope is sufficient for GET even if write scope is defined."""
        await self._call(
            "assessments:read",
            "assessments:write",
            method="GET",
            api_scopes=["assessments:read"],
        )

    @pytest.mark.asyncio
    async def test_api_key_write_scope_not_sufficient_for_get(self) -> None:
        """GET requires read scope; having only write scope is insufficient."""
        with pytest.raises(HTTPException) as exc_info:
            await self._call(
                "assessments:read",
                "assessments:write",
                method="GET",
                api_scopes=["assessments:write"],
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_read_only_gate_no_write_scope_falls_back_to_read(self) -> None:
        """When write_scope=None, POST falls back to requiring read_scope.
        A key with read_scope passes — HTTP method restriction is the router's job."""
        await self._call(
            "executive:read",
            None,
            method="POST",
            api_scopes=["executive:read"],
        )

    @pytest.mark.asyncio
    async def test_empty_scope_list_is_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await self._call("assessments:read", api_scopes=[])
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_method_requires_write_scope(self) -> None:
        with pytest.raises(HTTPException):
            await self._call(
                "suppliers:read",
                "suppliers:write",
                method="DELETE",
                api_scopes=["suppliers:read"],
            )

    @pytest.mark.asyncio
    async def test_patch_method_requires_write_scope(self) -> None:
        with pytest.raises(HTTPException):
            await self._call(
                "suppliers:read",
                "suppliers:write",
                method="PATCH",
                api_scopes=["suppliers:read"],
            )


# ── require_scope ─────────────────────────────────────────────────────────────


class TestRequireScope:
    """require_scope is used for fine-grained endpoint-level control."""

    async def _call(self, scope: str, *, api_scopes: list[str] | None) -> Any:
        dep = require_scope(scope)
        req = _make_request(api_scopes=api_scopes)
        user = _make_user()
        with patch("interfaces.api.deps.get_current_user", return_value=user):
            return await dep(request=req, current_user=user)

    @pytest.mark.asyncio
    async def test_jwt_user_always_passes(self) -> None:
        result = await self._call("some:scope", api_scopes=None)
        assert result is not None

    @pytest.mark.asyncio
    async def test_api_key_with_correct_scope_passes(self) -> None:
        result = await self._call("assessments:read", api_scopes=["assessments:read", "risks:read"])
        assert result is not None

    @pytest.mark.asyncio
    async def test_api_key_with_missing_scope_is_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await self._call("assessments:write", api_scopes=["assessments:read"])
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_error_message_names_the_missing_scope(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await self._call("executive:read", api_scopes=["reports:read"])
        assert "executive:read" in exc_info.value.detail
