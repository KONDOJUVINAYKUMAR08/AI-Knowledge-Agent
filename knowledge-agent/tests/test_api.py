"""Behavior and safety tests for FastAPI REST and WebSocket contracts."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.agent.agent import KnowledgeAgent
from src.api.main import app, app_state
from src.core.config import Settings
from src.mcp_client.client import MCPClient, MCPClientError

ALLOWED_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "http://localhost:3000"


class DummyTool:
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"{name} description"
        self.input_schema = {"type": "object"}


CORE_TOOLS = [
    DummyTool("get_ticket"),
    DummyTool("search_tickets"),
    DummyTool("find_similar_tickets"),
]


def _structured_response():
    return {
        "ticket_summary": "PROJ-1002 summary",
        "what_we_know": "Verified facts",
        "similar_historical_tickets": "PROJ-908",
        "previous_resolution": "Separated backup traffic",
        "recommended_investigation": "Recommended checks",
        "missing_information": "Current pool configuration",
        "sources": ["PROJ-1002", "PROJ-908"],
    }


def _agent_response(*, success=True, error_code=None, error=None):
    return {
        "success": success,
        "error_code": error_code,
        "error": error,
        "structured_response": _structured_response(),
        "timestamp": "2026-08-14T12:00:00+00:00",
        "processing_ms": 125.0,
    }


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_agent(monkeypatch) -> KnowledgeAgent:
    mock_mcp = AsyncMock(spec=MCPClient)
    mock_mcp.is_connected = True
    mock_mcp.available_tools = CORE_TOOLS
    mock_mcp.list_tools.return_value = CORE_TOOLS

    agent = AsyncMock(spec=KnowledgeAgent)
    agent.mcp_client = mock_mcp
    agent.llm_provider = "gemini"
    agent.llm_model = "gemini-3.5-flash"
    agent.process_query.return_value = _agent_response()
    monkeypatch.setattr("src.api.main._llm_is_configured", lambda settings: True)
    return agent


@pytest.fixture
def setup_app_state(mock_agent: KnowledgeAgent):
    app_state.mcp_client = mock_agent.mcp_client
    app_state.agent = mock_agent
    yield
    app_state.mcp_client = None
    app_state.agent = None


def test_health_actively_reports_three_core_tools(
    test_client: TestClient, setup_app_state: None
) -> None:
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mcp_connected"] is True
    assert data["available_tools"] == [
        "find_similar_tickets",
        "get_ticket",
        "search_tickets",
    ]
    assert data["llm"] == {
        "provider": "gemini",
        "model": "gemini-3.5-flash",
        "configured": True,
    }
    app_state.mcp_client.list_tools.assert_awaited()


def test_health_is_degraded_when_live_mcp_probe_fails(
    test_client: TestClient, setup_app_state: None
) -> None:
    app_state.mcp_client.list_tools.side_effect = MCPClientError("transport failed")

    response = test_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["mcp_connected"] is False
    assert data["available_tools"] == []


def test_cors_allows_supported_development_origin(
    test_client: TestClient, setup_app_state: None
) -> None:
    response = test_client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers


def test_cors_does_not_allow_legacy_origin(
    test_client: TestClient, setup_app_state: None
) -> None:
    response = test_client.get("/health", headers={"Origin": DISALLOWED_ORIGIN})

    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allows_query_contract(test_client: TestClient) -> None:
    response = test_client.options(
        "/query",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,X-Request-ID",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "x-request-id" in response.headers["access-control-allow-headers"].lower()


def test_cors_origins_remain_environment_configurable(monkeypatch) -> None:
    monkeypatch.setenv("API_CORS_ORIGINS", '["https://knowledge-agent.example.test"]')

    configured = Settings(_env_file=None)

    assert configured.api_cors_origins == ["https://knowledge-agent.example.test"]


def test_list_tools_returns_current_mcp_schemas(
    test_client: TestClient, setup_app_state: None
) -> None:
    response = test_client.get("/tools")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert {tool["name"] for tool in data["tools"]} == {
        "get_ticket",
        "search_tickets",
        "find_similar_tickets",
    }
    assert all(tool["parameters"] == {"type": "object"} for tool in data["tools"])


def test_query_returns_typed_response_and_correlation_id(
    test_client: TestClient, setup_app_state: None
) -> None:
    response = test_client.post(
        "/query",
        json={"query": "Help me understand PROJ-1002"},
        headers={"X-Request-ID": "request-12345"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-12345"
    data = response.json()
    assert data["request_id"] == "request-12345"
    assert data["success"] is True
    assert set(data["structured_response"]) == {
        "ticket_summary",
        "what_we_know",
        "similar_historical_tickets",
        "previous_resolution",
        "recommended_investigation",
        "missing_information",
        "sources",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"query": ""},
        {"query": "   "},
        {"query": 123},
        {"query": "x" * 2001},
    ],
)
def test_query_validation_is_strict_and_does_not_echo_input(
    test_client: TestClient, setup_app_state: None, payload
) -> None:
    response = test_client.post("/query", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["detail"] == "Invalid request parameters."
    assert all("input" not in error for error in data["errors"])
    assert "x" * 100 not in str(data)


def test_ticket_not_found_uses_404_with_safe_typed_body(
    test_client: TestClient, setup_app_state: None
) -> None:
    app_state.agent.process_query.return_value = _agent_response(
        success=False,
        error_code="ticket_not_found",
        error="Jira ticket PROJ-9999 was not found.",
    )

    response = test_client.post("/query", json={"query": "Get PROJ-9999"})

    assert response.status_code == 404
    assert response.json()["error_code"] == "ticket_not_found"
    assert "Traceback" not in response.text


def test_provider_timeout_uses_504_without_internal_details(
    test_client: TestClient, setup_app_state: None
) -> None:
    app_state.agent.process_query.return_value = _agent_response(
        success=False,
        error_code="llm_timeout",
        error="The Knowledge Agent timed out while generating the analysis. Please try again.",
    )

    response = test_client.post("/query", json={"query": "Help me understand PROJ-1002"})

    assert response.status_code == 504
    assert "timed out" in response.json()["error"]


def test_unhandled_query_error_is_sanitized(
    test_client: TestClient, setup_app_state: None
) -> None:
    app_state.agent.process_query.side_effect = RuntimeError(
        "SECRET_API_KEY at C:/internal/path"
    )

    response = test_client.post("/query", json={"query": "Help me understand PROJ-1002"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error. Please try again later."}
    assert "SECRET_API_KEY" not in response.text


def test_websocket_ping_query_and_repeated_query(
    test_client: TestClient, setup_app_state: None
) -> None:
    with test_client.websocket_connect(
        "/ws", headers={"Origin": "http://testserver"}
    ) as websocket:
        websocket.send_json(
            {"type": "ping", "payload": {"request_id": "ping-12345"}}
        )
        pong = websocket.receive_json()
        assert pong == {"type": "pong", "payload": {"request_id": "ping-12345"}}

        for request_id in ("query-12345", "query-67890"):
            websocket.send_json(
                {
                    "type": "query",
                    "payload": {
                        "query": "Help me understand PROJ-1002",
                        "request_id": request_id,
                    },
                }
            )
            thinking = websocket.receive_json()
            result = websocket.receive_json()
            assert thinking == {"type": "thinking", "payload": {"request_id": request_id}}
            assert result["type"] == "response"
            assert result["payload"]["success"] is True
            assert result["payload"]["request_id"] == request_id


def test_websocket_rejects_invalid_messages_and_recovers(
    test_client: TestClient, setup_app_state: None
) -> None:
    with test_client.websocket_connect("/ws") as websocket:
        websocket.send_text("not-json")
        assert websocket.receive_json()["payload"]["message"] == "Invalid message format"

        websocket.send_json({"type": "unsupported", "payload": {}})
        assert websocket.receive_json()["payload"]["message"] == "Unsupported message type"

        websocket.send_json({"type": "query", "payload": {"query": "   "}})
        assert websocket.receive_json()["payload"]["message"] == "Invalid query"

        websocket.send_json({"type": "ping", "payload": {"request_id": "recover-123"}})
        assert websocket.receive_json()["type"] == "pong"


def test_websocket_rejects_cross_site_origin(
    test_client: TestClient, setup_app_state: None
) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info, test_client.websocket_connect(
        "/ws", headers={"Origin": "https://evil.example.test"}
    ):
        pass

    assert exc_info.value.code == 1008


def test_websocket_reports_unavailable_agent_safely(
    test_client: TestClient, setup_app_state: None, monkeypatch
) -> None:
    monkeypatch.setattr(
        app_state,
        "refresh",
        AsyncMock(side_effect=MCPClientError("SECRET internal transport")),
    )

    with test_client.websocket_connect("/ws") as websocket:
        websocket.send_json(
            {
                "type": "query",
                "payload": {"query": "Get PROJ-1002", "request_id": "request-99999"},
            }
        )
        response = websocket.receive_json()

    assert response["type"] == "error"
    assert response["payload"]["message"] == "The Knowledge Agent is temporarily unavailable."
    assert "SECRET" not in str(response)
