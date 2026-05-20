"""Model-provider factory.

Returns a LangChain BaseChatModel based on settings.llm_provider:

  - openai     (default) - ChatOpenAI, requires OPENAI_API_KEY
  - ollama     - ChatOllama, runs against a local Ollama daemon
  - anthropic  - ChatAnthropic, requires ANTHROPIC_API_KEY

Each provider is imported lazily so the base install stays lean. Install
optional extras to enable a provider:

    pip install forgeflow[ollama]
    pip install forgeflow[anthropic]
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel

from forgeflow.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ProviderNotInstalledError(RuntimeError):
    """Raised when the optional extras for a chosen provider are not installed."""


def get_model(strong: bool = False) -> BaseChatModel:
    """Return a chat model instance for the configured provider.

    Args:
        strong: If True, return the higher-capability variant (used by
            supervisor + judge). Otherwise return the cheaper worker model.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return _build_openai(settings, strong)
    if provider == "ollama":
        return _build_ollama(settings, strong)
    if provider == "anthropic":
        return _build_anthropic(settings, strong)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
        f"Expected one of: openai, ollama, anthropic."
    )


def _build_openai(settings: Settings, strong: bool) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    key = settings.openai_api_key.get_secret_value()
    if not key:
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    model_name = settings.openai_model_strong if strong else settings.openai_model
    logger.debug("Building ChatOpenAI(model=%s, strong=%s)", model_name, strong)
    return ChatOpenAI(
        model=model_name,
        api_key=key,
        temperature=0,
        max_retries=settings.max_retries,
    )


def _build_ollama(settings: Settings, strong: bool) -> BaseChatModel:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:
        raise ProviderNotInstalledError(
            "Ollama support requires the optional 'ollama' extra. "
            "Install with: pip install 'forgeflow[ollama]'"
        ) from exc

    model_name = settings.ollama_model_strong if strong else settings.ollama_model
    logger.debug("Building ChatOllama(model=%s, base_url=%s, strong=%s)",
                 model_name, settings.ollama_base_url, strong)
    return ChatOllama(
        model=model_name,
        base_url=settings.ollama_base_url,
        temperature=0,
    )


def _build_anthropic(settings: Settings, strong: bool) -> BaseChatModel:
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:
        raise ProviderNotInstalledError(
            "Anthropic support requires the optional 'anthropic' extra. "
            "Install with: pip install 'forgeflow[anthropic]'"
        ) from exc

    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")

    model_name = settings.anthropic_model_strong if strong else settings.anthropic_model
    logger.debug("Building ChatAnthropic(model=%s, strong=%s)", model_name, strong)
    return ChatAnthropic(
        model=model_name,
        api_key=key,
        temperature=0,
        max_retries=settings.max_retries,
    )
