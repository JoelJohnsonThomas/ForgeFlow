"""OpenTelemetry tracing initialization.

Optional — only imports OTel SDK when tracing is explicitly enabled. Provides
a single function `init_tracing(app)` that:

  1. Installs the FastAPI auto-instrumentor if otel is available
  2. Configures an OTLP exporter pointing at OTEL_EXPORTER_OTLP_ENDPOINT
     (default: http://localhost:4318/v1/traces for OTLP-HTTP)
  3. Adds resource attributes service.name=forgeflow-api, plus the configured
     environment label

This works transparently with Phoenix, Langfuse, Jaeger, Tempo, Honeycomb, and
Datadog APM — all of them accept OTLP. The provider toggle in tracing_provider.py
just changes the endpoint and headers.
"""

from __future__ import annotations

import logging
from typing import Any

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


def init_tracing(app: Any) -> None:
    """Wire OpenTelemetry FastAPI instrumentation into the running app.

    Safe to call even when OTel packages are not installed — logs a warning
    and returns. This is the integration point for Phoenix, Langfuse, Jaeger,
    etc. via OTLP.
    """
    settings = get_settings()
    if not settings.otel_enabled:
        logger.debug("OpenTelemetry disabled (OTEL_ENABLED=false)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "OTEL_ENABLED=true but opentelemetry packages are not installed. "
            "Install with: pip install 'forgeflow[otel]'"
        )
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.otel_environment,
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_endpoint,
        headers=_parse_headers(settings.otel_exporter_headers),
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)

    logger.info(
        "OpenTelemetry tracing enabled | endpoint=%s service=%s",
        settings.otel_exporter_endpoint,
        settings.otel_service_name,
    )


def _parse_headers(raw: str) -> dict[str, str]:
    """Parse the W3C-style 'key1=val1,key2=val2' header string OTel expects."""
    if not raw:
        return {}
    result: dict[str, str] = {}
    for pair in raw.split(","):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        result[k.strip()] = v.strip()
    return result
