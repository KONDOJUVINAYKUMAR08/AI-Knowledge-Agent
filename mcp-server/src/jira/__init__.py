"""Provider-neutral Jira domain and repository implementations."""

from src.jira.factory import create_jira_repository
from src.jira.models import JiraSearchCriteria, JiraTicket, SimilarTicketMatch
from src.jira.repository import (
    InvalidJiraRequestError,
    JiraRepository,
    JiraRepositoryError,
    JiraTicketNotFoundError,
)

__all__ = [
    "InvalidJiraRequestError",
    "JiraRepository",
    "JiraRepositoryError",
    "JiraSearchCriteria",
    "JiraTicket",
    "JiraTicketNotFoundError",
    "SimilarTicketMatch",
    "create_jira_repository",
]
