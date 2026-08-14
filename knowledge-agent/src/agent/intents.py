"""Deterministic routing for supported Jira knowledge requests."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

AgentIntentName = Literal[
    "investigate_ticket",
    "get_ticket",
    "search_tickets",
    "find_similar_tickets",
    "capabilities",
    "unsupported",
]

_TICKET_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9_]*-\d+)\b", re.IGNORECASE)
_EXPLICIT_VALUE_PATTERN = re.compile(
    r"\b(?P<name>service|cluster|label|component):(?P<value>[a-zA-Z0-9_.-]+)\b",
    re.IGNORECASE,
)
_SEARCH_PREFIX_PATTERN = re.compile(
    r"^\s*(find|search(?:\s+for)?|list|show\s+me)\s+", re.IGNORECASE
)


@dataclass(frozen=True)
class AgentIntent:
    """Classified user intent and provider-neutral MCP arguments."""

    name: AgentIntentName
    ticket_key: str | None = None
    tool_arguments: dict[str, object] = field(default_factory=dict)


def classify_intent(query: str) -> AgentIntent:
    """Classify supported operational requests without bypassing MCP."""

    normalized = " ".join(query.strip().split())
    lowered = normalized.casefold()
    ticket_match = _TICKET_KEY_PATTERN.search(normalized)
    ticket_key = ticket_match.group(1).upper() if ticket_match else None

    if any(
        phrase in lowered
        for phrase in (
            "what can you help",
            "what can you do",
            "supported capabilities",
            "how can you help",
        )
    ):
        return AgentIntent(name="capabilities")

    if ticket_key and any(word in lowered for word in ("similar", "historical", "related")):
        return AgentIntent(
            name="find_similar_tickets",
            ticket_key=ticket_key,
            tool_arguments={"ticket_key": ticket_key},
        )

    if ticket_key and re.match(r"^\s*(get|show|fetch|retrieve)\b", lowered):
        return AgentIntent(
            name="get_ticket",
            ticket_key=ticket_key,
            tool_arguments={"ticket_key": ticket_key},
        )

    if ticket_key:
        return AgentIntent(
            name="investigate_ticket",
            ticket_key=ticket_key,
            tool_arguments={"ticket_key": ticket_key},
        )

    if any(word in lowered for word in ("find", "search", "incidents", "tickets")):
        return AgentIntent(name="search_tickets", tool_arguments=_search_arguments(normalized))

    return AgentIntent(name="unsupported")


def _search_arguments(query: str) -> dict[str, object]:
    lowered = query.casefold()
    explicit_matches = list(_EXPLICIT_VALUE_PATTERN.finditer(query))
    filter_free_lowered = _EXPLICIT_VALUE_PATTERN.sub(" ", lowered)
    arguments: dict[str, object] = {}
    consumed: set[str] = {
        "find",
        "search",
        "for",
        "list",
        "show",
        "me",
        "all",
        "jira",
        "ticket",
        "tickets",
        "incident",
        "incidents",
        "issue",
        "issues",
        "in",
        "this",
        "that",
        "the",
        "to",
        "with",
    }

    for priority in ("critical", "high", "medium", "low"):
        if re.search(rf"\b{priority}\b", filter_free_lowered):
            arguments["priority"] = priority.title()
            consumed.add(priority)
            break

    platform_aliases = {
        "kafka": "Apache Kafka",
        "redis": "Redis",
        "datapower": "IBM DataPower",
        "eks": "Amazon EKS",
        "aks": "Azure AKS",
    }
    for alias, platform in platform_aliases.items():
        if re.search(rf"\b{alias}\b", filter_free_lowered):
            arguments["platform"] = platform
            consumed.add(alias)
            break

    environment_aliases = {
        "production": "production",
        "prod": "production",
        "staging": "staging",
        "development": "development",
        "dev": "development",
        "test": "test",
    }
    for alias, environment in environment_aliases.items():
        if re.search(rf"\b{alias}\b", filter_free_lowered):
            arguments["environment"] = environment
            consumed.add(alias)
            break

    status_aliases = {
        "resolved": "Resolved",
        "closed": "Closed",
        "open": "Open",
        "investigating": "Investigating",
        "in progress": "In Progress",
    }
    for alias, status in status_aliases.items():
        if alias in filter_free_lowered:
            arguments["status"] = status
            consumed.update(alias.split())
            break

    issue_types = {"incident": "Incident", "problem": "Problem", "change": "Change"}
    for alias, issue_type in issue_types.items():
        if re.search(rf"\b{alias}s?\b", filter_free_lowered):
            arguments["issue_type"] = issue_type
            consumed.update({alias, f"{alias}s"})
            break

    labels: list[str] = []
    components: list[str] = []
    for match in explicit_matches:
        name = match.group("name").casefold()
        value = match.group("value")
        consumed.update({name, value.casefold()})
        if name == "label":
            labels.append(value)
        elif name == "component":
            components.append(value)
        else:
            arguments[name] = value

    if labels:
        arguments["labels"] = labels
    if components:
        arguments["components"] = components

    remaining = _SEARCH_PREFIX_PATTERN.sub("", lowered)
    words = re.findall(r"[a-z0-9_.-]+", remaining)
    text_words = [word for word in words if word not in consumed]
    if "similar" in text_words or "historical" in text_words:
        arguments.setdefault("status", "Resolved")
        text_words = [word for word in text_words if word not in {"similar", "historical"}]
    if text_words:
        arguments["text"] = " ".join(text_words)

    arguments["limit"] = 10
    return arguments
