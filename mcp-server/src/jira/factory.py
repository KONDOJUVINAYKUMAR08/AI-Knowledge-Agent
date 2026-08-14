"""Jira repository factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.jira.mock_repository import MockJiraRepository
from src.jira.repository import JiraRepository

if TYPE_CHECKING:
    from src.core.config import Settings


def create_jira_repository(settings: Settings) -> JiraRepository:
    """Create the configured Jira repository implementation."""

    provider = settings.jira_provider.strip().lower()
    if provider == "mock":
        return MockJiraRepository()

    raise ValueError(
        f"Unsupported Jira provider '{provider}'. Only 'mock' is available until real Jira access is configured."
    )
