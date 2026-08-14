"""
MCP Server entry point.

Initializes the MCPServer, registers all tool modules,
and starts listening on Streamable HTTP transport.
"""

import uvicorn
from mcp.server.mcpserver import MCPServer

from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.jira.factory import create_jira_repository
from src.tools.jira_tools import register_jira_tools

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

    repository = create_jira_repository(settings)
    register_jira_tools(mcp, repository)

    logger.info(
        "mcp_server.initialized",
        name=settings.mcp_server_name,
        version=settings.mcp_server_version,
        jira_provider=repository.provider_name,
    )
    return mcp


# Module-level server instance
mcp = create_server()

# The mcp>=1.0.0 (or v2.0.0) SDK natively supports Streamable HTTP for network transport.
app = mcp.streamable_http_app(streamable_http_path="/mcp", host="*")


def main() -> None:
    """Sync entry point for the MCP server."""
    logger.info("mcp_server.starting", transport="streamable_http", port=8001)
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()
