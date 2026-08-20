"""FastAPI REST and WebSocket entry points for the Knowledge Agent."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.types import Tool as MCPTool
from pydantic import ValidationError
from structlog.contextvars import bind_contextvars, clear_contextvars

from src.agent.agent import KnowledgeAgent
from src.api.models import (
    HealthResponse,
    LLMStatus,
    QueryRequest,
    QueryResponse,
    ToolInfo,
    ToolsResponse,
    WebSocketMessage,
)
from src.core.config import Settings, get_settings
from src.core.logging import configure_logging, get_logger
from src.mcp_client.client import MCPClient, MCPClientError

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_EXPECTED_TOOLS = {"get_ticket", "search_tickets", "find_similar_tickets"}


def _new_request_id(candidate: str | None = None) -> str:
    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())


def _llm_is_configured(app_settings: Settings) -> bool:
    provider = app_settings.llm_provider.strip().casefold()
    if provider == "gemini":
        return bool(app_settings.google_api_key)
    if provider == "openai":
        return bool(app_settings.openai_api_key)
    if provider == "groq":
        return bool(app_settings.groq_api_key)
    return False


class AppState:
    """Concurrency-safe lifecycle and recovery state."""

    def __init__(self) -> None:
        import asyncio

        self.mcp_client: MCPClient | None = None
        self.agent: KnowledgeAgent | None = None
        self._lock = asyncio.Lock()

    async def refresh(self) -> tuple[list[MCPTool], bool]:
        """Actively verify MCP tools and construct the agent when possible."""

        async with self._lock:
            if self.mcp_client is None:
                self.mcp_client = MCPClient()
            if not self.mcp_client.is_connected:
                await self.mcp_client.connect()

            try:
                tools = await self.mcp_client.list_tools()
            except Exception:
                self.agent = None
                raise

            if self.agent is None:
                try:
                    self.agent = KnowledgeAgent(self.mcp_client)
                except Exception as exc:  # noqa: BLE001 - provider initialization boundary
                    logger.error(
                        "api.llm_initialization_failed",
                        error_type=type(exc).__name__,
                    )

            return tools, self.agent is not None

    async def get_agent(self) -> KnowledgeAgent:
        try:
            await self.refresh()
        except MCPClientError as exc:
            raise HTTPException(
                status_code=503,
                detail="The Knowledge Agent is temporarily unavailable.",
            ) from exc

        if self.agent is None:
            raise HTTPException(
                status_code=503,
                detail="The configured LLM provider is unavailable.",
            )
        return self.agent

    async def close(self) -> None:
        if self.mcp_client:
            await self.mcp_client.disconnect()
        self.mcp_client = None
        self.agent = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("api.startup.begin")
    try:
        tools, agent_ready = await app_state.refresh()
        logger.info(
            "api.startup.complete",
            tools=len(tools),
            agent_ready=agent_ready,
        )
    except Exception as exc:  # noqa: BLE001 - keep startup safely degraded
        logger.error("api.startup.degraded", error_type=type(exc).__name__)

    yield

    logger.info("api.shutdown.begin")
    await app_state.close()
    logger.info("api.shutdown.complete")


app = FastAPI(
    title="AI Knowledge Agent API",
    description="Operational Jira Knowledge Agent backed by MCP tools",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = _new_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    clear_contextvars()
    bind_contextvars(request_id=request_id)
    started = perf_counter()
    try:
        response = await call_next(request)
    finally:
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        logger.info(
            "api.request.complete",
            method=request.method,
            path=request.url.path,
            processing_ms=elapsed_ms,
        )
        clear_contextvars()
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    sanitized_errors = [
        {"location": error.get("loc"), "message": error.get("msg"), "type": error.get("type")}
        for error in exc.errors()
    ]
    logger.warning(
        "api.validation_error",
        error_types=[error["type"] for error in sanitized_errors],
        path=request.url.path,
    )
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request parameters.", "errors": sanitized_errors},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "api.internal_error",
        path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    tools = []
    mcp_connected = False
    agent_ready = False
    try:
        tools, agent_ready = await app_state.refresh()
        mcp_connected = app_state.mcp_client is not None and app_state.mcp_client.is_connected
    except Exception as exc:  # noqa: BLE001 - active dependency health boundary
        logger.warning("api.health.mcp_probe_failed", error_type=type(exc).__name__)

    tool_names = sorted(tool.name for tool in tools)
    expected_tools_available = set(tool_names) == _EXPECTED_TOOLS
    configured = _llm_is_configured(settings)
    healthy = mcp_connected and expected_tools_available and configured and agent_ready
    return HealthResponse(
        status="healthy" if healthy else "degraded",
        mcp_connected=mcp_connected,
        available_tools=tool_names,
        llm=LLMStatus(
            provider=settings.llm_provider,
            model=settings.llm_model,
            configured=configured and agent_ready,
        ),
        version=app.version,
    )


@app.get("/tools", response_model=ToolsResponse, tags=["Tools"])
async def list_tools() -> ToolsResponse:
    try:
        tools, _ = await app_state.refresh()
    except MCPClientError as exc:
        raise HTTPException(status_code=503, detail="MCP Server not connected") from exc

    tool_infos = [
        ToolInfo(
            name=tool.name,
            description=tool.description,
            parameters=tool.input_schema,
        )
        for tool in tools
    ]
    return ToolsResponse(tools=tool_infos, count=len(tool_infos))


_ERROR_STATUS_CODES = {
    "invalid_ticket_key": 422,
    "unsupported_request": 422,
    "ticket_not_found": 404,
    "llm_timeout": 504,
    "query_timeout": 504,
    "llm_provider_unavailable": 503,
    "knowledge_service_unavailable": 503,
    "jira_unavailable": 503,
    "llm_invalid_response": 502,
    "invalid_tool_response": 502,
}


@app.post("/query", response_model=QueryResponse, tags=["Agent"])
async def query(request: QueryRequest, raw_request: Request, response: Response) -> QueryResponse:
    agent = await app_state.get_agent()
    request_id = raw_request.state.request_id
    logger.info(
        "api.query.received",
        query_length=len(request.query),
        has_session_id=request.session_id is not None,
    )
    result = await agent.process_query(request.query)
    if not result["success"]:
        response.status_code = _ERROR_STATUS_CODES.get(result.get("error_code"), 502)

    return QueryResponse(
        success=result["success"],
        error_code=result.get("error_code"),
        error=result["error"],
        structured_response=result["structured_response"],
        timestamp=result["timestamp"],
        processing_ms=result["processing_ms"],
        request_id=request_id,
    )


def _websocket_origin_allowed(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if not origin:
        return True
    if origin in settings.api_cors_origins:
        return True

    parsed = urlsplit(origin)
    return parsed.scheme in {"http", "https"} and parsed.netloc == websocket.headers.get("host")


async def _send_ws_error(
    websocket: WebSocket, message: str, request_id: str | None = None
) -> None:
    await websocket.send_json(
        {
            "type": "error",
            "payload": {"message": message, "request_id": request_id},
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    if not _websocket_origin_allowed(websocket):
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    await websocket.accept()
    logger.info("ws.client_connected")
    try:
        while True:
            raw = await websocket.receive_text()
            request_id: str | None = None
            try:
                decoded = json.loads(raw)
                if not isinstance(decoded, dict):
                    raise TypeError("Message must be an object")
            except (json.JSONDecodeError, ValueError, TypeError):
                await _send_ws_error(websocket, "Invalid message format")
                continue

            message_type = decoded.get("type")
            if message_type not in {"query", "ping"}:
                await _send_ws_error(websocket, "Unsupported message type")
                continue

            try:
                message = WebSocketMessage.model_validate(decoded)
            except ValidationError:
                await _send_ws_error(websocket, "Invalid message format")
                continue

            request_id = _new_request_id(str(message.payload.get("request_id") or ""))
            if message.type == "ping":
                await websocket.send_json(
                    {"type": "pong", "payload": {"request_id": request_id}}
                )
                continue

            try:
                query_request = QueryRequest(
                    query=message.payload.get("query"),
                    session_id=message.payload.get("session_id"),
                )
            except ValidationError:
                await _send_ws_error(websocket, "Invalid query", request_id)
                continue

            clear_contextvars()
            bind_contextvars(request_id=request_id)
            try:
                agent = await app_state.get_agent()
            except HTTPException:
                await _send_ws_error(
                    websocket,
                    "The Knowledge Agent is temporarily unavailable.",
                    request_id,
                )
                continue

            await websocket.send_json(
                {"type": "thinking", "payload": {"request_id": request_id}}
            )
            result = await agent.process_query(query_request.query)
            await websocket.send_json(
                {
                    "type": "response",
                    "payload": {
                        **result,
                        "request_id": request_id,
                    },
                }
            )
    except WebSocketDisconnect:
        logger.info("ws.client_disconnected")
    except Exception as exc:  # noqa: BLE001 - WebSocket safety boundary
        logger.error("ws.unexpected_error", error_type=type(exc).__name__)
        try:
            await _send_ws_error(websocket, "Internal server error")
        except Exception:  # noqa: BLE001 - socket may already be closed
            logger.warning("ws.error_delivery_failed")
    finally:
        clear_contextvars()
