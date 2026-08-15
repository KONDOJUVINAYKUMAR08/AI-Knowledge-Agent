"""Real HTTP Jira repository using httpx."""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.logging import get_logger
from src.jira.models import (
    JiraComment,
    JiraHistoryEntry,
    JiraSearchCriteria,
    JiraTicket,
    JiraUser,
    SimilarTicketMatch,
)
from src.jira.repository import (
    InvalidJiraRequestError,
    JiraRepositoryError,
    JiraTicketNotFoundError,
    normalize_ticket_key,
)

if TYPE_CHECKING:
    from src.core.config import Settings


logger = get_logger(__name__)


def _build_jql(criteria: JiraSearchCriteria, settings: Settings) -> str:
    """Build a safe JQL string from search criteria."""
    clauses: list[str] = []

    if criteria.text:
        # Simple text search escape. A true production JQL builder would need robust escaping.
        safe_text = criteria.text.replace('"', '\\"').replace("~", "\\~")
        clauses.append(f'text ~ "{safe_text}"')

    if criteria.status:
        clauses.append(f'status = "{criteria.status}"')

    if criteria.priority:
        clauses.append(f'priority = "{criteria.priority}"')

    if criteria.issue_type:
        clauses.append(f'issuetype = "{criteria.issue_type}"')

    if criteria.service and settings.jira_custom_field_service:
        clauses.append(f'{settings.jira_custom_field_service} = "{criteria.service}"')

    if criteria.environment and settings.jira_custom_field_environment:
        clauses.append(f'{settings.jira_custom_field_environment} = "{criteria.environment}"')

    if criteria.platform and settings.jira_custom_field_platform:
        clauses.append(f'{settings.jira_custom_field_platform} = "{criteria.platform}"')

    if criteria.cluster and settings.jira_custom_field_cluster:
        clauses.append(f'{settings.jira_custom_field_cluster} = "{criteria.cluster}"')

    if criteria.labels:
        label_clauses = [f'labels = "{label}"' for label in criteria.labels]
        if label_clauses:
            clauses.append(f"({' OR '.join(label_clauses)})")

    if criteria.components:
        component_clauses = [f'component = "{comp}"' for comp in criteria.components]
        if component_clauses:
            clauses.append(f"({' OR '.join(component_clauses)})")

    return " AND ".join(clauses) if clauses else "ORDER BY updated DESC"


class RealJiraRepository:
    """Real Jira repository connecting to a live Jira instance over HTTPS."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.jira_base_url or not settings.jira_api_token or not settings.jira_user_email:
            raise ValueError(
                "Real Jira integration requires JIRA_BASE_URL, JIRA_USER_EMAIL, and JIRA_API_TOKEN "
                "to be configured in the environment."
            )

        self.base_url = settings.jira_base_url.rstrip("/")
        
        # We store credentials in memory and create the client per-request or share it.
        # Basic auth string
        auth_string = f"{settings.jira_user_email}:{settings.jira_api_token}"
        self._auth_header = f"Basic {base64.b64encode(auth_string.encode('utf-8')).decode('ascii')}"

        self._timeout = httpx.Timeout(10.0)

    @property
    def provider_name(self) -> str:
        return "real"

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": self._auth_header,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )

    def _handle_httpx_error(self, exc: Exception) -> None:
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 404:
                raise JiraTicketNotFoundError("Jira ticket was not found.")
            if exc.response.status_code == 400:
                raise InvalidJiraRequestError(f"Invalid Jira request: {exc.response.text}")
            logger.error("jira.http_error", status_code=exc.response.status_code)
            raise JiraRepositoryError(f"Jira API returned HTTP {exc.response.status_code}")
        elif isinstance(exc, httpx.TimeoutException):
            logger.error("jira.timeout")
            raise JiraRepositoryError("Jira API request timed out.")
        elif isinstance(exc, httpx.RequestError):
            logger.error("jira.request_error")
            raise JiraRepositoryError("Failed to communicate with Jira API.")
        raise JiraRepositoryError("An unknown error occurred while communicating with Jira.")

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _make_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async with self._get_client() as client:
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code == 429:
                    # Raise a RequestError so tenacity can retry if we wanted to catch 429 specifically,
                    # but for this POC we will just treat 429 as an HTTP error for simplicity if not handled.
                    pass 
                response.raise_for_status()
                return response
            except Exception as e:
                self._handle_httpx_error(e)
                raise  # Should not reach here if _handle_httpx_error raises

    def _parse_ticket(self, data: dict[str, Any]) -> JiraTicket:
        fields = data.get("fields", {})
        
        # Helper to safely extract user fields
        def _parse_user(user_data: dict[str, Any] | None) -> JiraUser | None:
            if not user_data:
                return None
            return JiraUser(
                account_id=user_data.get("accountId", "unknown"),
                display_name=user_data.get("displayName", "Unknown User"),
            )

        # Parse custom fields safely based on config
        def _get_cf(field_name: str | None) -> str | None:
            if not field_name:
                return None
            val = fields.get(field_name)
            if isinstance(val, dict):
                return str(val.get("value", ""))
            return str(val) if val is not None else None

        # Gather comments
        comments_list: list[JiraComment] = []
        for c in fields.get("comment", {}).get("comments", []):
            author = _parse_user(c.get("author"))
            if author:
                comments_list.append(
                    JiraComment(
                        author=author,
                        body=c.get("body", ""),
                        created=c.get("created", ""),
                    )
                )

        reporter = _parse_user(fields.get("reporter")) or JiraUser(account_id="system", display_name="System")

        return JiraTicket(
            id=data.get("id", ""),
            key=data.get("key", ""),
            summary=fields.get("summary", ""),
            description=fields.get("description", "") or "",
            issue_type=fields.get("issuetype", {}).get("name", "Unknown"),
            status=fields.get("status", {}).get("name", "Unknown"),
            priority=fields.get("priority", {}).get("name", "Unknown"),
            severity=fields.get("customfield_10000", "Unknown"), # Example static severity field or fallback
            reporter=reporter,
            assignee=_parse_user(fields.get("assignee")),
            created=fields.get("created", ""),
            updated=fields.get("updated", ""),
            labels=tuple(fields.get("labels", [])),
            components=tuple(comp.get("name") for comp in fields.get("components", []) if isinstance(comp, dict)),
            service=_get_cf(self.settings.jira_custom_field_service) or "unknown",
            environment=_get_cf(self.settings.jira_custom_field_environment) or "unknown",
            platform=_get_cf(self.settings.jira_custom_field_platform) or "unknown",
            cluster=_get_cf(self.settings.jira_custom_field_cluster),
            region=_get_cf(self.settings.jira_custom_field_region),
            symptoms=(), # Requires specific parsing based on org structure
            comments=tuple(comments_list),
            history=(), # History usually requires /changelog endpoint, omitted for brevity here unless requested
            resolution=_get_cf(self.settings.jira_custom_field_resolution),
            affected_version=_get_cf(self.settings.jira_custom_field_affected_version),
            root_cause=_get_cf(self.settings.jira_custom_field_root_cause),
        )

    async def get_ticket(self, ticket_key: str) -> JiraTicket:
        normalized = normalize_ticket_key(ticket_key)
        response = await self._make_request("GET", f"/rest/api/3/issue/{normalized}")
        return self._parse_ticket(response.json())

    async def search_tickets(self, criteria: JiraSearchCriteria) -> list[JiraTicket]:
        jql = _build_jql(criteria, self.settings)
        payload = {
            "jql": jql,
            "maxResults": criteria.limit,
            "fields": ["*all"]  # Alternatively specify precise fields to save bandwidth
        }
        response = await self._make_request("POST", "/rest/api/3/search", json=payload)
        data = response.json()
        return [self._parse_ticket(issue) for issue in data.get("issues", [])]

    async def find_similar_tickets(
        self, ticket_key: str, *, limit: int = 3
    ) -> list[SimilarTicketMatch]:
        """
        Implementation of Phase 6: Similar Incident Strategy.
        Retrieves the target ticket, extracts its text, and performs a JQL search.
        """
        normalized = normalize_ticket_key(ticket_key)
        target = await self.get_ticket(normalized)
        
        # Create a simple text search from summary
        safe_summary = target.summary.replace('"', '\\"').replace("~", "\\~")
        
        # For a real integration, this might be a more sophisticated JQL or call to a vector DB
        jql = f'text ~ "{safe_summary}" AND key != "{target.key}" AND statusCategory = Done ORDER BY created DESC'
        
        payload = {
            "jql": jql,
            "maxResults": limit,
            "fields": ["*all"]
        }
        
        response = await self._make_request("POST", "/rest/api/3/search", json=payload)
        data = response.json()
        
        matches: list[SimilarTicketMatch] = []
        for issue in data.get("issues", []):
            candidate = self._parse_ticket(issue)
            
            # Simple heuristic for similarity score
            score = 50 
            
            matches.append(
                SimilarTicketMatch(
                    ticket=candidate,
                    similarity_score=score,
                    match_reasons=("JQL text match on summary",),
                    historical_resolved=True,
                    previous_resolution=candidate.resolution,
                    applicability="Moderate: based on text similarity.",
                )
            )
            
        return matches
