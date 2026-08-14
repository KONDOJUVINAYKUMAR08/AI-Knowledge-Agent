"""Normalized Jira domain models shared by Jira repository implementations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JiraUser(BaseModel):
    """Minimal user information required by the Knowledge Agent."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    display_name: str


class JiraComment(BaseModel):
    """A normalized Jira comment."""

    model_config = ConfigDict(frozen=True)

    author: JiraUser
    body: str
    created: str


class JiraHistoryEntry(BaseModel):
    """A relevant normalized Jira change-history entry."""

    model_config = ConfigDict(frozen=True)

    timestamp: str
    author: JiraUser
    field: str
    from_value: str | None = None
    to_value: str


class JiraTicket(BaseModel):
    """Provider-neutral operational Jira ticket representation."""

    model_config = ConfigDict(frozen=True)

    id: str
    key: str
    summary: str
    description: str
    issue_type: str
    status: str
    priority: str
    severity: str
    reporter: JiraUser
    assignee: JiraUser | None
    created: str
    updated: str
    labels: tuple[str, ...] = ()
    components: tuple[str, ...] = ()
    service: str
    environment: str
    platform: str
    cluster: str | None = None
    region: str | None = None
    symptoms: tuple[str, ...] = ()
    comments: tuple[JiraComment, ...] = ()
    history: tuple[JiraHistoryEntry, ...] = ()
    resolution: str | None = None
    affected_version: str | None = None
    root_cause: str | None = None


class JiraSearchCriteria(BaseModel):
    """Search filters that can later be translated to Jira/JQL."""

    text: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=100)
    issue_type: str | None = Field(default=None, max_length=100)
    service: str | None = Field(default=None, max_length=200)
    environment: str | None = Field(default=None, max_length=100)
    platform: str | None = Field(default=None, max_length=200)
    cluster: str | None = Field(default=None, max_length=200)
    labels: tuple[str, ...] = ()
    components: tuple[str, ...] = ()
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator(
        "text",
        "status",
        "priority",
        "issue_type",
        "service",
        "environment",
        "platform",
        "cluster",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator("labels", "components", mode="before")
    @classmethod
    def normalize_collections(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value


class SimilarTicketMatch(BaseModel):
    """A deterministic, explainable historical-ticket match."""

    model_config = ConfigDict(frozen=True)

    ticket: JiraTicket
    similarity_score: int = Field(ge=0, le=100)
    match_reasons: tuple[str, ...]
    historical_resolved: bool
    previous_resolution: str | None
    applicability: str
