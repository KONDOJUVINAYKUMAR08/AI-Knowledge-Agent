"""Focused tests for deterministic operational intent classification."""

from src.agent.intents import classify_intent


def test_redis_production_search_extracts_operational_filters():
    intent = classify_intent("Find Redis incidents in production")

    assert intent.name == "search_tickets"
    assert intent.tool_arguments == {
        "platform": "Redis",
        "environment": "production",
        "issue_type": "Incident",
        "limit": 10,
    }


def test_eks_deployment_search_keeps_meaningful_text():
    intent = classify_intent("Search for failed deployments in EKS")

    assert intent.name == "search_tickets"
    assert intent.tool_arguments == {
        "platform": "Amazon EKS",
        "text": "failed deployments",
        "limit": 10,
    }


def test_explicit_filters_are_provider_neutral_tool_arguments():
    intent = classify_intent(
        "Find incidents service:checkout-api cluster:eks-prod label:latency component:gateway"
    )

    assert intent.name == "search_tickets"
    assert intent.tool_arguments == {
        "issue_type": "Incident",
        "service": "checkout-api",
        "cluster": "eks-prod",
        "labels": ["latency"],
        "components": ["gateway"],
        "limit": 10,
    }


def test_ticket_intents_are_not_exact_sentence_hardcoded():
    assert classify_intent("Please retrieve proj-1002 for me").name == "investigate_ticket"
    assert classify_intent("Show me PROJ-1002").name == "get_ticket"
    assert classify_intent("Find related history for PROJ-1002").name == (
        "find_similar_tickets"
    )


def test_capabilities_and_unsupported_intents_are_truthful():
    assert classify_intent("What can you help me with?").name == "capabilities"
    assert classify_intent("Write a poem about databases").name == "unsupported"


def test_keyless_historical_issue_routes_to_resolved_jira_search():
    intent = classify_intent("Show me similar historical incidents for this database issue")

    assert intent.name == "search_tickets"
    assert intent.tool_arguments == {
        "status": "Resolved",
        "issue_type": "Incident",
        "text": "database",
        "limit": 10,
    }
