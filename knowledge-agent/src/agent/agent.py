"""
Knowledge Agent — LangGraph implementation.

Uses a deterministic state graph:
START -> Understand Request -> Identify Ticket -> Retrieve Context -> LLM Analysis -> Generate Structured Response -> END
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.core.logging import get_logger
from src.mcp_client.client import MCPClient, MCPClientError, ToolInvocationError
from src.agent.llm_factory import create_llm

logger = get_logger(__name__)
settings = get_settings()

_TICKET_ID_PATTERN = re.compile(r"\b([A-Z]+-\d+)\b", re.IGNORECASE)


class AgentResponseSchema(BaseModel):
    """Structured response required from the LLM."""
    ticket_summary: str = Field(description="Summary of the ticket")
    what_we_know: str = Field(description="Bullet points of known facts about the ticket")
    similar_historical_tickets: str = Field(description="Details of similar historical tickets")
    previous_resolution: str = Field(description="How similar tickets were previously resolved")
    recommended_investigation: str = Field(description="Suggested steps to investigate")
    missing_information: str = Field(description="Information that is missing from the ticket")
    sources: list[str] = Field(description="List of data sources used")


class AgentState(TypedDict):
    """The state dictionary for the LangGraph workflow."""
    query: str
    ticket_id: str | None
    ticket_data: dict[str, Any] | None
    similar_tickets_data: list[dict[str, Any]] | None
    error: str | None
    structured_response: dict[str, Any] | None
    processing_ms: float
    start_time: float


class KnowledgeAgent:
    """LangGraph-based Knowledge Agent."""

    def __init__(self, mcp_client: MCPClient) -> None:
        self._client = mcp_client
        
        # Initialize LLM with structured output via factory
        llm = create_llm(settings)
        self._llm = llm.with_structured_output(AgentResponseSchema)
        
        # Build LangGraph
        builder = StateGraph(AgentState)
        builder.add_node("understand_request", self._node_understand_request)
        builder.add_node("retrieve_context", self._node_retrieve_context)
        builder.add_node("analyze_and_generate", self._node_analyze_and_generate)
        
        builder.add_edge(START, "understand_request")
        
        # Conditional edge: if ticket found, retrieve context. Else skip to generation (with error).
        builder.add_conditional_edges(
            "understand_request",
            self._route_after_understanding,
            {
                "retrieve": "retrieve_context",
                "generate": "analyze_and_generate"
            }
        )
        
        builder.add_edge("retrieve_context", "analyze_and_generate")
        builder.add_edge("analyze_and_generate", END)
        
        self._graph = builder.compile()
        logger.info("knowledge_agent.initialized")

    def _node_understand_request(self, state: AgentState) -> dict:
        """Parse query to extract ticket ID deterministically."""
        query = state["query"]
        match = _TICKET_ID_PATTERN.search(query)
        ticket_id = match.group(1).upper() if match else None
        
        if not ticket_id:
            return {"error": "No valid ticket ID found in query."}
            
        return {"ticket_id": ticket_id}

    def _route_after_understanding(self, state: AgentState) -> Literal["retrieve", "generate"]:
        if state.get("error") or not state.get("ticket_id"):
            return "generate"
        return "retrieve"

    async def _node_retrieve_context(self, state: AgentState) -> dict:
        """Retrieve ticket and similar tickets via MCP."""
        ticket_id = state["ticket_id"]
        
        try:
            # 1. Get ticket
            ticket_resp = await self._client.call_tool("get_ticket", {"ticket_id": ticket_id})
            if not ticket_resp or "error" in ticket_resp:
                return {"error": ticket_resp.get("error", "Failed to retrieve ticket")}
                
            ticket_data = ticket_resp.get("ticket")
            
            # 2. Get similar tickets
            similar_resp = await self._client.call_tool("find_similar_tickets", {"ticket_id": ticket_id})
            similar_tickets = similar_resp.get("tickets", []) if similar_resp else []
            
            return {
                "ticket_data": ticket_data,
                "similar_tickets_data": similar_tickets
            }
            
        except ToolInvocationError as exc:
            logger.error("agent.tool_error", error=str(exc))
            return {"error": f"Tool execution failed: {exc}"}
        except MCPClientError as exc:
            logger.error("agent.mcp_transport_error", error=str(exc))
            return {"error": f"MCP communication failed (Transport/Session): {exc}"}
        except Exception as exc:
            logger.error("agent.unexpected_error", error=str(exc))
            return {"error": f"Unexpected error during retrieval: {exc}"}

    async def _node_analyze_and_generate(self, state: AgentState) -> dict:
        """Use LLM to analyze context and generate the structured response."""
        if state.get("error") and not state.get("ticket_data"):
            # We failed to get data. Generate a minimal response.
            return {
                "structured_response": {
                    "ticket_summary": "Error",
                    "what_we_know": state["error"],
                    "similar_historical_tickets": "N/A",
                    "previous_resolution": "N/A",
                    "recommended_investigation": "Please provide a valid ticket ID or check connectivity.",
                    "missing_information": "N/A",
                    "sources": ["System"]
                }
            }
            
        # Build prompt
        ticket = state.get("ticket_data", {})
        similar = state.get("similar_tickets_data", [])
        
        system_msg = SystemMessage(content=(
            "You are an AI Knowledge Agent assisting with a support ticket. "
            "You have retrieved the current ticket and a list of similar historical tickets. "
            "Your task is to analyze these and output a structured response. "
            "Never invent facts about the ticket or historical tickets. "
            "Clearly distinguish between retrieved facts, historical data, and your own AI-generated suggested investigation steps."
        ))
        
        context = f"CURRENT TICKET:\n{ticket}\n\nSIMILAR HISTORICAL TICKETS:\n{similar}"
        user_msg = HumanMessage(content=f"User Query: {state['query']}\n\nContext:\n{context}")
        
        try:
            response_obj: AgentResponseSchema = await self._llm.ainvoke([system_msg, user_msg])
            return {"structured_response": response_obj.model_dump()}
        except Exception as exc:
            logger.error("agent.llm_error", error=str(exc))
            return {
                "structured_response": {
                    "ticket_summary": "Error",
                    "what_we_know": "LLM generation failed.",
                    "similar_historical_tickets": "N/A",
                    "previous_resolution": "N/A",
                    "recommended_investigation": str(exc),
                    "missing_information": "N/A",
                    "sources": ["System"]
                }
            }

    async def process_query(self, query: str) -> dict[str, Any]:
        """Process a query end-to-end via LangGraph."""
        start_time = datetime.now(UTC)
        start_ms = start_time.timestamp() * 1000
        
        initial_state = AgentState(
            query=query,
            ticket_id=None,
            ticket_data=None,
            similar_tickets_data=None,
            error=None,
            structured_response=None,
            processing_ms=0.0,
            start_time=start_ms
        )
        
        final_state = await self._graph.ainvoke(initial_state)
        
        now = datetime.now(UTC)
        elapsed_ms = (now.timestamp() * 1000) - start_ms
        
        # Format the response compatible with the previous API shape if needed, 
        # or just return the structured response directly.
        return {
            "success": final_state.get("error") is None,
            "error": final_state.get("error"),
            "structured_response": final_state.get("structured_response"),
            "timestamp": now.isoformat(),
            "processing_ms": round(elapsed_ms, 2)
        }
