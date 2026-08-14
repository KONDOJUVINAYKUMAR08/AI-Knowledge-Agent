"""Behavior tests for the provider-neutral mock Jira repository."""

import pytest

from src.jira.mock_repository import build_mock_repository
from src.jira.models import JiraSearchCriteria
from src.jira.repository import InvalidJiraRequestError, JiraTicketNotFoundError


@pytest.fixture
def repository():
    return build_mock_repository()


@pytest.mark.asyncio
async def test_get_ticket_normalizes_key(repository):
    ticket = await repository.get_ticket("  proj-1002 ")

    assert ticket.key == "PROJ-1002"
    assert ticket.service == "postgres-cluster"
    assert ticket.platform == "PostgreSQL"
    assert ticket.environment == "production"
    assert ticket.cluster == "prod-postgres-primary"


@pytest.mark.asyncio
async def test_get_ticket_not_found(repository):
    with pytest.raises(JiraTicketNotFoundError, match="PROJ-9999"):
        await repository.get_ticket("PROJ-9999")


@pytest.mark.asyncio
@pytest.mark.parametrize("ticket_key", ["", "   ", "not-a-ticket", "PROJ", "-1002"])
async def test_get_ticket_rejects_malformed_key(repository, ticket_key):
    with pytest.raises(InvalidJiraRequestError):
        await repository.get_ticket(ticket_key)


@pytest.mark.asyncio
async def test_empty_search_is_deterministic_and_limited(repository):
    criteria = JiraSearchCriteria(limit=5)

    first = await repository.search_tickets(criteria)
    second = await repository.search_tickets(criteria)

    assert [ticket.key for ticket in first] == [ticket.key for ticket in second]
    assert len(first) == 5
    assert first[0].key == "PROJ-1002"


@pytest.mark.asyncio
async def test_search_by_operational_text(repository):
    tickets = await repository.search_tickets(JiraSearchCriteria(text="consumer lag"))

    assert [ticket.key for ticket in tickets] == ["PROJ-903"]


@pytest.mark.asyncio
async def test_search_by_service(repository):
    tickets = await repository.search_tickets(
        JiraSearchCriteria(service="postgres-cluster")
    )

    assert [ticket.key for ticket in tickets] == ["PROJ-1002", "PROJ-908"]


@pytest.mark.asyncio
async def test_search_by_platform_and_environment(repository):
    tickets = await repository.search_tickets(
        JiraSearchCriteria(platform="Apache Kafka", environment="production")
    )

    assert {ticket.key for ticket in tickets} == {"PROJ-903", "PROJ-909"}


@pytest.mark.asyncio
async def test_search_by_cluster(repository):
    tickets = await repository.search_tickets(
        JiraSearchCriteria(cluster="aks-prod-identity")
    )

    assert [ticket.key for ticket in tickets] == ["PROJ-1003"]


@pytest.mark.asyncio
async def test_search_by_labels_and_components(repository):
    tickets = await repository.search_tickets(
        JiraSearchCriteria(labels=("database", "connection-pool"), components=("PostgreSQL",))
    )

    assert [ticket.key for ticket in tickets] == ["PROJ-1002", "PROJ-908", "PROJ-901"]


@pytest.mark.asyncio
async def test_similarity_keeps_proj_908_first(repository):
    matches = await repository.find_similar_tickets("PROJ-1002")

    assert matches[0].ticket.key == "PROJ-908"
    assert matches[0].historical_resolved is True
    assert matches[0].previous_resolution
    assert matches[0].match_reasons
    assert "High:" in matches[0].applicability


@pytest.mark.asyncio
async def test_similarity_ordering_is_deterministic(repository):
    first = await repository.find_similar_tickets("PROJ-1002")
    second = await repository.find_similar_tickets("PROJ-1002")

    assert [(match.ticket.key, match.similarity_score) for match in first] == [
        (match.ticket.key, match.similarity_score) for match in second
    ]


@pytest.mark.asyncio
async def test_dataset_has_normalized_operational_fields(repository):
    tickets = await repository.search_tickets(JiraSearchCriteria(limit=50))

    assert len(tickets) == 15
    for ticket in tickets:
        assert ticket.key
        assert ticket.summary
        assert ticket.description
        assert ticket.issue_type
        assert ticket.status
        assert ticket.priority
        assert ticket.severity
        assert ticket.reporter
        assert ticket.created.endswith("Z")
        assert ticket.updated.endswith("Z")
        assert ticket.service
        assert ticket.environment
        assert ticket.platform
        assert ticket.symptoms
