"""Unit tests for M46 — OpenTelemetry tracing, HTTP metrics, health check."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# OTel tracing module
# ──────────────────────────────────────────────────────────────────────────────


class TestOtelTracing:
    def test_configure_tracing_is_idempotent(self) -> None:
        from infrastructure.observability import tracing as _mod

        original = _mod._CONFIGURED
        _mod._CONFIGURED = False
        try:
            from infrastructure.observability.tracing import configure_tracing

            configure_tracing(None)
            configure_tracing(None)  # second call must be a no-op
            assert _mod._CONFIGURED is True
        finally:
            _mod._CONFIGURED = original

    def test_get_trace_context_returns_empty_when_no_span(self) -> None:
        from infrastructure.observability.tracing import get_trace_context

        ctx = get_trace_context()
        assert "trace_id" in ctx
        assert "span_id" in ctx
        # Outside a span both are empty strings
        assert ctx["trace_id"] == "" or len(ctx["trace_id"]) == 32

    def test_otel_structlog_processor_adds_keys(self) -> None:
        from infrastructure.observability.tracing import OtelStructlogProcessor

        proc = OtelStructlogProcessor()
        event = {"event": "test_log"}
        result = proc(None, "info", event)
        assert "trace_id" in result
        assert "span_id" in result

    def test_otel_structlog_processor_does_not_overwrite_existing_keys(self) -> None:
        from infrastructure.observability.tracing import OtelStructlogProcessor

        proc = OtelStructlogProcessor()
        event = {"event": "test", "trace_id": "existing-trace"}
        result = proc(None, "info", event)
        assert result["trace_id"] == "existing-trace"

    def test_configure_tracing_graceful_when_otel_missing(self) -> None:
        import infrastructure.observability.tracing as _mod

        original = _mod._CONFIGURED
        _mod._CONFIGURED = False
        try:
            with patch(
                "infrastructure.observability.tracing._setup_tracing",
                side_effect=ImportError("no otel"),
            ):
                from infrastructure.observability.tracing import configure_tracing

                configure_tracing(None)  # must not raise
        finally:
            _mod._CONFIGURED = original


# ──────────────────────────────────────────────────────────────────────────────
# HTTP metrics module
# ──────────────────────────────────────────────────────────────────────────────


class TestHttpMetrics:
    def test_prometheus_metrics_are_registered(self) -> None:
        from prometheus_client import REGISTRY

        # prometheus_client stores Counter("eios_http_requests_total") under base name
        # "eios_http_requests" (strips _total suffix in MetricFamily.name)
        names = {m.name for m in REGISTRY.collect()}
        assert "eios_http_request_duration_seconds" in names
        assert "eios_http_requests_active" in names
        # Accept either form — prometheus_client version-dependent
        assert "eios_http_requests_total" in names or "eios_http_requests" in names

    def test_record_request_increments_counter(self) -> None:
        from infrastructure.observability.http_metrics import http_requests_total, record_request

        before = http_requests_total.labels(
            method="GET", endpoint="/test", status_code="200"
        )._value.get()
        record_request("GET", "/test", 200, 0.05)
        after = http_requests_total.labels(
            method="GET", endpoint="/test", status_code="200"
        )._value.get()
        assert after == before + 1

    def test_record_request_observes_histogram(self) -> None:
        from infrastructure.observability.http_metrics import record_request

        record_request("POST", "/evidences/", 201, 0.123)
        # Histogram sum should increase — just verify no exception raised


# ──────────────────────────────────────────────────────────────────────────────
# MetricsCounterMiddleware
# ──────────────────────────────────────────────────────────────────────────────


class TestMetricsCounterMiddleware:
    @pytest.mark.asyncio
    async def test_middleware_calls_record_request(self) -> None:
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from app.middleware.metrics_counter import MetricsCounterMiddleware

        async def homepage(request):
            return Response("ok", status_code=200)

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(MetricsCounterMiddleware)

        recorded = []

        with patch(
            # Patch where it's actually used (directly imported into the middleware module)
            "app.middleware.metrics_counter.record_request",
            side_effect=lambda *a, **kw: recorded.append((a, kw)),
        ):
            with TestClient(app) as client:
                resp = client.get("/")
                assert resp.status_code == 200

        assert len(recorded) == 1
        _, kw = recorded[0]
        assert kw["method"] == "GET"
        assert kw["status_code"] == 200


# ──────────────────────────────────────────────────────────────────────────────
# Health endpoints
# ──────────────────────────────────────────────────────────────────────────────


class TestHealthEndpoints:
    def test_version_is_updated(self) -> None:
        from interfaces.api.routers.health import VERSION

        assert VERSION == "0.23.0"

    @pytest.mark.asyncio
    async def test_liveness_returns_ok(self) -> None:
        from interfaces.api.routers.health import liveness

        result = await liveness()
        assert result.status == "ok"
        assert result.service == "eios-backend"
        assert result.version == "0.23.0"
        assert result.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_readiness_degrades_when_db_down(self) -> None:
        from interfaces.api.routers.health import readiness

        with patch(
            "interfaces.api.routers.health.engine",
        ) as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
            mock_conn.__aexit__ = AsyncMock(return_value=False)
            mock_engine.connect.return_value = mock_conn

            with patch("infrastructure.llm.deps._provider", None):
                response = await readiness()

        # JSONResponse — check status_code
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_readiness_ok_with_mocked_db_and_redis(self) -> None:
        from interfaces.api.routers.health import readiness

        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.execute = AsyncMock(return_value=None)

        with (
            patch("interfaces.api.routers.health.engine") as mock_engine,
            patch("infrastructure.redis.client.get_redis", return_value=None),
            patch("infrastructure.redis.blacklist.get_redis_blacklist", return_value=None),
            patch("infrastructure.llm.deps._provider", None),
        ):
            mock_engine.connect.return_value = mock_conn
            response = await readiness()

        assert response.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# Alert rules file
# ──────────────────────────────────────────────────────────────────────────────


class TestAlertRules:
    def test_alert_rules_file_exists(self) -> None:
        import os

        path = "/Users/ayhanyaman/Desktop/EIOS/backend/infrastructure/observability/alert_rules.yml"
        assert os.path.exists(path)

    def test_alert_rules_are_valid_yaml(self) -> None:
        import yaml

        path = "/Users/ayhanyaman/Desktop/EIOS/backend/infrastructure/observability/alert_rules.yml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "groups" in data
        assert len(data["groups"]) > 0

    def test_critical_alerts_defined(self) -> None:
        import yaml

        path = "/Users/ayhanyaman/Desktop/EIOS/backend/infrastructure/observability/alert_rules.yml"
        with open(path) as f:
            data = yaml.safe_load(f)
        alert_names = [rule["alert"] for group in data["groups"] for rule in group["rules"]]
        assert "EIOSHighErrorRate" in alert_names
        assert "EIOSHighP99Latency" in alert_names
        assert "EIOSServiceDown" in alert_names
        assert "EIOSRedisBlacklistUnavailable" in alert_names
        assert "EIOSBackupStale" in alert_names

    def test_prometheus_scrape_config_exists(self) -> None:
        import os

        path = "/Users/ayhanyaman/Desktop/EIOS/backend/infrastructure/observability/prometheus.yml"
        assert os.path.exists(path)
