"""LangGraph Knowledge Agent for operational Jira knowledge requests."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.agent.intents import AgentIntentName, classify_intent
from src.agent.llm_factory import create_llm
from src.core.config import Settings, get_settings
from src.core.logging import get_logger
from src.mcp_client.client import MCPClient, MCPClientError, ToolInvocationError

logger = get_logger(__name__)

_JIRA_KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]*-\d+\b")


class AgentResponseSchema(BaseModel):
    """Seven-section response required from every investigation."""

    ticket_summary: str = Field(description="Verified summary of the current ticket")
    what_we_know: str = Field(description="Known facts retrieved from Jira")
    similar_historical_tickets: str = Field(description="Relevant resolved Jira incidents")
    previous_resolution: str = Field(description="Retrieved resolutions from historical incidents")
    recommended_investigation: str = Field(description="Clearly labelled recommended investigation")
    missing_information: str = Field(description="Evidence missing from the current Jira ticket")
    sources: list[str] = Field(description="Jira ticket keys used as evidence")


class AgentState(TypedDict):
    query: str
    intent: AgentIntentName | None
    ticket_key: str | None
    tool_arguments: dict[str, Any]
    ticket_data: dict[str, Any] | None
    search_results: list[dict[str, Any]] | None
    similar_matches: list[dict[str, Any]] | None
    error_code: str | None
    error_message: str | None
    structured_response: dict[str, Any] | None


class LLMGenerationError(Exception):
    """Safe, categorized LLM failure used inside the agent workflow."""

    def __init__(self, code: str, user_message: str) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


class KnowledgeAgent:
    """Route operational requests to Jira MCP tools and grounded analysis."""

    def __init__(self, mcp_client: MCPClient, settings: Settings | None = None) -> None:
        self._client = mcp_client
        self._settings = settings or get_settings()
        llm = create_llm(self._settings)
        self._llm = llm.with_structured_output(AgentResponseSchema)

        builder = StateGraph(AgentState)
        builder.add_node("understand_request", self._node_understand_request)
        builder.add_node("execute_tools", self._node_execute_tools)
        builder.add_node("generate_response", self._node_generate_response)
        builder.add_edge(START, "understand_request")
        builder.add_conditional_edges(
            "understand_request",
            self._route_after_understanding,
            {"tools": "execute_tools", "generate": "generate_response"},
        )
        builder.add_edge("execute_tools", "generate_response")
        builder.add_edge("generate_response", END)
        self._graph = builder.compile()
        logger.info(
            "knowledge_agent.initialized",
            llm_provider=self._settings.llm_provider,
            llm_model=self._settings.llm_model,
        )

    @property
    def llm_provider(self) -> str:
        return self._settings.llm_provider

    @property
    def llm_model(self) -> str:
        return self._settings.llm_model

    def _node_understand_request(self, state: AgentState) -> dict[str, Any]:
        intent = classify_intent(state["query"])
        logger.info("agent.intent_classified", intent=intent.name)
        return {
            "intent": intent.name,
            "ticket_key": intent.ticket_key,
            "tool_arguments": intent.tool_arguments,
        }

    @staticmethod
    def _route_after_understanding(state: AgentState) -> Literal["tools", "generate"]:
        if state.get("intent") in {
            "investigate_ticket",
            "get_ticket",
            "search_tickets",
            "find_similar_tickets",
        }:
            return "tools"
        return "generate"

    async def _node_execute_tools(self, state: AgentState) -> dict[str, Any]:
        intent = state["intent"]
        arguments = state.get("tool_arguments", {})

        try:
            if intent == "get_ticket":
                response = await self._client.call_tool("get_ticket", arguments)
                error = self._tool_error(response)
                if error:
                    return error
                return {"ticket_data": response["ticket"]}

            if intent == "search_tickets":
                response = await self._client.call_tool("search_tickets", arguments)
                error = self._tool_error(response)
                if error:
                    return error
                return {"search_results": response.get("tickets", [])}

            if intent == "find_similar_tickets":
                response = await self._client.call_tool("find_similar_tickets", arguments)
                error = self._tool_error(response)
                if error:
                    return error
                return {"similar_matches": response.get("matches", [])}

            if intent == "investigate_ticket":
                ticket_response = await self._client.call_tool("get_ticket", arguments)
                error = self._tool_error(ticket_response)
                if error:
                    return error

                similar_response = await self._client.call_tool(
                    "find_similar_tickets", arguments
                )
                error = self._tool_error(similar_response)
                if error:
                    return error

                return {
                    "ticket_data": ticket_response["ticket"],
                    "similar_matches": similar_response.get("matches", []),
                }

        except ToolInvocationError:
            logger.error("agent.mcp_tool_invocation_failed", intent=intent)
            return {
                "error_code": "jira_tool_failed",
                "error_message": "Unable to complete the Jira operation. Please try again.",
            }
        except MCPClientError:
            logger.error("agent.mcp_transport_failed", intent=intent)
            return {
                "error_code": "knowledge_service_unavailable",
                "error_message": "Unable to connect to the knowledge service. Please try again.",
            }
        except Exception as exc:  # noqa: BLE001 - sanitize arbitrary MCP SDK failures
            logger.error(
                "agent.unexpected_tool_failure",
                intent=intent,
                error_type=type(exc).__name__,
            )
            return {
                "error_code": "jira_operation_failed",
                "error_message": "Unable to retrieve Jira information. Please try again.",
            }

        return {
            "error_code": "unsupported_request",
            "error_message": "That request is not supported by the Jira Knowledge Agent.",
        }

    @staticmethod
    def _tool_error(response: Any) -> dict[str, str] | None:
        if isinstance(response, dict) and response.get("success") is False:
            error = response.get("error")
            if isinstance(error, dict):
                code = str(error.get("code") or "jira_operation_failed")
                message = str(error.get("message") or "Unable to complete the Jira operation.")
                return {"error_code": code, "error_message": message}
            return {
                "error_code": "jira_operation_failed",
                "error_message": "Unable to complete the Jira operation.",
            }
        if not isinstance(response, dict):
            return {
                "error_code": "invalid_tool_response",
                "error_message": "The knowledge service returned an invalid response.",
            }
        return None

    async def _node_generate_response(self, state: AgentState) -> dict[str, Any]:
        if state.get("error_code"):
            message = state.get("error_message") or "The Knowledge Agent could not complete the request."
            return {
                "structured_response": self._error_response(
                    message,
                    ticket_key=state.get("ticket_key"),
                )
            }

        intent = state.get("intent")
        if intent == "capabilities":
            return {"structured_response": self._capabilities_response()}
        if intent == "unsupported":
            message = (
                "I can retrieve Jira tickets, search operational incidents, find similar resolved "
                "incidents, and investigate a Jira ticket when you provide its key."
            )
            return {
                "error_code": "unsupported_request",
                "error_message": message,
                "structured_response": self._error_response(message),
            }
        if intent == "get_ticket":
            return {"structured_response": self._ticket_response(state["ticket_data"] or {})}
        if intent == "search_tickets":
            return {
                "structured_response": self._search_response(state.get("search_results") or [])
            }
        if intent == "find_similar_tickets":
            return {
                "structured_response": self._similarity_response(
                    state.get("ticket_key"), state.get("similar_matches") or []
                )
            }
        if intent == "investigate_ticket":
            try:
                response = await self._generate_investigation(
                    state["query"],
                    state.get("ticket_data") or {},
                    state.get("similar_matches") or [],
                )
                return {"structured_response": response.model_dump()}
            except LLMGenerationError as exc:
                return {
                    "error_code": exc.code,
                    "error_message": exc.user_message,
                    "structured_response": self._investigation_fallback_response(
                        state.get("ticket_data") or {},
                        state.get("similar_matches") or [],
                        exc.code,
                    ),
                }

        message = "The Knowledge Agent could not classify this request."
        return {
            "error_code": "unsupported_request",
            "error_message": message,
            "structured_response": self._error_response(message),
        }

    async def _generate_investigation(
        self,
        query: str,
        ticket: dict[str, Any],
        similar_matches: list[dict[str, Any]],
    ) -> AgentResponseSchema:
        system_message = SystemMessage(
            content=(
                "You are an internal operational Jira Knowledge Agent helping a junior engineer. "
                "Use only the supplied Jira evidence. Never claim that you accessed a cluster, "
                "database, Kafka, Redis, DataPower, cloud API, logs, or metrics. The what_we_know "
                "section must contain only verified Jira facts. The similar_historical_tickets and "
                "previous_resolution sections must cite retrieved historical tickets. The "
                "recommended_investigation section must clearly label recommendations and must not "
                "present them as completed actions. State unavailable evidence in missing_information. "
                "Every source must be a supplied Jira key. The sources list must include the current "
                "ticket key and, when historical matches are supplied, the first (highest-ranked) "
                "historical ticket key. Do not mention or cite any Jira key absent from the supplied evidence."
            )
        )
        evidence = json.dumps(
            {"current_ticket": ticket, "similar_historical_matches": similar_matches},
            ensure_ascii=False,
            sort_keys=True,
        )
        user_message = HumanMessage(
            content=f"User request: {query}\n\nRetrieved Jira evidence:\n{evidence}"
        )
        messages = [system_message, user_message]

        last_category = "llm_provider_unavailable"
        attempts = self._settings.llm_max_retries + 1
        for attempt in range(attempts):
            try:
                raw_response = await asyncio.wait_for(
                    self._llm.ainvoke(messages),
                    timeout=self._settings.llm_timeout_seconds,
                )
                try:
                    response = AgentResponseSchema.model_validate(raw_response)
                    if self._response_is_grounded(response, ticket, similar_matches):
                        return response
                    last_category = "llm_invalid_response"
                    logger.warning(
                        "agent.llm_ungrounded_response",
                        attempt=attempt + 1,
                    )
                except ValidationError as exc:
                    last_category = "llm_invalid_response"
                    logger.warning(
                        "agent.llm_invalid_response",
                        attempt=attempt + 1,
                        error_type=type(exc).__name__,
                    )
            except TimeoutError:
                last_category = "llm_timeout"
                logger.warning("agent.llm_timeout", attempt=attempt + 1)
            except Exception as exc:  # noqa: BLE001 - providers expose varied exception types
                last_category = "llm_provider_unavailable"
                logger.warning(
                    "agent.llm_provider_failure",
                    attempt=attempt + 1,
                    error_type=type(exc).__name__,
                )

            if attempt + 1 < attempts:
                delay = self._settings.llm_retry_backoff_seconds * (2**attempt)
                await asyncio.sleep(delay)

        messages_by_category = {
            "llm_timeout": (
                "AI analysis timed out. Verified Jira evidence is shown below."
            ),
            "llm_invalid_response": (
                "AI-generated analysis did not pass response validation. "
                "Verified Jira evidence is shown below."
            ),
            "llm_provider_unavailable": (
                "AI analysis is temporarily unavailable. Verified Jira evidence is shown below."
            ),
        }
        raise LLMGenerationError(last_category, messages_by_category[last_category])

    @staticmethod
    def _response_is_grounded(
        response: AgentResponseSchema,
        ticket: dict[str, Any],
        similar_matches: list[dict[str, Any]],
    ) -> bool:
        current_key = str(ticket.get("key") or "")
        match_keys = {
            str(match.get("ticket", {}).get("key") or "")
            for match in similar_matches
        }
        allowed_keys = {key for key in {current_key, *match_keys} if key}
        required_keys = {current_key} if current_key else set()
        if match_keys:
            first_match_key = str(similar_matches[0].get("ticket", {}).get("key") or "")
            if first_match_key:
                required_keys.add(first_match_key)

        cited_keys = set(response.sources)
        rendered = json.dumps(response.model_dump(), ensure_ascii=False)
        mentioned_keys = set(_JIRA_KEY_PATTERN.findall(rendered))
        return (
            bool(cited_keys)
            and required_keys <= cited_keys
            and cited_keys <= allowed_keys
            and mentioned_keys <= allowed_keys
        )

    @staticmethod
    def _ticket_response(ticket: dict[str, Any]) -> dict[str, Any]:
        key = str(ticket.get("key", "Jira ticket"))
        facts = [
            f"- **Status:** {ticket.get('status', 'Unavailable')}",
            f"- **Priority / severity:** {ticket.get('priority', 'Unavailable')} / {ticket.get('severity', 'Unavailable')}",
            f"- **Service:** {ticket.get('service', 'Unavailable')}",
            f"- **Platform:** {ticket.get('platform', 'Unavailable')}",
            f"- **Environment:** {ticket.get('environment', 'Unavailable')}",
            f"- **Cluster:** {ticket.get('cluster') or 'Unavailable'}",
        ]
        symptoms = ticket.get("symptoms") or []
        if symptoms:
            facts.append(f"- **Symptoms:** {', '.join(str(value) for value in symptoms)}")
        return AgentResponseSchema(
            ticket_summary=f"**Verified Jira ticket {key}:** {ticket.get('summary', 'Summary unavailable')}",
            what_we_know="\n".join(facts),
            similar_historical_tickets="Not requested for this ticket retrieval.",
            previous_resolution=str(ticket.get("resolution") or "No resolution is recorded for this ticket."),
            recommended_investigation=(
                "**Recommended:** Ask the agent to investigate this ticket to retrieve historical "
                "matches and generate grounded investigation guidance."
            ),
            missing_information=(
                "Root cause is not yet recorded." if not ticket.get("root_cause") else "No missing root-cause field."
            ),
            sources=[key],
        ).model_dump()

    @staticmethod
    def _search_response(tickets: list[dict[str, Any]]) -> dict[str, Any]:
        if not tickets:
            return AgentResponseSchema(
                ticket_summary="No Jira tickets matched the requested operational filters.",
                what_we_know="The search completed successfully and returned zero results.",
                similar_historical_tickets="No matching incidents were retrieved.",
                previous_resolution="No historical resolution was retrieved.",
                recommended_investigation="**Recommended:** Broaden or revise the search filters.",
                missing_information="A specific Jira key was not supplied.",
                sources=[],
            ).model_dump()

        lines = [
            (
                f"- **{ticket['key']}** — {ticket['summary']} "
                f"({ticket['status']}, {ticket['service']}, {ticket['environment']})"
            )
            for ticket in tickets
        ]
        resolutions = [
            f"- **{ticket['key']}:** {ticket['resolution']}"
            for ticket in tickets
            if ticket.get("resolution")
        ]
        keys = [str(ticket["key"]) for ticket in tickets]
        return AgentResponseSchema(
            ticket_summary=f"The Jira search returned {len(tickets)} operational ticket(s).",
            what_we_know="\n".join(lines),
            similar_historical_tickets="These are search results, not a similarity ranking.",
            previous_resolution="\n".join(resolutions) or "No resolutions were present in the results.",
            recommended_investigation=(
                "**Recommended:** Open a relevant ticket or request similar incidents for a specific Jira key."
            ),
            missing_information="A target ticket is required for similarity analysis.",
            sources=keys,
        ).model_dump()

    @staticmethod
    def _similarity_response(
        ticket_key: str | None, matches: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not matches:
            return AgentResponseSchema(
                ticket_summary=f"No resolved historical matches were found for {ticket_key or 'the ticket'}.",
                what_we_know="The similarity search completed successfully.",
                similar_historical_tickets="No similar resolved incidents were retrieved.",
                previous_resolution="No historical resolution was retrieved.",
                recommended_investigation="**Recommended:** Investigate the current ticket using its direct evidence.",
                missing_information="Historical comparison evidence is unavailable.",
                sources=[ticket_key] if ticket_key else [],
            ).model_dump()

        match_lines: list[str] = []
        resolution_lines: list[str] = []
        sources = [ticket_key] if ticket_key else []
        for match in matches:
            ticket = match.get("ticket", {})
            key = str(ticket.get("key", "Unknown"))
            reasons = "; ".join(str(reason) for reason in match.get("match_reasons", []))
            match_lines.append(
                f"- **{key}** ({match.get('similarity_score', 0)}%): {ticket.get('summary', '')}. {reasons}"
            )
            resolution_lines.append(
                f"- **{key}:** {match.get('previous_resolution') or 'No resolution recorded.'}"
            )
            sources.append(key)

        return AgentResponseSchema(
            ticket_summary=f"Resolved historical incidents similar to {ticket_key or 'the requested ticket'}.",
            what_we_know="Similarity is based only on normalized Jira operational fields.",
            similar_historical_tickets="\n".join(match_lines),
            previous_resolution="\n".join(resolution_lines),
            recommended_investigation=(
                "**Recommended:** Validate current logs, metrics, configuration, and resource state before "
                "reusing a historical resolution."
            ),
            missing_information="Current runtime telemetry is not available to this Jira Knowledge Agent.",
            sources=[source for source in sources if source],
        ).model_dump()

    @staticmethod
    def _capabilities_response() -> dict[str, Any]:
        return AgentResponseSchema(
            ticket_summary="The Knowledge Agent supports operational Jira knowledge workflows.",
            what_we_know=(
                "- Retrieve a Jira ticket by key\n"
                "- Search operational incidents by service, platform, environment, priority, or text\n"
                "- Find explainable similar resolved incidents\n"
                "- Investigate a ticket using retrieved Jira evidence and historical resolutions"
            ),
            similar_historical_tickets="Similarity analysis requires a Jira ticket key.",
            previous_resolution="Historical resolutions are returned only from retrieved Jira incidents.",
            recommended_investigation=(
                "**Recommended:** Try `Help me understand PROJ-1002` or `Find critical Kafka incidents`."
            ),
            missing_information=(
                "This system does not directly access clusters, logs, metrics, Kafka, Redis, DataPower, or cloud APIs."
            ),
            sources=[],
        ).model_dump()

    @classmethod
    def _investigation_fallback_response(
        cls,
        ticket: dict[str, Any],
        similar_matches: list[dict[str, Any]],
        failure_code: str,
    ) -> dict[str, Any]:
        """Return verified Jira evidence when AI synthesis cannot be accepted."""
        ticket_key = str(ticket.get("key") or "the requested ticket")
        ticket_response = AgentResponseSchema.model_validate(cls._ticket_response(ticket))
        similarity_response = AgentResponseSchema.model_validate(
            cls._similarity_response(ticket_key, similar_matches)
        )
        failure_explanations = {
            "llm_timeout": "AI synthesis timed out before a validated analysis was produced.",
            "llm_invalid_response": (
                "AI synthesis was rejected because it did not satisfy the required response "
                "schema or Jira-source grounding checks."
            ),
            "llm_provider_unavailable": (
                "AI synthesis could not be completed because the configured provider was unavailable."
            ),
        }
        missing_details = [
            failure_explanations.get(
                failure_code,
                "AI synthesis could not be completed or validated.",
            ),
            "Current runtime logs, metrics, traces, and configuration were not supplied to this system.",
        ]
        if not ticket.get("root_cause"):
            missing_details.append("The current ticket does not contain a confirmed root cause.")
        if not ticket.get("resolution"):
            missing_details.append("The current ticket does not contain a recorded resolution.")

        sources = list(
            dict.fromkeys([*ticket_response.sources, *similarity_response.sources])
        )
        return AgentResponseSchema(
            ticket_summary=ticket_response.ticket_summary,
            what_we_know=ticket_response.what_we_know,
            similar_historical_tickets=similarity_response.similar_historical_tickets,
            previous_resolution=similarity_response.previous_resolution,
            recommended_investigation=(
                "**Recommended:** Review the verified Jira facts above, validate current logs, "
                "metrics, traces, configuration, and resource state, and confirm that the current "
                "failure conditions match a historical incident before reusing its resolution."
            ),
            missing_information="\n".join(f"- {detail}" for detail in missing_details),
            sources=sources,
        ).model_dump()

    @staticmethod
    def _error_response(
        message: str,
        *,
        ticket_key: str | None = None,
    ) -> dict[str, Any]:
        summary = (
            f"Unable to retrieve Jira ticket {ticket_key}"
            if ticket_key
            else "Unable to complete the request"
        )
        return AgentResponseSchema(
            ticket_summary=summary,
            what_we_know=f"The operation did not complete successfully: {message}",
            similar_historical_tickets=(
                "Historical similarity analysis was not performed because the requested Jira "
                "evidence could not be retrieved."
            ),
            previous_resolution=(
                "No verified historical resolution is available for this unsuccessful request."
            ),
            recommended_investigation=(
                "**Recommended:** Verify the Jira ticket key and request format, confirm that the "
                "knowledge service is available, and retry the request."
            ),
            missing_information=(
                "Ticket facts, comments, history, runtime telemetry, and historical comparison "
                "evidence could not be retrieved because the Jira operation did not complete."
            ),
            sources=[],
        ).model_dump()

    async def process_query(self, query: str) -> dict[str, Any]:
        """Process one query with an overall timeout and safe error contract."""

        started = datetime.now(UTC)
        initial_state = AgentState(
            query=query,
            intent=None,
            ticket_key=None,
            tool_arguments={},
            ticket_data=None,
            search_results=None,
            similar_matches=None,
            error_code=None,
            error_message=None,
            structured_response=None,
        )

        try:
            final_state = await asyncio.wait_for(
                self._graph.ainvoke(initial_state),
                timeout=self._settings.agent_query_timeout_seconds,
            )
        except TimeoutError:
            logger.error("agent.query_timeout")
            final_state = {
                **initial_state,
                "error_code": "query_timeout",
                "error_message": "The Knowledge Agent timed out. Please try again.",
                "structured_response": self._error_response(
                    "The Knowledge Agent timed out. Please try again."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - final graph safety boundary
            logger.error("agent.query_failed", error_type=type(exc).__name__)
            final_state = {
                **initial_state,
                "error_code": "internal_error",
                "error_message": "The Knowledge Agent is temporarily unavailable. Please try again.",
                "structured_response": self._error_response(
                    "The Knowledge Agent is temporarily unavailable. Please try again."
                ),
            }

        completed = datetime.now(UTC)
        elapsed_ms = (completed - started).total_seconds() * 1000
        error_code = final_state.get("error_code")
        return {
            "success": error_code is None,
            "error_code": error_code,
            "error": final_state.get("error_message"),
            "structured_response": final_state.get("structured_response"),
            "timestamp": completed.isoformat(),
            "processing_ms": round(elapsed_ms, 2),
        }
