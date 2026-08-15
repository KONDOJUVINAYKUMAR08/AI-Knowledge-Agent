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
        extra="ignore",
    )

    # Server identity
    mcp_server_name: str = Field(default="knowledge-agent-mcp-server")
    mcp_server_version: str = Field(default="0.1.0")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # "json" | "console"

    # Jira provider
    jira_provider: str = Field(default="mock")

    # Real Jira Configuration (Future)
    jira_base_url: str | None = Field(default=None)
    jira_auth_mode: str | None = Field(default=None)
    jira_user_email: str | None = Field(default=None)
    jira_api_token: str | None = Field(default=None)

    # Jira Custom Fields Mapping
    jira_custom_field_service: str | None = Field(default=None)
    jira_custom_field_environment: str | None = Field(default=None)
    jira_custom_field_platform: str | None = Field(default=None)
    jira_custom_field_cluster: str | None = Field(default=None)
    jira_custom_field_region: str | None = Field(default=None)
    jira_custom_field_symptoms: str | None = Field(default=None)
    jira_custom_field_resolution: str | None = Field(default=None)
    jira_custom_field_affected_version: str | None = Field(default=None)
    jira_custom_field_root_cause: str | None = Field(default=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
