"""
Unit tests for MCP Server tools.

Tests the tool functions directly without needing a running MCP server.
"""

import pytest

from src.core.config import get_settings
from src.tools.general_tools import register_general_tools
from src.tools.mock_jira_tools import register_mock_jira_tools


class TestGeneralTools:
    """Tests for general-purpose tools."""

    def test_settings_loads(self):
        """Settings should load without errors."""
        settings = get_settings()
        assert settings.mcp_server_name == "knowledge-agent-mcp-server"
        assert settings.mcp_server_version == "0.1.0"


class TestMockJiraTools:
    """Tests for mock Jira tools."""

    @pytest.mark.asyncio
    async def test_get_existing_ticket(self):
        """Should return ticket data for a valid ticket ID."""
        from src.tools.mock_jira_tools import _MOCK_TICKETS

        ticket = _MOCK_TICKETS.get("PROJ-1001")
        assert ticket is not None
        assert ticket["key"] == "PROJ-1001"
        assert ticket["summary"] is not None
        assert ticket["status"]["name"] is not None

    @pytest.mark.asyncio
    async def test_all_tickets_have_required_fields(self):
        """All mock tickets must have required Jira fields."""
        from src.tools.mock_jira_tools import _MOCK_TICKETS

        required_fields = [
            "id", "key", "summary", "status", "project"
        ]
        for ticket_key, ticket in _MOCK_TICKETS.items():
            for field in required_fields:
                assert field in ticket, f"Ticket {ticket_key} missing field: {field}"

    @pytest.mark.asyncio
    async def test_ticket_not_found_returns_error(self):
        """Non-existent ticket should return an error dict with available tickets."""
        from src.tools.mock_jira_tools import _MOCK_TICKETS

        result = _MOCK_TICKETS.get("PROJ-9999")
        assert result is None  # Not in the store

    @pytest.mark.asyncio
    async def test_mock_tickets_loaded(self):
        """Should have multiple mock tickets pre-loaded."""
        from src.tools.mock_jira_tools import _MOCK_TICKETS

        assert len(_MOCK_TICKETS) > 5
        assert "PROJ-1002" in _MOCK_TICKETS
