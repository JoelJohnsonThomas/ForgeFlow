"""High-level tracing-provider selector — sets OTel endpoint + auth per backend.

This is the layer above forgeflow/observability/tracing.py. Users pick a
provider with one env var (`TRACING_PROVIDER`) instead of remembering the
OTLP endpoint and header format for each vendor.

Supported providers:

  langsmith   — keep LangSmith auto-tracing (no OTel). This is the default
                because every ForgeFlow agent is already LangChain-instrumented.
  phoenix     — local Arize Phoenix or cloud. Sends OTLP-HTTP.
  langfuse    — Langfuse cloud or self-hosted. Uses Basic auth derived from
                LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY.
  none        — disable all tracing.

Each entry returns a dict the caller merges into settings:
  {"otel_enabled": bool, "otel_exporter_endpoint": str, "otel_exporter_headers": str}
"""

from __future__ import annotations

import base64
import logging
import os

from forgeflow.config import Settings, get_settings

logger = logging.getLogger(__name__)


def configure() -> Settings:
    """Apply the TRACING_PROVIDER selection to OTel settings.

    Called once at app startup before init_tracing(). Updates the cached
    Settings instance in place so the rest of the app sees consistent values.
    """
    settings = get_settings()
    provider = settings.tracing_provider.lower()

    if provider in ("langsmith", ""):
        # No change — LangSmith uses LANGCHAIN_TRACING_V2 directly
        logger.info("Tracing provider: langsmith (LangChain native instrumentation)")
        return settings

    if provider == "none":
        settings.otel_enabled = False
        logger.info("Tracing provider: none (all backends disabled)")
        return settings

    if provider == "phoenix":
        # Phoenix accepts OTLP-HTTP on /v1/traces by default. Override via
        # OTEL_EXPORTER_ENDPOINT if running Phoenix on a non-default URL.
        if settings.otel_exporter_endpoint == "http://localhost:4318/v1/traces":
            settings.otel_exporter_endpoint = "http://localhost:6006/v1/traces"
        settings.otel_enabled = True
        logger.info(
            "Tracing provider: phoenix → %s", settings.otel_exporter_endpoint
        )
        return settings

    if provider == "langfuse":
        # Langfuse expects Basic auth: base64(public_key:secret_key)
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not (public_key and secret_key):
            logger.warning(
                "TRACING_PROVIDER=langfuse but LANGFUSE_PUBLIC_KEY / "
                "LANGFUSE_SECRET_KEY are not set; tracing disabled."
            )
            settings.otel_enabled = False
            return settings

        token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
        settings.otel_exporter_endpoint = f"{host.rstrip('/')}/api/public/otel/v1/traces"
        settings.otel_exporter_headers = f"Authorization=Basic {token}"
        settings.otel_enabled = True
        logger.info("Tracing provider: langfuse → %s", host)
        return settings

    logger.warning(
        "Unknown TRACING_PROVIDER '%s'; falling back to langsmith.", provider
    )
    return settings
