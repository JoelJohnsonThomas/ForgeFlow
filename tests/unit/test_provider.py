"""Tests for the model-provider factory."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.models.provider import ProviderNotInstalledError, get_model


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_openai_provider_returns_chat_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        mock_chat.return_value = MagicMock(name="ChatOpenAI-instance")
        model = get_model(strong=False)
        assert model is mock_chat.return_value
        mock_chat.assert_called_once()


def test_openai_strong_selects_strong_model(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_MODEL_STRONG", "gpt-4o")

    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        get_model(strong=True)
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["model"] == "gpt-4o"


def test_openai_missing_key_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        get_model()


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bogus")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_model()


def test_ollama_missing_extra_raises_helpful_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    # Simulate langchain-ollama not installed
    with (
        patch.dict(sys.modules, {"langchain_ollama": None}),
        pytest.raises(ProviderNotInstalledError, match="forgeflow\\[ollama\\]"),
    ):
        get_model()


def test_anthropic_missing_extra_raises_helpful_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with (
        patch.dict(sys.modules, {"langchain_anthropic": None}),
        pytest.raises(ProviderNotInstalledError, match="forgeflow\\[anthropic\\]"),
    ):
        get_model()


def test_anthropic_missing_key_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    fake_module = MagicMock()
    fake_module.ChatAnthropic = MagicMock()

    with (
        patch.dict(sys.modules, {"langchain_anthropic": fake_module}),
        pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"),
    ):
        get_model()
