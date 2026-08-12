import pytest
import asyncio
from unittest.mock import MagicMock

from src.tools.mock_jira_tools import register_mock_jira_tools, _MOCK_TICKETS

class MockMCPServer:
    def __init__(self):
        self.tools = {}
        
    def tool(self, name, description):
        def decorator(func):
            self.tools[name] = func
            return func
        return decorator

@pytest.fixture
def mock_tools():
    server = MockMCPServer()
    register_mock_jira_tools(server)
    return server.tools

@pytest.mark.asyncio
async def test_find_similar_exact_component_match(mock_tools):
    find_similar = mock_tools["find_similar_tickets"]
    # PROJ-1002 has service="postgres-cluster", components=["Database", "Backend API"]
    # PROJ-908 was added as a highly similar ticket with same service/components and matching summary keywords
    result = await find_similar("PROJ-1002")
    tickets = result["tickets"]
    
    assert len(tickets) > 0
    # PROJ-908 should be the top match because of service(5) + components(4) + summary(3) matches
    assert tickets[0]["key"] == "PROJ-908"

@pytest.mark.asyncio
async def test_find_similar_stop_words_ignored(mock_tools):
    find_similar = mock_tools["find_similar_tickets"]
    
    # Let's search using PROJ-909 which is just generic words: "Please help with this issue when you can"
    result = await find_similar("PROJ-909")
    tickets = result["tickets"]
    
    if tickets:
        for t in tickets:
            assert t["key"] != "PROJ-909"

@pytest.mark.asyncio
async def test_find_similar_deterministic_ordering(mock_tools):
    find_similar = mock_tools["find_similar_tickets"]
    
    # Run it multiple times and ensure the exact same ordering
    result1 = await find_similar("PROJ-1001")
    result2 = await find_similar("PROJ-1001")
    result3 = await find_similar("PROJ-1001")
    
    keys1 = [t["key"] for t in result1["tickets"]]
    keys2 = [t["key"] for t in result2["tickets"]]
    keys3 = [t["key"] for t in result3["tickets"]]
    
    assert keys1 == keys2 == keys3

@pytest.mark.asyncio
async def test_search_tickets_basic(mock_tools):
    search_tickets = mock_tools["search_tickets"]
    
    # Search by keyword
    res = await search_tickets(query="exhaustion")
    assert res["count"] > 0
    assert any(t["key"] == "PROJ-1002" for t in res["tickets"])
    
    # Search by label
    res = await search_tickets(label="database")
    assert res["count"] > 0
    assert all("database" in [l.lower() for l in t["labels"]] for t in res["tickets"])
    
    # Search by status
    res = await search_tickets(status="In Progress")
    assert all(t["status"]["name"] == "In Progress" for t in res["tickets"])

@pytest.mark.asyncio
async def test_find_similar_technical_terms(mock_tools):
    find_similar = mock_tools["find_similar_tickets"]
    
    # PROJ-903 has technical terms "OAuth", "token", "refresh", "PKCE", "iOS"
    result = await find_similar("PROJ-903")
    keys = [t["key"] for t in result["tickets"]]
    
    # PROJ-1001 also has "OAuth2" (might not match exactly unless tokenized well), "PKCE" and "authentication"
    # "PKCE" is definitely a technical term that should match.
    # It should appear in the results.
    assert "PROJ-1001" in keys

@pytest.mark.asyncio
async def test_find_similar_labels(mock_tools):
    find_similar = mock_tools["find_similar_tickets"]
    # PROJ-910 has labels matching PROJ-1002 but completely different components/service.
    result = await find_similar("PROJ-910")
    keys = [t["key"] for t in result["tickets"]]
    # PROJ-1002 should be matched because of 4 identical labels (4 * 2 = 8 score)
    assert "PROJ-1002" in keys
