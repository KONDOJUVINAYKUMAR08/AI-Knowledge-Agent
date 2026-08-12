import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcp.types import Tool
from src.mcp_client.client import MCPClient, MCPClientError, ToolInvocationError

@pytest.fixture
def mock_mcp_session():
    session = AsyncMock()
    # Setup list_tools
    session.list_tools.return_value.tools = [
        Tool(name="get_ticket", description="Get a ticket", inputSchema={})
    ]
    return session


@pytest.fixture
def mock_streamable():
    cm = AsyncMock()
    cm.__aenter__.return_value = (AsyncMock(), AsyncMock())
    return cm


@pytest.fixture
def mock_session_cm(mock_mcp_session):
    cm = AsyncMock()
    cm.__aenter__.return_value = mock_mcp_session
    return cm


@pytest.mark.asyncio
async def test_successful_mcp_tool_call(mock_mcp_session, mock_streamable, mock_session_cm):
    with patch("src.mcp_client.client.streamable_http_client", return_value=mock_streamable), \
         patch("src.mcp_client.client.ClientSession", return_value=mock_session_cm):
         
        client = MCPClient()
        await client.connect()
        assert client.is_connected
        
        # Mock successful tool call
        mock_result = MagicMock()
        mock_result.isError = False
        mock_content = MagicMock()
        mock_content.text = '{"success": true}'
        mock_result.content = [mock_content]
        
        mock_mcp_session.call_tool.return_value = mock_result
        
        res = await client.call_tool("get_ticket", {"ticket_id": "PROJ-1002"})
        assert res == {"success": True}


@pytest.mark.asyncio
async def test_tool_returning_iserror_true(mock_mcp_session, mock_streamable, mock_session_cm):
    with patch("src.mcp_client.client.streamable_http_client", return_value=mock_streamable), \
         patch("src.mcp_client.client.ClientSession", return_value=mock_session_cm):
         
        client = MCPClient()
        await client.connect()
        
        # Mock tool returning isError=True
        mock_result = MagicMock()
        mock_result.isError = True
        mock_result.content = "Mock tool logic error"
        
        mock_mcp_session.call_tool.return_value = mock_result
        
        with pytest.raises(ToolInvocationError, match="Mock tool logic error"):
            await client.call_tool("get_ticket", {})
            
        # Should not disconnect on tool error
        assert client.is_connected


@pytest.mark.asyncio
async def test_mcp_connection_failure():
    with patch("src.mcp_client.client.streamable_http_client", side_effect=Exception("Network down")):
        client = MCPClient()
        with pytest.raises(MCPClientError, match="Failed to connect"):
            await client.connect()
        assert not client.is_connected


@pytest.mark.asyncio
async def test_timeout_transport_failure(mock_mcp_session, mock_streamable, mock_session_cm):
    with patch("src.mcp_client.client.streamable_http_client", return_value=mock_streamable), \
         patch("src.mcp_client.client.ClientSession", return_value=mock_session_cm):
         
        client = MCPClient()
        await client.connect()
        
        mock_mcp_session.call_tool.side_effect = asyncio.TimeoutError("Timeout")
        
        with pytest.raises(MCPClientError, match="timed out"):
            await client.call_tool("get_ticket", {})
            
        # Should disconnect on timeout
        assert not client.is_connected


@pytest.mark.asyncio
async def test_reconnect_after_failure(mock_mcp_session, mock_streamable, mock_session_cm):
    with patch("src.mcp_client.client.streamable_http_client", return_value=mock_streamable), \
         patch("src.mcp_client.client.ClientSession", return_value=mock_session_cm):
         
        client = MCPClient()
        await client.connect()
        assert client.is_connected
        
        # Force a transport disconnect
        mock_mcp_session.call_tool.side_effect = Exception("Transport drop")
        with pytest.raises(MCPClientError, match="Transport/Session failed"):
            await client.call_tool("get_ticket", {})
            
        assert not client.is_connected
        
        # Next call should auto-reconnect
        mock_mcp_session.call_tool.side_effect = None
        mock_result = MagicMock()
        mock_result.isError = False
        mock_result.content = []
        mock_mcp_session.call_tool.return_value = mock_result
        
        res = await client.call_tool("get_ticket", {})
        assert client.is_connected


@pytest.mark.asyncio
async def test_safe_disconnect(mock_streamable, mock_session_cm):
    with patch("src.mcp_client.client.streamable_http_client", return_value=mock_streamable), \
         patch("src.mcp_client.client.ClientSession", return_value=mock_session_cm):
         
        client = MCPClient()
        await client.connect()
        assert client.is_connected
        
        await client.disconnect()
        assert not client.is_connected
        
        # Double disconnect should be safe
        await client.disconnect()
        assert not client.is_connected


@pytest.mark.asyncio
async def test_concurrent_reconnect():
    # Better test for concurrent reconnect using real logic
    cm = AsyncMock()
    cm.__aenter__.return_value = (AsyncMock(), AsyncMock())
    
    session_cm = AsyncMock()
    session = AsyncMock()
    session.list_tools.return_value.tools = [Tool(name="t1", description="t1", inputSchema={})]
    session_cm.__aenter__.return_value = session
    
    with patch("src.mcp_client.client.streamable_http_client", return_value=cm) as mock_streamable, \
         patch("src.mcp_client.client.ClientSession", return_value=session_cm):
        
        real_client = MCPClient()
        
        # Ensure concurrent tools calls trigger connect exactly once
        session.call_tool.return_value = MagicMock(isError=False, content=[])
        
        # Fire multiple concurrent calls
        await asyncio.gather(
            real_client.call_tool("t1", {}),
            real_client.call_tool("t1", {}),
            real_client.call_tool("t1", {})
        )
        
        # streamable_http_client should only have been called ONCE
        assert mock_streamable.call_count == 1
        assert real_client.is_connected
