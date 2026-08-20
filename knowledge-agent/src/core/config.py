"""
Knowledge Agent configuration.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Knowledge Agent application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=False)
    api_cors_origins: list[str] = Field(
        default=["http://localhost:5173"]
    )

    # MCP Server
    mcp_server_url: str = Field(
        default="http://mcp-server:8001/mcp"
    )

    # LLM
    llm_provider: str = Field(default="gemini")
    llm_model: str = Field(default="gemini-3.5-flash")
    openai_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)
    groq_api_key: str | None = Field(default=None)
    llm_timeout_seconds: float = Field(default=45.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=10)

    # Agent
    agent_tool_timeout_seconds: int = Field(default=30)
    agent_query_timeout_seconds: int = Field(default=90, ge=1, le=300)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="console")




@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
