"""Behavior tests for agent intent routing and safe generation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent.agent import AgentResponseSchema, KnowledgeAgent
from src.core.config import Settings
from src.mcp_client.client import MCPClient, MCPClientError


@pytest.fixture
def mock_mcp_client():
    client = MagicMock(spec=MCPClient)
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def structured_llm():
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def agent(mock_mcp_client, structured_llm, monkeypatch):
    import src.agent.agent as agent_module

    base_llm = MagicMock()
    base_llm.with_structured_output.return_value = structured_llm
    monkeypatch.setattr(agent_module, "create_llm", lambda settings: base_llm)
    settings = Settings(
        google_api_key="test-key",
        llm_max_retries=0,
        llm_retry_backoff_seconds=0,
    )
    return KnowledgeAgent(mock_mcp_client, settings=settings)


def _ticket(key="PROJ-1002"):
    return {
        "key": key,
        "summary": "Database connection pool exhaustion under peak load",
        "status": "Investigating",
        "priority": "Critical",
        "severity": "SEV-1",
        "service": "postgres-cluster",
        "platform": "PostgreSQL",
        "environment": "production",
        "cluster": "prod-postgres-primary",
        "symptoms": ["connection pool exhaustion"],
        "resolution": None,
        "root_cause": None,
    }


def _similar_match():
    return {
        "ticket": {
            **_ticket("PROJ-908"),
            "summary": "PostgreSQL connection pool exhaustion during backup",
        },
        "similarity_score": 100,
        "match_reasons": ["Same service: postgres-cluster"],
        "historical_resolved": True,
        "previous_resolution": "Separated backup connections.",
        "applicability": "High: validate current evidence.",
    }


def _llm_response():
    return AgentResponseSchema(
        ticket_summary="Verified PROJ-1002 summary",
        what_we_know="Verified facts",
        similar_historical_tickets="PROJ-908",
        previous_resolution="Separated backup connections.",
        recommended_investigation="Recommended checks",
        missing_information="Application pool configuration",
        sources=["PROJ-1002", "PROJ-908"],
    )


@pytest.mark.asyncio
async def test_get_ticket_intent_calls_only_get_ticket(agent, mock_mcp_client):
    mock_mcp_client.call_tool.return_value = {
        "success": True,
        "ticket": _ticket(),
    }

    result = await agent.process_query("Get PROJ-1002")

    assert result["success"] is True
    mock_mcp_client.call_tool.assert_awaited_once_with(
        "get_ticket", {"ticket_key": "PROJ-1002"}
    )
    assert "PROJ-1002" in result["structured_response"]["ticket_summary"]


@pytest.mark.asyncio
async def test_search_intent_routes_operational_filters(agent, mock_mcp_client):
    mock_mcp_client.call_tool.return_value = {
        "success": True,
        "tickets": [_ticket("PROJ-909")],
    }

    result = await agent.process_query("Find critical Kafka incidents")

    assert result["success"] is True
    tool_name, arguments = mock_mcp_client.call_tool.await_args.args
    assert tool_name == "search_tickets"
    assert arguments["priority"] == "Critical"
    assert arguments["platform"] == "Apache Kafka"
    assert arguments["issue_type"] == "Incident"


@pytest.mark.asyncio
async def test_similarity_intent_calls_similarity_tool(agent, mock_mcp_client):
    mock_mcp_client.call_tool.return_value = {
        "success": True,
        "matches": [_similar_match()],
    }

    result = await agent.process_query("Find similar incidents to PROJ-1002")

    assert result["success"] is True
    mock_mcp_client.call_tool.assert_awaited_once_with(
        "find_similar_tickets", {"ticket_key": "PROJ-1002"}
    )
    assert "PROJ-908" in result["structured_response"]["similar_historical_tickets"]


@pytest.mark.asyncio
async def test_investigation_workflow_uses_ticket_similarity_and_llm(
    agent, mock_mcp_client, structured_llm
):
    mock_mcp_client.call_tool.side_effect = [
        {"success": True, "ticket": _ticket()},
        {"success": True, "matches": [_similar_match()]},
    ]
    structured_llm.ainvoke.return_value = _llm_response()

    result = await agent.process_query("Help me understand PROJ-1002")

    assert result["success"] is True
    assert result["structured_response"]["sources"] == ["PROJ-1002", "PROJ-908"]
    assert [call.args[0] for call in mock_mcp_client.call_tool.await_args_list] == [
        "get_ticket",
        "find_similar_tickets",
    ]
    messages = structured_llm.ainvoke.await_args.args[0]
    assert "Use only the supplied Jira evidence" in messages[0].content
    assert "PROJ-1002" in messages[1].content
    assert "PROJ-908" in messages[1].content


@pytest.mark.asyncio
async def test_capabilities_request_is_truthful(agent, mock_mcp_client, structured_llm):
    result = await agent.process_query("What can you help me with?")

    assert result["success"] is True
    assert "search operational incidents" in result["structured_response"]["what_we_know"].lower()
    assert "does not directly access clusters" in result["structured_response"]["missing_information"]
    mock_mcp_client.call_tool.assert_not_awaited()
    structured_llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_unsupported_request_returns_safe_failure(agent, mock_mcp_client):
    result = await agent.process_query("Write a marketing email")

    assert result["success"] is False
    assert result["error_code"] == "unsupported_request"
    assert "retrieve Jira tickets" in result["error"]
    mock_mcp_client.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_ticket_not_found_is_clean(agent, mock_mcp_client):
    mock_mcp_client.call_tool.return_value = {
        "success": False,
        "error": {
            "code": "ticket_not_found",
            "message": "Jira ticket PROJ-9999 was not found.",
        },
    }

    result = await agent.process_query("Get PROJ-9999")

    assert result["success"] is False
    assert result["error_code"] == "ticket_not_found"
    assert result["error"] == "Jira ticket PROJ-9999 was not found."
    assert "Traceback" not in str(result)


@pytest.mark.asyncio
async def test_mcp_transport_failure_does_not_expose_exception(agent, mock_mcp_client):
    mock_mcp_client.call_tool.side_effect = MCPClientError(
        "Connection refused at C:/internal/path?token=secret"
    )

    result = await agent.process_query("Get PROJ-1002")

    assert result["success"] is False
    assert result["error_code"] == "knowledge_service_unavailable"
    assert "secret" not in str(result)
    assert "internal/path" not in str(result)


@pytest.mark.asyncio
async def test_provider_failure_is_safe_and_unsuccessful(
    agent, mock_mcp_client, structured_llm
):
    mock_mcp_client.call_tool.side_effect = [
        {"success": True, "ticket": _ticket()},
        {"success": True, "matches": [_similar_match()]},
    ]
    structured_llm.ainvoke.side_effect = RuntimeError("SECRET_API_KEY provider failure")

    result = await agent.process_query("Help me understand PROJ-1002")

    assert result["success"] is False
    assert result["error_code"] == "llm_provider_unavailable"
    assert "temporarily unavailable" in result["error"]
    assert "SECRET_API_KEY" not in str(result)


@pytest.mark.asyncio
async def test_malformed_llm_output_is_safe(agent, mock_mcp_client, structured_llm):
    mock_mcp_client.call_tool.side_effect = [
        {"success": True, "ticket": _ticket()},
        {"success": True, "matches": [_similar_match()]},
    ]
    structured_llm.ainvoke.return_value = {"ticket_summary": "Incomplete"}

    result = await agent.process_query("Help me understand PROJ-1002")

    assert result["success"] is False
    assert result["error_code"] == "llm_invalid_response"
    assert "invalid structured response" in result["error"]


@pytest.mark.asyncio
async def test_ungrounded_llm_source_is_rejected(agent, mock_mcp_client, structured_llm):
    mock_mcp_client.call_tool.side_effect = [
        {"success": True, "ticket": _ticket()},
        {"success": True, "matches": [_similar_match()]},
    ]
    response = _llm_response()
    response.sources.append("PROJ-9999")
    structured_llm.ainvoke.return_value = response

    result = await agent.process_query("Help me understand PROJ-1002")

    assert result["success"] is False
    assert result["error_code"] == "llm_invalid_response"
    assert "PROJ-9999" not in str(result)


@pytest.mark.asyncio
async def test_provider_retry_recovers_with_grounded_response(
    mock_mcp_client, structured_llm, monkeypatch
):
    import src.agent.agent as agent_module

    base_llm = MagicMock()
    base_llm.with_structured_output.return_value = structured_llm
    structured_llm.ainvoke.side_effect = [RuntimeError("temporary failure"), _llm_response()]
    monkeypatch.setattr(agent_module, "create_llm", lambda settings: base_llm)
    retry_agent = KnowledgeAgent(
        mock_mcp_client,
        settings=Settings(
            google_api_key="test-key",
            llm_max_retries=1,
            llm_retry_backoff_seconds=0,
        ),
    )
    mock_mcp_client.call_tool.side_effect = [
        {"success": True, "ticket": _ticket()},
        {"success": True, "matches": [_similar_match()]},
    ]

    result = await retry_agent.process_query("Help me understand PROJ-1002")

    assert result["success"] is True
    assert structured_llm.ainvoke.await_count == 2


@pytest.mark.asyncio
async def test_llm_timeout_is_safe(mock_mcp_client, structured_llm, monkeypatch):
    import src.agent.agent as agent_module

    async def slow_response(*args, **kwargs):
        await asyncio.sleep(0.1)
        return _llm_response()

    base_llm = MagicMock()
    base_llm.with_structured_output.return_value = structured_llm
    structured_llm.ainvoke.side_effect = slow_response
    monkeypatch.setattr(agent_module, "create_llm", lambda settings: base_llm)
    settings = Settings(
        google_api_key="test-key",
        llm_timeout_seconds=0.01,
        llm_max_retries=0,
    )
    timeout_agent = KnowledgeAgent(mock_mcp_client, settings=settings)
    mock_mcp_client.call_tool.side_effect = [
        {"success": True, "ticket": _ticket()},
        {"success": True, "matches": [_similar_match()]},
    ]

    result = await timeout_agent.process_query("Help me understand PROJ-1002")

    assert result["success"] is False
    assert result["error_code"] == "llm_timeout"
    assert "timed out" in result["error"]
