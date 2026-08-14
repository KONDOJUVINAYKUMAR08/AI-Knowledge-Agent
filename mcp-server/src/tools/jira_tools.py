"""MCP tools backed by the configured provider-neutral Jira repository."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from pydantic import ValidationError

from src.core.logging import get_logger
from src.jira.models import JiraSearchCriteria
from src.jira.repository import (
    InvalidJiraRequestError,
    JiraRepository,
    JiraRepositoryError,
    JiraTicketNotFoundError,
)

logger = get_logger(__name__)


def _error(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message}}


def register_jira_tools(mcp: MCPServer, repository: JiraRepository) -> None:
    """Register operational Jira tools using an injected repository."""

    @mcp.tool(
        name="get_ticket",
        description="Retrieve a normalized operational Jira ticket by key, for example PROJ-1002.",
    )
    async def get_ticket(ticket_key: str) -> dict[str, Any]:
        try:
            ticket = await repository.get_ticket(ticket_key)
        except InvalidJiraRequestError as exc:
            return _error("invalid_ticket_key", str(exc))
        except JiraTicketNotFoundError as exc:
            return _error("ticket_not_found", str(exc))
        except JiraRepositoryError:
            logger.error("jira_tool.get_ticket.repository_error")
            return _error("jira_unavailable", "Unable to retrieve the Jira ticket.")

        logger.info("jira_tool.get_ticket.success", ticket_key=ticket.key)
        return {
            "success": True,
            "ticket": ticket.model_dump(mode="json"),
            "source": repository.provider_name,
        }

    @mcp.tool(
        name="search_tickets",
        description=(
            "Search operational Jira tickets using text and structured filters such as status, "
            "priority, issue type, service, environment, platform, cluster, labels, and components."
        ),
    )
    async def search_tickets(
        text: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        issue_type: str | None = None,
        service: str | None = None,
        environment: str | None = None,
        platform: str | None = None,
        cluster: str | None = None,
        labels: list[str] | None = None,
        components: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        try:
            criteria = JiraSearchCriteria(
                text=text,
                status=status,
                priority=priority,
                issue_type=issue_type,
                service=service,
                environment=environment,
                platform=platform,
                cluster=cluster,
                labels=labels,
                components=components,
                limit=limit,
            )
            tickets = await repository.search_tickets(criteria)
        except ValidationError:
            return _error(
                "invalid_search",
                "Search filters are invalid. The result limit must be between 1 and 50.",
            )
        except JiraRepositoryError:
            logger.error("jira_tool.search.repository_error")
            return _error("jira_unavailable", "Unable to search Jira tickets.")

        logger.info("jira_tool.search.success", result_count=len(tickets))
        return {
            "success": True,
            "tickets": [ticket.model_dump(mode="json") for ticket in tickets],
            "count": len(tickets),
            "criteria": criteria.model_dump(mode="json"),
            "source": repository.provider_name,
        }

    @mcp.tool(
        name="find_similar_tickets",
        description=(
            "Find deterministic resolved operational Jira incidents similar to a ticket, including "
            "scores, match reasons, previous resolutions, and applicability guidance."
        ),
    )
    async def find_similar_tickets(ticket_key: str, limit: int = 3) -> dict[str, Any]:
        try:
            matches = await repository.find_similar_tickets(ticket_key, limit=limit)
        except InvalidJiraRequestError as exc:
            return _error("invalid_ticket_key", str(exc))
        except JiraTicketNotFoundError as exc:
            return _error("ticket_not_found", str(exc))
        except ValueError as exc:
            return _error("invalid_limit", str(exc))
        except JiraRepositoryError:
            logger.error("jira_tool.similarity.repository_error")
            return _error("jira_unavailable", "Unable to find similar Jira incidents.")

        logger.info("jira_tool.similarity.success", result_count=len(matches))
        return {
            "success": True,
            "matches": [match.model_dump(mode="json") for match in matches],
            "count": len(matches),
            "source": repository.provider_name,
        }
