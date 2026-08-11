"""
FastAPI application for the Knowledge Agent.

Provides REST API and WebSocket endpoints for the frontend.
Manages the MCP Client lifecycle as an application dependency.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from src.agent.agent import KnowledgeAgent
from src.api.models import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
    ToolInfo,
    ToolsResponse,
    WebSocketMessage,
)
from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.mcp_client.client import MCPClient

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Application state — shared across requests
# ---------------------------------------------------------------------------

class AppState:
    mcp_client: MCPClient | None = None
    agent: KnowledgeAgent | None = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — connect MCP client on startup, disconnect on shutdown."""
    logger.info("api.startup.begin")

    try:
        client = MCPClient()
        await client.connect()
        app_state.mcp_client = client
        app_state.agent = KnowledgeAgent(client)
        logger.info("api.startup.complete", tools=len(client.available_tools))
    except Exception as exc:
        logger.exception("api.startup.mcp_connection_failed", error=str(exc))
        # Allow app to start even if MCP server fails — health check will reflect this
        app_state.mcp_client = None
        app_state.agent = None

    yield

    logger.info("api.shutdown.begin")
    if app_state.mcp_client:
        await app_state.mcp_client.disconnect()
    logger.info("api.shutdown.complete")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Knowledge Agent API",
    description="Production-grade Knowledge Agent backed by MCP tools",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def require_agent() -> KnowledgeAgent:
    """Dependency that ensures the agent is initialized."""
    if app_state.agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge Agent is not connected. MCP Server may be unavailable.",
        )
    return app_state.agent


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """System health check — reports MCP connectivity and available tools."""
    client = app_state.mcp_client
    connected = client is not None and client.is_connected
    tools = [t.name for t in client.available_tools] if connected and client else []

    return HealthResponse(
        status="healthy" if connected else "degraded",
        mcp_connected=connected,
        available_tools=tools,
        version="0.1.0",
    )


@app.get("/tools", response_model=ToolsResponse, tags=["Tools"])
async def list_tools() -> ToolsResponse:
    """List all available MCP tools."""
    client = app_state.mcp_client
    if not client or not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP Server not connected",
        )

    tools = await client.list_tools()
    tool_infos = [
        ToolInfo(
            name=t.name,
            description=t.description,
            parameters=t.inputSchema,
        )
        for t in tools
    ]
    return ToolsResponse(tools=tool_infos, count=len(tool_infos))


@app.post("/query", response_model=QueryResponse, tags=["Agent"])
async def query(request: QueryRequest) -> QueryResponse:
    """
    Submit a natural language query to the Knowledge Agent.

    The agent will parse intent, select the appropriate MCP tool,
    invoke it, and return the structured result.
    """
    agent = require_agent()
    logger.info("api.query.received", query=request.query, session_id=request.session_id)

    response = await agent.process_query(request.query)

    return QueryResponse(
        success=response["success"],
        error=response["error"],
        structured_response=response["structured_response"],
        timestamp=response["timestamp"],
        processing_ms=response["processing_ms"],
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time agent communication.

    Message format (client → server):
        {"type": "query", "payload": {"query": "...", "session_id": "..."}}

    Message format (server → client):
        {"type": "response", "payload": {...QueryResponse...}}
        {"type": "error", "payload": {"message": "..."}}
    """
    await websocket.accept()
    logger.info("ws.client_connected", client=str(websocket.client))

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = WebSocketMessage(**json.loads(raw))
            except Exception:
                await websocket.send_text(
                    json.dumps({"type": "error", "payload": {"message": "Invalid message format"}})
                )
                continue

            if msg.type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "payload": {}}))
                continue

            if msg.type == "query":
                query_text = msg.payload.get("query", "").strip()
                session_id = msg.payload.get("session_id")

                if not query_text:
                    await websocket.send_text(
                        json.dumps({"type": "error", "payload": {"message": "Query cannot be empty"}})
                    )
                    continue

                agent = app_state.agent
                if not agent:
                    await websocket.send_text(
                        json.dumps({"type": "error", "payload": {"message": "Agent not available"}})
                    )
                    continue

                # Send "thinking" indicator
                await websocket.send_text(
                    json.dumps({"type": "thinking", "payload": {"query": query_text}})
                )

                response = await agent.process_query(query_text)

                await websocket.send_text(
                    json.dumps({
                        "type": "response",
                        "payload": {
                            "success": response["success"],
                            "error": response["error"],
                            "structured_response": response["structured_response"],
                            "timestamp": response["timestamp"],
                            "processing_ms": response["processing_ms"],
                        },
                    })
                )
            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "payload": {"message": f"Unknown message type: {msg.type}"}})
                )

    except WebSocketDisconnect:
        logger.info("ws.client_disconnected", client=str(websocket.client))
    except Exception as exc:
        logger.exception("ws.unexpected_error", error=str(exc))
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "payload": {"message": "Internal server error"}})
            )
        except Exception:
            pass
