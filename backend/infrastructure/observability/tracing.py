"""OpenTelemetry distributed tracing setup (M46).

Wiring:
  - TracerProvider with OTLP HTTP exporter (→ Jaeger / Grafana Tempo)
  - FastAPI auto-instrumentation (span per request, route + method labels)
  - SQLAlchemy async engine auto-instrumentation (span per DB statement)
  - Structlog processor that injects trace_id / span_id into every log record

Configuration (env vars):
  OTEL_SERVICE_NAME          default: eios-backend
  OTEL_EXPORTER_OTLP_ENDPOINT  e.g. http://jaeger:4318  (empty = no export, traces still collected)
  OTEL_TRACES_SAMPLER        default: parentbased_always_on  (use traceidratio for prod sampling)
  OTEL_TRACES_SAMPLER_ARG    float 0.0–1.0 when using traceidratio

Graceful degradation:
  When OTel packages are absent or the OTLP endpoint is unreachable, tracing
  falls back to a NoOp tracer. Logs still get trace_id='' so downstream parsing
  never fails on a missing field.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_CONFIGURED = False


def configure_tracing(app: Any | None = None) -> None:  # noqa: ANN401
    """Set up OTel tracing. Call once from the FastAPI lifespan."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    try:
        _setup_tracing(app)
    except ImportError:
        logger.warning(
            "otel_not_installed", detail="opentelemetry packages missing — tracing disabled"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("otel_setup_failed", error=str(exc))


def _setup_tracing(app: Any | None) -> None:  # noqa: ANN401
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    service_name = os.environ.get("OTEL_SERVICE_NAME", "eios-backend")
    resource = Resource.create({SERVICE_NAME: service_name})

    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("otel_tracing_enabled", endpoint=otlp_endpoint, service=service_name)
    else:
        logger.info(
            "otel_tracing_local_only", detail="Set OTEL_EXPORTER_OTLP_ENDPOINT to export traces"
        )

    trace.set_tracer_provider(provider)

    # ── FastAPI auto-instrumentation ──────────────────────────────────────────
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=provider,
                excluded_urls="/health,/health/ready,/metrics,/metrics/prometheus",
            )
            logger.info("otel_fastapi_instrumented")
        except Exception as exc:  # noqa: BLE001
            logger.warning("otel_fastapi_instrument_failed", error=str(exc))

    # ── SQLAlchemy async engine auto-instrumentation ──────────────────────────
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        from infrastructure.persistence.database import engine as async_engine

        SQLAlchemyInstrumentor().instrument(
            engine=async_engine.sync_engine,
            tracer_provider=provider,
            enable_commenter=True,
        )
        logger.info("otel_sqlalchemy_instrumented")
    except Exception as exc:  # noqa: BLE001
        logger.warning("otel_sqlalchemy_instrument_failed", error=str(exc))


def get_trace_context() -> dict[str, str]:
    """Return current trace_id and span_id as hex strings (empty strings when no span active)."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.is_valid:
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
    except Exception:  # noqa: BLE001
        pass
    return {"trace_id": "", "span_id": ""}


class OtelStructlogProcessor:
    """Structlog processor: injects trace_id + span_id from the active OTel span."""

    def __call__(self, logger: Any, method: str, event_dict: dict) -> dict:  # noqa: ANN401
        ctx = get_trace_context()
        event_dict.setdefault("trace_id", ctx["trace_id"])
        event_dict.setdefault("span_id", ctx["span_id"])
        return event_dict
