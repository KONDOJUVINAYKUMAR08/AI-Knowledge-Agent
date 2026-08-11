"""
Shared Pydantic models used across knowledge-agent and mcp-server.

Import from this module in both components to ensure schema consistency.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TicketStatus(BaseModel):
    name: str
    category: str  # "new" | "indeterminate" | "done"
    color: str


class TicketPriority(BaseModel):
    name: str
    icon: str


class TicketIssueType(BaseModel):
    name: str
    icon: str


class AgentUser(BaseModel):
    account_id: str
    display_name: str
    email: str
    avatar_url: str | None = None


class TicketComment(BaseModel):
    author: AgentUser
    body: str
    created: str


class LinkedIssue(BaseModel):
    type: str
    key: str
    summary: str


class Ticket(BaseModel):
    id: str
    key: str
    summary: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    issue_type: TicketIssueType
    project: dict[str, str]
    assignee: AgentUser | None
    reporter: AgentUser
    labels: list[str]
    components: list[str]
    story_points: int | None
    sprint: dict[str, str] | None
    created: str
    updated: str
    due_date: str | None
    comments: list[TicketComment]
    linked_issues: list[LinkedIssue]
