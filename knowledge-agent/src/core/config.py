"""
Knowledge Agent configuration.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Knowledge Agent application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=False)
    api_cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    # MCP Server
    mcp_server_url: str = Field(
        default="http://mcp-server:8001/mcp"
    )

    # LLM
    llm_provider: str = Field(default="openai")
    llm_model: str = Field(default="gpt-4o-mini")
    openai_api_key: str | None = Field(default=None)

    # Agent
    agent_max_tool_retries: int = Field(default=3)
    agent_tool_timeout_seconds: int = Field(default=30)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="console")




@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
