"""Jira repository factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.jira.mock_repository import MockJiraRepository
from src.jira.real_repository import RealJiraRepository
from src.jira.repository import JiraRepository

if TYPE_CHECKING:
    from src.core.config import Settings


def create_jira_repository(settings: Settings) -> JiraRepository:
    """Create the configured Jira repository implementation."""

    provider = settings.jira_provider.strip().lower()
    if provider == "mock":
        return MockJiraRepository()
    if provider == "real":
        return RealJiraRepository(settings)

    raise ValueError(
        f"Unsupported Jira provider '{provider}'. Must be 'mock' or 'real'."
    )
