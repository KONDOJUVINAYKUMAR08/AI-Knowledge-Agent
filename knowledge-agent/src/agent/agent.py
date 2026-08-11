"""
Knowledge Agent — rule-based dispatcher.

Parses user queries and maps them to the appropriate MCP tool.
Designed to be replaced or extended with an LLM dispatcher later.

Architecture: Intent → Tool → MCP Client → Result
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.core.logging import get_logger
from src.mcp_client.client import MCPClient, MCPClientError

logger = get_logger(__name__)


class IntentType(str, Enum):
    """Recognized intent categories."""
    GREETING = "greeting"
    GET_TICKET = "get_ticket"
    SEARCH_TICKETS = "search_tickets"
    GET_PROJECT = "get_project"
    GET_TIME = "get_time"
    LIST_TOOLS = "list_tools"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Result of intent parsing."""
    intent: IntentType
    tool_name: str | None
    arguments: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_query: str = ""


@dataclass
class AgentResponse:
    """Structured response from the agent."""
    success: bool
    intent: IntentType
    tool_name: str | None
    tool_arguments: dict[str, Any]
    result: Any
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    processing_ms: float = 0.0


# Compiled regex patterns for intent matching
_TICKET_ID_PATTERN = re.compile(r"\b([A-Z]+-\d+)\b", re.IGNORECASE)
_GREETING_PATTERN = re.compile(r"\b(hello|hi|hey|greet|test|ping|check)\b", re.IGNORECASE)
_TIME_PATTERN = re.compile(r"\b(time|date|now|current|today|clock|when)\b", re.IGNORECASE)
_PROJECT_PATTERN = re.compile(r"\b(project|overview|summary|team|stats|statistics|board)\b", re.IGNORECASE)
_SEARCH_PATTERN = re.compile(r"\b(search|find|look|list|query|filter|get all)\b", re.IGNORECASE)
_TOOL_LIST_PATTERN = re.compile(r"\b(tools|capabilities|what can you do|help|available)\b", re.IGNORECASE)


class IntentParser:
    """
    Rule-based intent parser.

    Parses free-form user queries into structured intents.
    Replace this class with an LLM-based parser when ready.
    """

    def parse(self, query: str) -> ParsedIntent:
        """Parse user query into a structured intent."""
        query_stripped = query.strip()

        # Priority 1: Explicit ticket ID (e.g., "PROJ-1001")
        ticket_match = _TICKET_ID_PATTERN.search(query_stripped)
        if ticket_match:
            ticket_id = ticket_match.group(1).upper()
            return ParsedIntent(
                intent=IntentType.GET_TICKET,
                tool_name="get_mock_ticket",
                arguments={"ticket_id": ticket_id},
                raw_query=query_stripped,
            )

        # Priority 2: Project overview (before search to avoid false positive)
        if _PROJECT_PATTERN.search(query_stripped):
            return ParsedIntent(
                intent=IntentType.GET_PROJECT,
                tool_name="get_mock_project",
                arguments={},
                raw_query=query_stripped,
            )

        # Priority 3: Search intent
        if _SEARCH_PATTERN.search(query_stripped):
            args = self._extract_search_args(query_stripped)
            return ParsedIntent(
                intent=IntentType.SEARCH_TICKETS,
                tool_name="search_mock_tickets",
                arguments=args,
                raw_query=query_stripped,
            )

        # Priority 4: Time/date query
        if _TIME_PATTERN.search(query_stripped):
            return ParsedIntent(
                intent=IntentType.GET_TIME,
                tool_name="current_time",
                arguments={},
                raw_query=query_stripped,
            )

        # Priority 5: Tool listing
        if _TOOL_LIST_PATTERN.search(query_stripped):
            return ParsedIntent(
                intent=IntentType.LIST_TOOLS,
                tool_name=None,
                arguments={},
                raw_query=query_stripped,
            )

        # Priority 6: Greeting / connectivity test
        if _GREETING_PATTERN.search(query_stripped) or len(query_stripped) <= 10:
            name = self._extract_name(query_stripped) or "User"
            return ParsedIntent(
                intent=IntentType.GREETING,
                tool_name="hello",
                arguments={"name": name},
                raw_query=query_stripped,
            )

        # Fallback: Unknown intent — still try hello
        return ParsedIntent(
            intent=IntentType.UNKNOWN,
            tool_name="hello",
            arguments={"name": "User"},
            confidence=0.3,
            raw_query=query_stripped,
        )

    def _extract_search_args(self, query: str) -> dict[str, str]:
        """Extract search filter parameters from the query text."""
        args: dict[str, str] = {}

        # Status extraction
        status_map = {
            "open": "Open",
            "in progress": "In Progress",
            "done": "Done",
            "backlog": "Backlog",
            "review": "In Review",
            "closed": "Done",
        }
        for keyword, status in status_map.items():
            if keyword in query.lower():
                args["status"] = status
                break

        # Priority extraction
        for priority in ["critical", "high", "medium", "low"]:
            if priority in query.lower():
                args["priority"] = priority.capitalize()
                break

        # Label/component extraction (simple)
        for label in ["security", "authentication", "database", "frontend", "backend", "mobile", "performance"]:
            if label in query.lower():
                args["label"] = label
                break

        # Generic keyword search (use entire query if no specific filters)
        if not args:
            args["query"] = query

        return args

    def _extract_name(self, query: str) -> str | None:
        """Try to extract a name from a greeting."""
        # Match patterns like "hello John", "hi, I'm Alice"
        match = re.search(r"(?:hello|hi|hey)[,\s]+(?:i'?m\s+)?([A-Z][a-z]+)", query, re.IGNORECASE)
        if match:
            return match.group(1)
        return None


class KnowledgeAgent:
    """
    Rule-based Knowledge Agent.

    Orchestrates intent parsing → MCP tool invocation → response formatting.
    The MCP Client is injected for testability (dependency injection pattern).
    """

    def __init__(self, mcp_client: MCPClient) -> None:
        self._client = mcp_client
        self._parser = IntentParser()
        logger.info("knowledge_agent.initialized")

    async def process_query(self, query: str) -> AgentResponse:
        """
        Process a user query end-to-end.

        1. Parse intent
        2. Invoke MCP tool
        3. Return structured response
        """
        start_time = datetime.now(UTC)
        intent = self._parser.parse(query)

        logger.info(
            "agent.processing_query",
            intent=intent.intent.value,
            tool=intent.tool_name,
            args=intent.arguments,
            confidence=intent.confidence,
        )

        # Special case: list available tools
        if intent.intent == IntentType.LIST_TOOLS:
            tools = await self._client.list_tools()
            result = {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema,
                    }
                    for t in tools
                ],
                "count": len(tools),
            }
            return self._build_response(
                success=True,
                intent=intent,
                result=result,
                start_time=start_time,
            )

        # Regular tool invocation
        if not intent.tool_name:
            return self._build_response(
                success=False,
                intent=intent,
                result=None,
                error="Could not determine which tool to invoke for your query.",
                start_time=start_time,
            )

        try:
            result = await self._client.call_tool(intent.tool_name, intent.arguments)
            return self._build_response(
                success=True,
                intent=intent,
                result=result,
                start_time=start_time,
            )
        except MCPClientError as exc:
            logger.error("agent.tool_invocation_error", tool=intent.tool_name, error=str(exc))
            return self._build_response(
                success=False,
                intent=intent,
                result=None,
                error=str(exc),
                start_time=start_time,
            )

    def _build_response(
        self,
        success: bool,
        intent: ParsedIntent,
        result: Any,
        start_time: datetime,
        error: str | None = None,
    ) -> AgentResponse:
        """Build a structured agent response."""
        now = datetime.now(UTC)
        elapsed_ms = (now - start_time).total_seconds() * 1000

        return AgentResponse(
            success=success,
            intent=intent.intent,
            tool_name=intent.tool_name,
            tool_arguments=intent.arguments,
            result=result,
            error=error,
            timestamp=now.isoformat(),
            processing_ms=round(elapsed_ms, 2),
        )
