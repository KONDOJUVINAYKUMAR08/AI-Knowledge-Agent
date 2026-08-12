"""
Unit tests for the LangGraph Knowledge Agent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage

from src.agent.agent import KnowledgeAgent, AgentState, AgentResponseSchema
from src.mcp_client.client import MCPClient, MCPClientError


@pytest.fixture
def mock_mcp_client():
    client = MagicMock(spec=MCPClient)
    # Default mocks
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def agent(mock_mcp_client, monkeypatch):
    # Mock LLM and structured output
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    
    # We patch create_llm in the agent module
    import src.agent.agent as agent_module
    
    def fake_create_llm(settings):
        # Return an object that has with_structured_output
        fake_llm = MagicMock()
        fake_llm.with_structured_output = lambda schema: mock_llm
        return fake_llm
            
    monkeypatch.setattr(agent_module, "create_llm", fake_create_llm)
    
    ag = KnowledgeAgent(mock_mcp_client)
    ag._llm = mock_llm  # Ensure our mock is used
    return ag


@pytest.mark.asyncio
async def test_process_query_valid_ticket(agent, mock_mcp_client):
    # Setup MCP responses
    mock_mcp_client.call_tool.side_effect = lambda name, args: {
        "get_ticket": {"ticket": {"key": "PROJ-1002", "summary": "DB exhaustion"}},
        "find_similar_tickets": {"tickets": [{"key": "PROJ-901"}]}
    }[name]
    
    # Setup LLM response
    agent._llm.ainvoke.return_value = AgentResponseSchema(
        ticket_summary="DB is exhausted.",
        what_we_know="Max connections reached.",
        similar_historical_tickets="PROJ-901",
        previous_resolution="Scaled pool.",
        recommended_investigation="Check metrics.",
        missing_information="None.",
        sources=["mock"]
    )
    
    result = await agent.process_query("Tell me about PROJ-1002")
    
    assert result["success"] is True
    assert result["error"] is None
    assert result["structured_response"]["ticket_summary"] == "DB is exhausted."
    
    # Verify MCP tool calls
    assert mock_mcp_client.call_tool.call_count == 2
    calls = mock_mcp_client.call_tool.call_args_list
    assert calls[0][0][0] == "get_ticket"
    assert calls[0][0][1] == {"ticket_id": "PROJ-1002"}
    assert calls[1][0][0] == "find_similar_tickets"
    assert calls[1][0][1] == {"ticket_id": "PROJ-1002"}


@pytest.mark.asyncio
async def test_process_query_invalid_ticket(agent, mock_mcp_client):
    # Missing ticket ID
    result = await agent.process_query("What's up?")
    
    assert result["success"] is False
    assert result["error"] == "No valid ticket ID found in query."
    assert "structured_response" in result
    assert result["structured_response"]["ticket_summary"] == "Error"
    
    # MCP should NOT be called
    mock_mcp_client.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_process_query_tool_failure(agent, mock_mcp_client):
    # MCP tool logic error
    from src.mcp_client.client import ToolInvocationError
    mock_mcp_client.call_tool.side_effect = ToolInvocationError("Tool returned error: Not found")
    
    result = await agent.process_query("Tell me about PROJ-1002")
    
    assert result["success"] is False
    assert "Tool execution failed" in result["error"]


@pytest.mark.asyncio
async def test_process_query_mcp_failure(agent, mock_mcp_client):
    # MCP transport error
    mock_mcp_client.call_tool.side_effect = MCPClientError("Connection refused")
    
    result = await agent.process_query("Tell me about PROJ-1002")
    
    assert result["success"] is False
    assert "MCP communication failed (Transport/Session)" in result["error"]


@pytest.mark.asyncio
async def test_process_query_llm_failure(agent, mock_mcp_client):
    # Setup MCP responses
    mock_mcp_client.call_tool.return_value = {"ticket": {"key": "PROJ-1002"}}
    
    # Setup LLM failure
    agent._llm.ainvoke.side_effect = Exception("OpenAI API Timeout")
    
    result = await agent.process_query("Tell me about PROJ-1002")
    
    assert result["success"] is True  # Technically workflow finished
    assert "LLM generation failed" in result["structured_response"]["what_we_know"]
    assert "OpenAI API Timeout" in result["structured_response"]["recommended_investigation"]
