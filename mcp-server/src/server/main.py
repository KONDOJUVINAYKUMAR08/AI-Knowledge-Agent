"""
MCP Server entry point.

Initializes the MCPServer, registers all tool modules,
and starts listening on stdio transport.
"""

import asyncio
import sys

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


async def run_async() -> None:
    """Run the MCP server using stdio transport."""
    logger.info("mcp_server.starting", transport="stdio")
    await mcp.run_stdio_async()


def main() -> None:
    """Sync entry point for the MCP server."""
    try:
        asyncio.run(run_async())
    except KeyboardInterrupt:
        logger.info("mcp_server.shutdown", reason="KeyboardInterrupt")
        sys.exit(0)
    except Exception as exc:
        logger.exception("mcp_server.fatal_error", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
