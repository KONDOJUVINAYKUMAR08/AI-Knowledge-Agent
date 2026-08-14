"""Provider-neutral Jira repository contract."""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from src.jira.models import JiraSearchCriteria, JiraTicket, SimilarTicketMatch

_JIRA_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")


class JiraRepositoryError(Exception):
    """Base exception for Jira repository operations."""


class InvalidJiraRequestError(JiraRepositoryError):
    """Raised when a Jira operation contains invalid input."""


class JiraTicketNotFoundError(JiraRepositoryError):
    """Raised when the requested Jira ticket does not exist."""


def normalize_ticket_key(ticket_key: str) -> str:
    """Normalize and validate a Jira ticket key."""

    if not isinstance(ticket_key, str):
        raise InvalidJiraRequestError("Ticket key must be a string.")

    normalized = ticket_key.strip().upper()
    if not normalized:
        raise InvalidJiraRequestError("Ticket key cannot be empty.")
    if not _JIRA_KEY_PATTERN.fullmatch(normalized):
        raise InvalidJiraRequestError(
            "Ticket key must use Jira format, for example PROJ-1002."
        )
    return normalized


@runtime_checkable
class JiraRepository(Protocol):
    """Operations required by Jira-facing MCP tools."""

    @property
    def provider_name(self) -> str:
        """Return the configured repository provider name."""

    async def get_ticket(self, ticket_key: str) -> JiraTicket:
        """Retrieve one Jira ticket."""

    async def search_tickets(self, criteria: JiraSearchCriteria) -> list[JiraTicket]:
        """Search Jira tickets using provider-neutral filters."""

    async def find_similar_tickets(
        self, ticket_key: str, *, limit: int = 3
    ) -> list[SimilarTicketMatch]:
        """Return deterministic historical tickets similar to the target."""
