"""
MCP Client wrapper.

Manages a connection to the MCP Server via Streamable HTTP transport.
Provides a clean async interface for tool discovery and invocation.

Compatible with MCP SDK v2.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""


class ToolNotFoundError(MCPClientError):
    """Raised when a requested tool does not exist on the server."""


class ToolInvocationError(MCPClientError):
    """Raised when a tool invocation fails."""


class MCPClient:
    """
    Async MCP client that manages a long-lived connection to the MCP server.

    The client uses streamable_http_client as an async context manager and must remain
    within its scope for the entire duration of use.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._session: ClientSession | None = None
        self._connected = False
        self._available_tools: dict[str, Tool] = {}
        # Holds the live client context manager
        self._http_cm = None
        self._session_cm = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def available_tools(self) -> list[Tool]:
        return list(self._available_tools.values())

    async def connect(self) -> None:
        """Start the MCP session over Streamable HTTP."""
        async with self._lock:
            await self._locked_connect()

    async def _locked_connect(self) -> None:
        """Internal connect that requires the caller to hold the lock."""
        if self._connected:
            logger.warning("mcp_client.already_connected")
            return

        server_url = self._settings.mcp_server_url
        logger.info(
            "mcp_client.connecting",
            url=server_url,
        )

        try:
            self._http_cm = streamable_http_client(url=server_url)
            read_stream, write_stream = await self._http_cm.__aenter__()

            self._session_cm = ClientSession(read_stream, write_stream)
            self._session = await self._session_cm.__aenter__()
            await self._session.initialize()

            await self._refresh_tools()
            self._connected = True
            logger.info(
                "mcp_client.connected",
                tool_count=len(self._available_tools),
                tools=list(self._available_tools.keys()),
            )
        except Exception as exc:
            logger.exception("mcp_client.connection_failed", error=str(exc))
            await self._locked_disconnect()
            raise MCPClientError(f"Failed to connect to MCP server: {exc}") from exc

    async def disconnect(self) -> None:
        """Terminate the MCP session."""
        async with self._lock:
            await self._locked_disconnect()
            
    async def _locked_disconnect(self) -> None:
        """Internal disconnect that requires the caller to hold the lock."""
        if not self._connected and self._session is None and self._http_cm is None:
            return

        try:
            if self._session_cm:
                await self._session_cm.__aexit__(None, None, None)
            if self._http_cm:
                await self._http_cm.__aexit__(None, None, None)
        except Exception as exc:
            logger.warning("mcp_client.disconnect_error", error=str(exc))
        finally:
            self._session = None
            self._session_cm = None
            self._http_cm = None
            self._connected = False
            self._available_tools = {}
            logger.info("mcp_client.disconnected")

    async def _ensure_connected(self) -> None:
        """Ensure connection is active; reconnect if not."""
        if not self._connected:
            async with self._lock:
                if not self._connected:
                    logger.info("mcp_client.attempting_reconnect")
                    await self._locked_connect()

    async def _refresh_tools(self) -> None:
        """Fetch and cache the list of available tools from the server."""
        if not self._session:
            raise MCPClientError("Not connected")

        response = await self._session.list_tools()
        self._available_tools = {tool.name: tool for tool in response.tools}

    async def list_tools(self) -> list[Tool]:
        """Return the list of available tools, reconnecting/refreshing from server."""
        await self._ensure_connected()
        try:
            # We already refreshed during connect, but this forces a fresh list
            # if we were already connected.
            await self._refresh_tools()
            return self.available_tools
        except Exception as exc:
            logger.exception("mcp_client.list_tools_failed", error=str(exc))
            # Transport failure
            await self.disconnect()
            raise MCPClientError(f"Failed to list tools: {exc}") from exc

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """
        Invoke a tool on the MCP server.

        Args:
            tool_name: The registered tool name.
            arguments: Dict of keyword arguments for the tool.

        Returns:
            The tool's result (deserialized).

        Raises:
            ToolNotFoundError: If tool is not registered.
            ToolInvocationError: If the tool returns an error.
            MCPClientError: If transport/session drops.
        """
        await self._ensure_connected()

        if tool_name not in self._available_tools:
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not found. Available: {list(self._available_tools.keys())}"
            )

        args = arguments or {}
        logger.info("mcp_client.calling_tool", tool=tool_name, args=args)
        
        # We need self._session for type checking/linting inside the try block,
        # but _ensure_connected should guarantee it's not None.
        session = self._session
        if not session:
            raise MCPClientError("Session is none even after connecting")

        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, args),
                timeout=self._settings.agent_tool_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error("mcp_client.tool_call_timeout", tool=tool_name)
            # Timeout is a transport/session failure. Disconnect.
            await self.disconnect()
            raise MCPClientError(
                f"Tool '{tool_name}' timed out after {self._settings.agent_tool_timeout_seconds}s"
            )
        except Exception as exc:
            logger.exception("mcp_client.transport_call_failed", tool=tool_name, error=str(exc))
            # Any other exception here is a transport error (e.g. EOF, connection reset)
            await self.disconnect()
            raise MCPClientError(f"Transport/Session failed calling '{tool_name}': {exc}") from exc

        is_err = getattr(result, "isError", getattr(result, "is_error", False))
        if is_err:
            error_msg = str(result.content)
            logger.error("mcp_client.tool_returned_error", tool=tool_name, error=error_msg)
            # Tool logic error. Do NOT disconnect.
            raise ToolInvocationError(f"Tool '{tool_name}' returned error: {error_msg}")

        # Extract text content from MCP response
        content = result.content
        if content and len(content) > 0:
            first = content[0]
            if hasattr(first, "text"):
                try:
                    parsed = json.loads(first.text)
                    logger.info("mcp_client.tool_success", tool=tool_name)
                    return parsed
                except (json.JSONDecodeError, TypeError):
                    return first.text

        return None

    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()

