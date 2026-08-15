"""Behavior tests for the operational Jira MCP tool contracts."""

from typing import Any

import pytest

from src.core.config import Settings
from src.jira.factory import create_jira_repository
from src.jira.mock_repository import build_mock_repository
from src.tools.jira_tools import register_jira_tools


class CaptureMCPServer:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, name: str, description: str):
        def decorator(function):
            self.tools[name] = function
            return function

        return decorator


@pytest.fixture
def tools():
    server = CaptureMCPServer()
    register_jira_tools(server, build_mock_repository())
    return server.tools


def test_only_operational_jira_tools_are_registered(tools):
    assert set(tools) == {"get_ticket", "search_tickets", "find_similar_tickets"}


@pytest.mark.asyncio
async def test_get_ticket_tool_success(tools):
    response = await tools["get_ticket"](" proj-1002 ")

    assert response["success"] is True
    assert response["ticket"]["key"] == "PROJ-1002"
    assert response["source"] == "mock"


@pytest.mark.asyncio
async def test_get_ticket_tool_not_found(tools):
    response = await tools["get_ticket"]("PROJ-9999")

    assert response == {
        "success": False,
        "error": {
            "code": "ticket_not_found",
            "message": "Jira ticket PROJ-9999 was not found.",
        },
    }


@pytest.mark.asyncio
async def test_get_ticket_tool_rejects_malformed_key(tools):
    response = await tools["get_ticket"]("invalid")

    assert response["success"] is False
    assert response["error"]["code"] == "invalid_ticket_key"
    assert "Traceback" not in str(response)


@pytest.mark.asyncio
async def test_search_tool_supports_operational_filters(tools):
    response = await tools["search_tickets"](
        priority="Critical",
        platform="Apache Kafka",
        environment="production",
    )

    assert response["success"] is True
    assert [ticket["key"] for ticket in response["tickets"]] == ["PROJ-909"]


@pytest.mark.asyncio
async def test_search_tool_rejects_invalid_limit(tools):
    response = await tools["search_tickets"](limit=0)

    assert response["success"] is False
    assert response["error"]["code"] == "invalid_search"


@pytest.mark.asyncio
async def test_find_similar_tool_returns_explainable_match(tools):
    response = await tools["find_similar_tickets"]("PROJ-1002")

    assert response["success"] is True
    first = response["matches"][0]
    assert first["ticket"]["key"] == "PROJ-908"
    assert first["similarity_score"] > 0
    assert first["match_reasons"]
    assert first["historical_resolved"] is True
    assert first["previous_resolution"]
    assert first["applicability"]


def test_repository_factory_rejects_unconfigured_real_provider():
    settings = Settings(jira_provider="real")

    with pytest.raises(ValueError, match="Real Jira integration requires JIRA_BASE_URL"):
        create_jira_repository(settings)
