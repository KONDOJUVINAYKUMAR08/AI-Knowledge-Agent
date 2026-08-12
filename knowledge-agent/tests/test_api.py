"""
Tests for the FastAPI endpoints ensuring functionality and safe error handling.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, app_state
from src.agent.agent import KnowledgeAgent
from src.mcp_client.client import MCPClient


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_agent() -> KnowledgeAgent:
    """Provides a mocked agent to avoid real LLM/MCP calls during API testing."""
    mock_mcp = AsyncMock(spec=MCPClient)
    mock_mcp.is_connected = True
    
    class DummyTool:
        name = "dummy_tool"
        description = "A dummy tool"
        inputSchema = {}

    mock_mcp.available_tools = [DummyTool()]
    mock_mcp.list_tools.return_value = [DummyTool()]

    agent = AsyncMock(spec=KnowledgeAgent)
    agent.mcp_client = mock_mcp
    return agent


@pytest.fixture
def setup_app_state(mock_agent: KnowledgeAgent) -> None:
    """Injects the mock agent into the global app state."""
    app_state.mcp_client = mock_agent.mcp_client
    app_state.agent = mock_agent
    yield
    app_state.mcp_client = None
    app_state.agent = None


def test_health_check(test_client: TestClient, setup_app_state: None) -> None:
    """Test the health check endpoint returns 200 and expected schema."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mcp_connected"] is True
    assert "dummy_tool" in data["available_tools"]


def test_list_tools(test_client: TestClient, setup_app_state: None) -> None:
    """Test the tools endpoint returns available tools."""
    response = test_client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tools"][0]["name"] == "dummy_tool"


def test_query_valid(test_client: TestClient, setup_app_state: None) -> None:
    """Test a valid query returns a structured response without errors."""
    mock_response = {
        "success": True,
        "error": None,
        "structured_response": {"answer": "PROJ-1002 is fixed"},
        "timestamp": "2026-08-12T12:00:00Z",
        "processing_ms": 150.0
    }
    app_state.agent.process_query.return_value = mock_response

    response = test_client.post("/query", json={"query": "Help me understand PROJ-1002"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["structured_response"]["answer"] == "PROJ-1002 is fixed"


def test_query_missing_payload(test_client: TestClient, setup_app_state: None) -> None:
    """Test that missing required fields trigger a 422 Unprocessable Entity."""
    response = test_client.post("/query", json={"session_id": "123"})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "Invalid request parameters" in data["detail"]
    assert "errors" in data


def test_query_invalid_payload(test_client: TestClient, setup_app_state: None) -> None:
    """Test that empty queries (failing min_length=1) trigger a 422."""
    response = test_client.post("/query", json={"query": ""})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "Invalid request parameters" in data["detail"]


def test_query_internal_error_safe(test_client: TestClient, setup_app_state: None) -> None:
    """Test that unhandled agent exceptions result in a safe 500 error."""
    # Force the mock to raise a simulated internal error (e.g., API key failure, connection drop)
    app_state.agent.process_query.side_effect = Exception("SECRET_API_KEY_ERROR")

    response = test_client.post("/query", json={"query": "Help me understand PROJ-1002"})
    assert response.status_code == 500
    data = response.json()
    # Ensure the secret error is NOT in the response
    assert "SECRET_API_KEY_ERROR" not in str(data)
    assert data["detail"] == "Internal server error. Please try again later."


def test_websocket_flow(test_client: TestClient, setup_app_state: None) -> None:
    """Test the WebSocket connection accepts queries and returns responses."""
    mock_response = {
        "success": True,
        "error": None,
        "structured_response": {"ticket_summary": "Test"},
        "timestamp": "2026-08-12T12:00:00Z",
        "processing_ms": 100.0
    }
    app_state.agent.process_query.return_value = mock_response

    with test_client.websocket_connect("/ws") as websocket:
        # Send a ping
        websocket.send_json({"type": "ping", "payload": {}})
        data = websocket.receive_json()
        assert data["type"] == "pong"

        # Send a query
        websocket.send_json({"type": "query", "payload": {"query": "Test query"}})
        
        # Should receive thinking event first
        data = websocket.receive_json()
        assert data["type"] == "thinking"
        
        # Then receive the response
        data = websocket.receive_json()
        assert data["type"] == "response"
        assert data["payload"]["success"] is True
