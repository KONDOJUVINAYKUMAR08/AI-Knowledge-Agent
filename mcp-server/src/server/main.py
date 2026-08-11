"""
MCP Server entry point.

Initializes the MCPServer, registers all tool modules,
and starts listening on Streamable HTTP transport.
"""

import sys
import uvicorn
from starlette.applications import Starlette

from mcp.server.mcpserver import MCPServer

from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.tools.general_tools import register_general_tools
from src.tools.mock_jira_tools import register_mock_jira_tools

# Bootstrap logging before anything else
configure_logging()
logger = get_logger(__name__)


def create_server() -> MCPServer:
    """Factory function that creates and configures the MCP server."""
    settings = get_settings()

    mcp = MCPServer(
        name=settings.mcp_server_name,
        version=settings.mcp_server_version,
    )

    # Register all tool modules
    register_general_tools(mcp)
    register_mock_jira_tools(mcp)

    logger.info(
        "mcp_server.initialized",
        name=settings.mcp_server_name,
        version=settings.mcp_server_version,
    )
    return mcp


# Module-level server instance
mcp = create_server()

# The mcp>=1.0.0 (or v2.0.0) SDK natively supports Streamable HTTP for network transport.
app = mcp.streamable_http_app(streamable_http_path="/mcp")


def main() -> None:
    """Sync entry point for the MCP server."""
    logger.info("mcp_server.starting", transport="streamable_http", port=8001)
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()
