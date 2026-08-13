"""
Tests for the FastAPI endpoints ensuring functionality and safe error handling.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, app_state
from src.agent.agent import KnowledgeAgent
from src.core.config import Settings
from src.mcp_client.client import MCPClient

ALLOWED_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "http://localhost:3000"


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


def test_cors_allows_supported_development_origin(
    test_client: TestClient, setup_app_state: None
) -> None:
    """The supported direct-development origin receives an explicit CORS grant."""
    response = test_client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers


def test_cors_does_not_allow_legacy_origin(
    test_client: TestClient, setup_app_state: None
) -> None:
    """Legacy or unconfigured origins must not receive an allow-origin header."""
    response = test_client.get("/health", headers={"Origin": DISALLOWED_ORIGIN})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allows_query_contract(test_client: TestClient) -> None:
    """The browser may preflight the JSON POST used by the direct API path."""
    response = test_client.options(
        "/query",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers


def test_cors_origins_remain_environment_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pydantic settings accept a deployment-provided JSON origin list."""
    configured_origins = ["https://knowledge-agent.example.test"]
    monkeypatch.setenv("API_CORS_ORIGINS", '["https://knowledge-agent.example.test"]')

    configured = Settings(_env_file=None)

    assert configured.api_cors_origins == configured_origins


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


def test_websocket_rejects_invalid_messages(
    test_client: TestClient, setup_app_state: None
) -> None:
    """Malformed, unsupported, and empty query messages receive safe errors."""
    with test_client.websocket_connect("/ws") as websocket:
        websocket.send_text("not-json")
        assert websocket.receive_json() == {
            "type": "error",
            "payload": {"message": "Invalid message format"},
        }

        websocket.send_json({"type": "unsupported", "payload": {}})
        assert websocket.receive_json() == {
            "type": "error",
            "payload": {"message": "Unknown message type: unsupported"},
        }

        websocket.send_json({"type": "query", "payload": {"query": "   "}})
        assert websocket.receive_json() == {
            "type": "error",
            "payload": {"message": "Query cannot be empty"},
        }


def test_websocket_returns_agent_query_error(
    test_client: TestClient, setup_app_state: None
) -> None:
    """An agent-level query failure is returned in the normal response envelope."""
    app_state.agent.process_query.return_value = {
        "success": False,
        "error": "Ticket not found",
        "structured_response": None,
        "timestamp": "2026-08-12T12:00:00Z",
        "processing_ms": 10.0,
    }

    with test_client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "query", "payload": {"query": "PROJ-9999"}})
        assert websocket.receive_json()["type"] == "thinking"
        response = websocket.receive_json()

    assert response["type"] == "response"
    assert response["payload"]["success"] is False
    assert response["payload"]["error"] == "Ticket not found"


def test_websocket_reports_unavailable_agent(test_client: TestClient) -> None:
    """A connected client receives a safe error when the agent is unavailable."""
    app_state.mcp_client = None
    app_state.agent = None

    with test_client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "query", "payload": {"query": "PROJ-1002"}})
        response = websocket.receive_json()

    assert response == {
        "type": "error",
        "payload": {"message": "Agent not available"},
    }
