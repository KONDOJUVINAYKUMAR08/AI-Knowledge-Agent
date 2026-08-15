"""Tests for the Real Jira Repository using respx to mock HTTP calls."""

import httpx
import pytest
import respx

from src.core.config import Settings
from src.jira.models import JiraSearchCriteria
from src.jira.real_repository import RealJiraRepository
from src.jira.repository import InvalidJiraRequestError, JiraRepositoryError, JiraTicketNotFoundError

@pytest.fixture
def settings() -> Settings:
    return Settings(
        jira_provider="real",
        jira_base_url="https://jira.example.com",
        jira_user_email="test@example.com",
        jira_api_token="token123",
        jira_custom_field_service="customfield_10001",
    )

@pytest.fixture
def repository(settings: Settings) -> RealJiraRepository:
    return RealJiraRepository(settings)

@pytest.mark.asyncio
async def test_real_repository_requires_config() -> None:
    bad_settings = Settings(jira_provider="real", jira_base_url=None, jira_api_token=None, jira_user_email=None)
    with pytest.raises(ValueError, match="Real Jira integration requires"):
        RealJiraRepository(bad_settings)

@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_success(repository: RealJiraRepository) -> None:
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1002").mock(
        return_value=httpx.Response(200, json={
            "id": "10002",
            "key": "PROJ-1002",
            "fields": {
                "summary": "Test issue",
                "customfield_10001": "auth-service"
            }
        })
    )
    
    ticket = await repository.get_ticket("PROJ-1002")
    assert ticket.key == "PROJ-1002"
    assert ticket.summary == "Test issue"
    assert ticket.service == "auth-service"

@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_not_found(repository: RealJiraRepository) -> None:
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-9999").mock(
        return_value=httpx.Response(404, json={"errorMessages": ["Issue does not exist"]})
    )
    with pytest.raises(JiraTicketNotFoundError):
        await repository.get_ticket("PROJ-9999")

@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_400_error(repository: RealJiraRepository) -> None:
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1002").mock(
        return_value=httpx.Response(400, json={"errorMessages": ["Bad Request"]})
    )
    with pytest.raises(InvalidJiraRequestError):
        await repository.get_ticket("PROJ-1002")

@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_401_error(repository: RealJiraRepository) -> None:
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1002").mock(
        return_value=httpx.Response(401, json={"errorMessages": ["Unauthorized"]})
    )
    with pytest.raises(JiraRepositoryError, match="HTTP 401"):
        await repository.get_ticket("PROJ-1002")

@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_timeout(repository: RealJiraRepository) -> None:
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1002").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )
    with pytest.raises(JiraRepositoryError, match="request timed out"):
        await repository.get_ticket("PROJ-1002")

@pytest.mark.asyncio
@respx.mock
async def test_search_tickets(repository: RealJiraRepository) -> None:
    respx.post("https://jira.example.com/rest/api/3/search").mock(
        return_value=httpx.Response(200, json={
            "issues": [
                {
                    "key": "PROJ-1002",
                    "fields": {"summary": "Issue 1"}
                }
            ]
        })
    )
    criteria = JiraSearchCriteria(text="Test", service="auth", labels=["critical"])
    tickets = await repository.search_tickets(criteria)
    assert len(tickets) == 1
    assert tickets[0].key == "PROJ-1002"

@pytest.mark.asyncio
@respx.mock
async def test_find_similar_tickets(repository: RealJiraRepository) -> None:
    # First it calls get_ticket
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1002").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1002",
            "fields": {"summary": "Test issue"}
        })
    )
    # Then it calls search
    respx.post("https://jira.example.com/rest/api/3/search").mock(
        return_value=httpx.Response(200, json={
            "issues": [
                {
                    "key": "PROJ-901",
                    "fields": {"summary": "Similar issue", "customfield_10001": "resolution found"}
                }
            ]
        })
    )
    
    matches = await repository.find_similar_tickets("PROJ-1002")
    assert len(matches) == 1
    assert matches[0].ticket.key == "PROJ-901"
