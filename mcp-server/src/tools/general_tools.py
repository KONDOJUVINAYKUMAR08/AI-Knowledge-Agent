"""
General-purpose utility tools.

Tools: hello, current_time
"""

from datetime import UTC, datetime

from mcp.server.mcpserver import MCPServer

from src.core.logging import get_logger

logger = get_logger(__name__)


def register_general_tools(mcp: MCPServer) -> None:
    """Register general-purpose tools on the MCP server."""

    @mcp.tool(
        name="hello",
        description="Returns a greeting message. Use this to verify MCP connectivity.",
    )
    def hello(name: str = "World") -> dict:
        """Return a greeting message for the given name."""
        logger.info("tool.hello.called", name=name)
        return {
            "message": f"Hello, {name}! I am the Knowledge Agent MCP Server.",
            "server_version": "0.1.0",
            "status": "operational",
        }

    @mcp.tool(
        name="current_time",
        description=(
            "Returns the current UTC timestamp in ISO 8601 format. "
            "Use this to get the current date and time."
        ),
    )
    def current_time() -> dict:
        """Return the current UTC timestamp."""
        now = datetime.now(UTC)
        logger.info("tool.current_time.called", timestamp=now.isoformat())
        return {
            "timestamp": now.isoformat(),
            "unix_epoch": int(now.timestamp()),
            "timezone": "UTC",
            "formatted": now.strftime("%A, %B %d, %Y at %H:%M:%S UTC"),
        }
