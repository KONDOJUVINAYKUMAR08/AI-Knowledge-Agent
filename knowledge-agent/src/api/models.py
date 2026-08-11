"""
Pydantic request/response models for the Knowledge Agent API.
"""

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """User query request payload."""
    query: str = Field(..., min_length=1, max_length=2000, description="User's natural language query")
    session_id: str | None = Field(default=None, description="Optional session identifier for conversation tracking")


class ToolInfo(BaseModel):
    """Information about an available MCP tool."""
    name: str
    description: str | None
    parameters: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    """Agent query response."""
    success: bool
    query: str
    intent: str
    tool_name: str | None
    tool_arguments: dict[str, Any]
    result: Any
    error: str | None = None
    timestamp: str
    processing_ms: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    mcp_connected: bool
    available_tools: list[str]
    version: str


class ToolsResponse(BaseModel):
    """List of available tools."""
    tools: list[ToolInfo]
    count: int


class WebSocketMessage(BaseModel):
    """WebSocket message envelope."""
    type: str  # "query" | "response" | "error" | "ping"
    payload: dict[str, Any]
