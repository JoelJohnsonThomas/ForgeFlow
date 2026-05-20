"""Central configuration — all environment variables loaded here via Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM provider ---
    llm_provider: str = Field(
        "openai",
        description="Which LLM provider to use: openai | ollama | anthropic",
    )

    # OpenAI
    openai_api_key: SecretStr = Field(
        SecretStr(""),
        description="OpenAI API key (required when llm_provider=openai)",
    )
    openai_model: str = Field("gpt-4o-mini", description="Default (cheap) model for agents")
    openai_model_strong: str = Field("gpt-4o", description="Strong model for supervisor + judge")

    # Ollama (local)
    ollama_base_url: str = Field(
        "http://localhost:11434",
        description="Ollama daemon URL",
    )
    ollama_model: str = Field("llama3.2:3b", description="Default Ollama model")
    ollama_model_strong: str = Field("llama3.1:8b", description="Strong Ollama model")

    # Anthropic
    anthropic_api_key: SecretStr = Field(
        SecretStr(""),
        description="Anthropic API key (required when llm_provider=anthropic)",
    )
    anthropic_model: str = Field("claude-haiku-4-5", description="Default Anthropic model")
    anthropic_model_strong: str = Field(
        "claude-sonnet-4-5", description="Strong Anthropic model"
    )

    # --- Database ---
    postgres_url: str = Field(
        "postgresql+asyncpg://forgeflow:forgeflow@localhost:5432/forgeflow",
        description="asyncpg DSN for application queries",
    )
    postgres_sync_url: str = Field(
        "postgresql+psycopg://forgeflow:forgeflow@localhost:5432/forgeflow",
        description="psycopg3 DSN for LangGraph checkpointer",
    )

    # --- LangSmith ---
    langchain_tracing_v2: bool = Field(True, description="Enable LangSmith tracing")
    langchain_endpoint: str = Field("https://api.smith.langchain.com")
    langchain_api_key: SecretStr = Field(
        SecretStr(""), description="LangSmith API key (optional)"
    )
    langchain_project: str = Field("forgeflow", description="LangSmith project name")

    # --- MCP Server ---
    mcp_server_host: str = Field("0.0.0.0")
    mcp_server_port: int = Field(8001)

    # --- FastAPI ---
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000)
    api_secret_key: SecretStr = Field(
        SecretStr("change-me-in-production"),
        description="Secret key for signing tokens",
    )

    # --- Resilience ---
    max_retries: int = Field(3, ge=1, le=10)
    circuit_breaker_threshold: int = Field(5, ge=1)
    budget_limit_usd: float = Field(5.0, gt=0, description="Max USD spend per workflow run")

    # --- A2A protocol ---
    a2a_dispatch_enabled: bool = Field(
        True,
        description=(
            "Route LangGraph node invocations through the A2A registry. "
            "Required if agents are deployed out-of-process via HTTPTransport."
        ),
    )

    # --- Approval escalation ---
    approval_escalation_interval_seconds: int = Field(
        300,
        ge=10,
        description="How often the escalation background task runs (>=10s)",
    )
    approval_first_escalation_minutes: int = Field(
        30, ge=1, description="Pending approval older than this -> level 1 (manager)"
    )
    approval_second_escalation_minutes: int = Field(
        120, ge=1, description="Pending approval older than this -> level 2 (director)"
    )
    approval_auto_reject_minutes: int = Field(
        1440, ge=1, description="Pending approval older than this -> auto-rejected"
    )

    # --- Search ---
    tavily_api_key: SecretStr = Field(SecretStr(""), description="Tavily search API key")

    # --- OpenTelemetry (optional — for Phoenix/Langfuse/Jaeger/Datadog APM) ---
    otel_enabled: bool = Field(False, description="Toggle OpenTelemetry tracing")
    otel_service_name: str = Field("forgeflow-api")
    otel_environment: str = Field("development", description="prod | staging | development")
    otel_exporter_endpoint: str = Field(
        "http://localhost:4318/v1/traces",
        description="OTLP-HTTP endpoint (Phoenix/Langfuse/Tempo/etc.)",
    )
    otel_exporter_headers: str = Field(
        "",
        description="Comma-separated 'k=v' headers for the OTLP exporter (e.g. auth)",
    )

    # --- Tracing provider switch (high-level — sets OTel endpoint accordingly) ---
    tracing_provider: str = Field(
        "langsmith",
        description="langsmith | phoenix | langfuse | none",
    )

    # --- GitHub connector ---
    github_token: SecretStr = Field(
        SecretStr(""),
        description="GitHub PAT or installation token (repo scope)",
    )
    github_base_url: str = Field(
        "https://api.github.com",
        description="GitHub REST API base — override for GHES",
    )
    github_default_owner: str = Field(
        "",
        description="Default repo owner so tool calls can omit it",
    )

    # --- Slack (for HITL approval notifications) ---
    slack_bot_token: SecretStr = Field(
        SecretStr(""),
        description="Slack bot user OAuth token (xoxb-...)",
    )
    slack_default_channel: str = Field(
        "",
        description="Default Slack channel for posts (e.g. #forgeflow or C0123456)",
    )
    api_public_url: str = Field(
        "http://localhost:8000",
        description="Externally-reachable API base URL — used for approval deep-links in Slack",
    )

    # --- Dashboard ---
    api_url: str = Field("http://localhost:8000", description="Used by Streamlit to call the API")

    def is_langsmith_enabled(self) -> bool:
        key = self.langchain_api_key.get_secret_value()
        return self.langchain_tracing_v2 and bool(key and key != "")

    def is_tavily_enabled(self) -> bool:
        key = self.tavily_api_key.get_secret_value()
        return bool(key and key != "")

    def is_slack_enabled(self) -> bool:
        key = self.slack_bot_token.get_secret_value()
        return bool(key and key.startswith("xoxb-"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
