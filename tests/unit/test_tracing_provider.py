"""Tests for the high-level tracing-provider selector."""

from __future__ import annotations

import base64

import pytest

from forgeflow.config import get_settings
from forgeflow.observability.tracing_provider import configure


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_langsmith_default_leaves_otel_disabled(monkeypatch):
    monkeypatch.setenv("TRACING_PROVIDER", "langsmith")
    get_settings.cache_clear()

    settings = configure()
    assert settings.otel_enabled is False


def test_none_disables_otel(monkeypatch):
    monkeypatch.setenv("TRACING_PROVIDER", "none")
    monkeypatch.setenv("OTEL_ENABLED", "true")
    get_settings.cache_clear()

    settings = configure()
    assert settings.otel_enabled is False


def test_phoenix_swaps_endpoint_and_enables(monkeypatch):
    monkeypatch.setenv("TRACING_PROVIDER", "phoenix")
    get_settings.cache_clear()

    settings = configure()
    assert settings.otel_enabled is True
    assert "6006" in settings.otel_exporter_endpoint


def test_phoenix_respects_custom_endpoint(monkeypatch):
    monkeypatch.setenv("TRACING_PROVIDER", "phoenix")
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://phoenix.internal/v1/traces")
    get_settings.cache_clear()

    settings = configure()
    # Custom endpoint preserved — the configurator only swaps if the user
    # left the OTel default in place
    assert settings.otel_exporter_endpoint == "https://phoenix.internal/v1/traces"


def test_langfuse_builds_basic_auth(monkeypatch):
    monkeypatch.setenv("TRACING_PROVIDER", "langfuse")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk_test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    get_settings.cache_clear()

    settings = configure()

    assert settings.otel_enabled is True
    assert "cloud.langfuse.com/api/public/otel/v1/traces" in settings.otel_exporter_endpoint

    expected_token = base64.b64encode(b"pk_test:sk_test").decode()
    assert f"Authorization=Basic {expected_token}" == settings.otel_exporter_headers


def test_langfuse_missing_keys_disables(monkeypatch):
    monkeypatch.setenv("TRACING_PROVIDER", "langfuse")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    get_settings.cache_clear()

    settings = configure()
    assert settings.otel_enabled is False


def test_unknown_provider_falls_back_to_langsmith(monkeypatch):
    monkeypatch.setenv("TRACING_PROVIDER", "bogus")
    get_settings.cache_clear()

    settings = configure()
    # Default OTel state is disabled; unknown providers should not enable it
    assert settings.otel_enabled is False
