"""Typed API contracts for the Knowledge Agent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """Validated natural-language query payload."""

    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=128)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Query cannot be empty or whitespace.")
        return normalized

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class StructuredResponse(BaseModel):
    """Seven-section Knowledge Agent response."""

    ticket_summary: str
    what_we_know: str
    similar_historical_tickets: str
    previous_resolution: str
    recommended_investigation: str
    missing_information: str
    sources: list[str]


class ToolInfo(BaseModel):
    name: str
    description: str | None
    parameters: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    success: bool
    error_code: str | None = None
    error: str | None = None
    structured_response: StructuredResponse | None = None
    timestamp: str
    processing_ms: float
    request_id: str


class LLMStatus(BaseModel):
    provider: str
    model: str
    configured: bool


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    mcp_connected: bool
    available_tools: list[str]
    llm: LLMStatus
    version: str


class ToolsResponse(BaseModel):
    tools: list[ToolInfo]
    count: int


class WebSocketMessage(BaseModel):
    type: Literal["query", "ping"]
    payload: dict[str, Any]
