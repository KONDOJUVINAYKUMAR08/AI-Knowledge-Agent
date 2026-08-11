"""
Centralized configuration for the MCP Server.

Loaded from environment variables with .env file support.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MCP Server application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server identity
    mcp_server_name: str = Field(default="knowledge-agent-mcp-server")
    mcp_server_version: str = Field(default="0.1.0")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # "json" | "console"

    # Mock data
    mock_ticket_response_delay_ms: int = Field(default=0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
