"""Unit tests for M20 middleware and rate limiter."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.rate_limit import _check, _windows


# ── Rate limiter unit tests ───────────────────────────────────────────────────

class TestRateLimiter:
    def setup_method(self) -> None:
        # Clear all window state before each test
        _windows.clear()

    def test_allows_request_within_limit(self) -> None:
        assert _check("test-key", limit=5) is True

    def test_allows_up_to_limit(self) -> None:
        for _ in range(5):
            assert _check("burst-key", limit=5) is True

    def test_blocks_when_limit_exceeded(self) -> None:
        for _ in range(5):
            _check("block-key", limit=5)
        result = _check("block-key", limit=5)
        assert result is False

    def test_different_keys_are_independent(self) -> None:
        for _ in range(5):
            _check("key-a", limit=5)
        # key-b should still have full quota
        assert _check("key-b", limit=5) is True

    def test_window_slides_on_expiry(self) -> None:
        # Fill the window
        for _ in range(3):
            _check("slide-key", limit=3, window_seconds=1)
        # Blocked immediately
        assert _check("slide-key", limit=3, window_seconds=1) is False
        # After window expires, slot opens again
        time.sleep(1.05)
        assert _check("slide-key", limit=3, window_seconds=1) is True

    def test_zero_limit_always_blocks(self) -> None:
        result = _check("zero-key", limit=0)
        assert result is False


class TestRateLimitDependencies:
    """Test FastAPI dependency functions raise 429 on violation."""

    def setup_method(self) -> None:
        _windows.clear()

    @pytest.mark.asyncio
    async def test_rate_limit_auth_passes_within_limit(self) -> None:
        from fastapi import Request
        from shared.rate_limit import rate_limit_auth

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "1.2.3.4"

        with patch("shared.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_auth_per_minute = 100
            await rate_limit_auth(mock_request)  # must not raise

    @pytest.mark.asyncio
    async def test_rate_limit_auth_raises_429_when_exceeded(self) -> None:
        from fastapi import HTTPException, Request
        from shared.rate_limit import rate_limit_auth

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "9.9.9.9"

        with patch("shared.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_auth_per_minute = 2
            await rate_limit_auth(mock_request)
            await rate_limit_auth(mock_request)
            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_auth(mock_request)
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_llm_raises_429_when_exceeded(self) -> None:
        from fastapi import HTTPException, Request
        from shared.rate_limit import rate_limit_llm

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "7.7.7.7"

        with patch("shared.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_llm_per_minute = 1
            await rate_limit_llm(mock_request)
            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_llm(mock_request)
            assert exc_info.value.status_code == 429
            assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_x_forwarded_for_used_as_client_ip(self) -> None:
        from fastapi import Request
        from shared.rate_limit import rate_limit_api

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"

        with patch("shared.rate_limit.settings") as mock_settings:
            mock_settings.rate_limit_api_per_minute = 100
            await rate_limit_api(mock_request)  # must not raise; 203.0.113.1 is the key


# ── Security headers middleware ───────────────────────────────────────────────

class TestSecurityHeadersMiddleware:
    """Test that security headers are injected correctly."""

    @pytest.mark.asyncio
    async def test_security_headers_present_in_development(self) -> None:
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse
        from app.middleware.security_headers import SecurityHeadersMiddleware

        async def homepage(request):  # type: ignore[no-untyped-def]
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(SecurityHeadersMiddleware)

        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert resp.headers["Permissions-Policy"] == "geolocation=(), camera=(), microphone=()"

    @pytest.mark.asyncio
    async def test_hsts_only_in_production(self) -> None:
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse
        from app.middleware.security_headers import SecurityHeadersMiddleware

        async def homepage(request):  # type: ignore[no-untyped-def]
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(SecurityHeadersMiddleware)

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.is_production = False
            with TestClient(app) as client:
                resp = client.get("/")
            assert "Strict-Transport-Security" not in resp.headers

    @pytest.mark.asyncio
    async def test_hsts_set_in_production(self) -> None:
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse
        from app.middleware.security_headers import SecurityHeadersMiddleware

        async def homepage(request):  # type: ignore[no-untyped-def]
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(SecurityHeadersMiddleware)

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.is_production = True
            with TestClient(app) as client:
                resp = client.get("/")
            assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]


# ── Request ID middleware ─────────────────────────────────────────────────────

class TestRequestIDMiddleware:
    def test_request_id_injected_into_response(self) -> None:
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse
        from app.middleware.request_id import RequestIDMiddleware

        async def homepage(request):  # type: ignore[no-untyped-def]
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(RequestIDMiddleware)

        with TestClient(app) as client:
            resp = client.get("/")
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) == 36  # UUID format

    def test_client_supplied_request_id_preserved(self) -> None:
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse
        from app.middleware.request_id import RequestIDMiddleware

        async def homepage(request):  # type: ignore[no-untyped-def]
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(RequestIDMiddleware)

        custom_id = "my-trace-id-12345"
        with TestClient(app) as client:
            resp = client.get("/", headers={"X-Request-ID": custom_id})
        assert resp.headers["X-Request-ID"] == custom_id
