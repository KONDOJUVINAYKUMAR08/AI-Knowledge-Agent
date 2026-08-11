"""
Unit tests for the IntentParser.

These tests run without any MCP connection.
"""

import pytest

from src.agent.agent import IntentParser, IntentType


@pytest.fixture
def parser() -> IntentParser:
    return IntentParser()


class TestIntentParser:
    def test_ticket_id_extraction(self, parser):
        result = parser.parse("Show me PROJ-1001")
        assert result.intent == IntentType.GET_TICKET
        assert result.tool_name == "get_mock_ticket"
        assert result.arguments["ticket_id"] == "PROJ-1001"

    def test_ticket_id_case_insensitive(self, parser):
        result = parser.parse("get ticket proj-1002")
        assert result.intent == IntentType.GET_TICKET
        assert result.arguments["ticket_id"] == "PROJ-1002"

    def test_search_intent(self, parser):
        result = parser.parse("search for open tickets")
        assert result.intent == IntentType.SEARCH_TICKETS
        assert result.tool_name == "search_mock_tickets"

    def test_search_with_priority(self, parser):
        result = parser.parse("find all critical bugs")
        assert result.intent == IntentType.SEARCH_TICKETS
        assert result.arguments.get("priority") == "Critical"

    def test_search_with_status(self, parser):
        result = parser.parse("list in progress stories")
        assert result.intent == IntentType.SEARCH_TICKETS
        assert result.arguments.get("status") == "In Progress"

    def test_project_intent(self, parser):
        result = parser.parse("show me the project overview")
        assert result.intent == IntentType.GET_PROJECT
        assert result.tool_name == "get_mock_project"

    def test_time_intent(self, parser):
        result = parser.parse("what time is it?")
        assert result.intent == IntentType.GET_TIME
        assert result.tool_name == "current_time"

    def test_greeting_intent(self, parser):
        result = parser.parse("hello")
        assert result.intent == IntentType.GREETING
        assert result.tool_name == "hello"

    def test_tools_listing_intent(self, parser):
        result = parser.parse("what tools are available?")
        assert result.intent == IntentType.LIST_TOOLS

    def test_ticket_takes_priority_over_search(self, parser):
        """Ticket ID should take priority even if query also contains 'search'."""
        result = parser.parse("search for PROJ-1003 details")
        assert result.intent == IntentType.GET_TICKET
        assert result.arguments["ticket_id"] == "PROJ-1003"

    def test_unknown_returns_default(self, parser):
        """Completely unrecognized input should not crash."""
        result = parser.parse("xyzzy florp blarg")
        assert result.intent == IntentType.UNKNOWN
        assert result.tool_name is not None  # Should have a fallback
