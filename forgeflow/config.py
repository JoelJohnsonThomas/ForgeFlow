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

    # --- LLM ---
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    openai_model: str = Field("gpt-4o-mini", description="Default (cheap) model for agents")
    openai_model_strong: str = Field("gpt-4o", description="Strong model for supervisor + judge")

    # --- Database ---
    postgres_url: str = Field(
        "postgresql+asyncpg://forgeflow:forgeflow@localhost:5432/forgeflow",
        description="asyncpg DSN for application queries",
    )
    postgres_sync_url: str = Field(
        "postgresql://forgeflow:forgeflow@localhost:5432/forgeflow",
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

    # --- Search ---
    tavily_api_key: SecretStr = Field(SecretStr(""), description="Tavily search API key")

    # --- Dashboard ---
    api_url: str = Field("http://localhost:8000", description="Used by Streamlit to call the API")

    def is_langsmith_enabled(self) -> bool:
        key = self.langchain_api_key.get_secret_value()
        return self.langchain_tracing_v2 and bool(key and key != "")

    def is_tavily_enabled(self) -> bool:
        key = self.tavily_api_key.get_secret_value()
        return bool(key and key != "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
