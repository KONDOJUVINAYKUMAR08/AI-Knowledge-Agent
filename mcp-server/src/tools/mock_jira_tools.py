"""
Mock Jira ticket tools.

Tools: get_ticket, search_tickets, find_similar_tickets
"""

import asyncio
import re
from collections import Counter
from datetime import UTC, datetime, timedelta

from mcp.server.mcpserver import MCPServer

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_MOCK_USERS = [
    {"account_id": "user-001", "display_name": "Alice Chen", "email": "alice.chen@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=alice"},
    {"account_id": "user-002", "display_name": "Bob Martinez", "email": "bob.martinez@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=bob"},
    {"account_id": "user-003", "display_name": "Carol Singh", "email": "carol.singh@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=carol"},
    {"account_id": "user-004", "display_name": "David Kim", "email": "david.kim@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=david"},
]

_MOCK_TICKETS = {
    "PROJ-901": {
        "id": "9001", "key": "PROJ-901",
        "summary": "Intermittent 503 errors during traffic spike",
        "description": "During yesterday's marketing campaign, the API gateway returned 503 Service Unavailable for about 2% of requests. Logs show database connection timeouts.",
        "status": {"name": "Done", "category": "done", "color": "#00875A"},
        "priority": {"name": "Critical", "icon": "🔥"},
        "issue_type": {"name": "Bug", "icon": "🐛"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "assignee": _MOCK_USERS[2], "reporter": _MOCK_USERS[3],
        "labels": ["production", "database", "incident", "performance"],
        "components": ["Database", "Backend API"],
        "service": "postgres-cluster", "environment": "prod",
        "resolution": "Increased PgBouncer pool_size from 50 to 150 and added strict 5s connection timeouts in the application layer to prevent queuing.",
        "created": (datetime.now(UTC) - timedelta(days=180)).isoformat(),
        "updated": (datetime.now(UTC) - timedelta(days=175)).isoformat(),
    },
    "PROJ-902": {
        "id": "9002", "key": "PROJ-902",
        "summary": "Database CPU at 100% due to missing index on users table",
        "description": "The users query by email is doing a full table scan, causing CPU spikes.",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "High"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform"},
        "labels": ["database", "performance"],
        "components": ["Database"],
        "resolution": "Added concurrent index on users(email). CPU dropped to 15%.",
        "created": (datetime.now(UTC) - timedelta(days=160)).isoformat(),
    },
    "PROJ-903": {
        "id": "9003", "key": "PROJ-903",
        "summary": "OAuth token refresh failing for iOS clients",
        "description": "iOS app is randomly logging users out. Refresh tokens are being rejected with 'invalid_grant' due to missing PKCE challenge.",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "High"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform"},
        "labels": ["security", "authentication", "mobile"],
        "components": ["Auth Service"],
        "resolution": "Fixed the S256 PKCE verification logic in the Auth Service which was failing when base64 padding was missing.",
        "created": (datetime.now(UTC) - timedelta(days=150)).isoformat(),
    },
    "PROJ-904": {
        "id": "9004", "key": "PROJ-904",
        "summary": "GraphQL query timeout on deep nested relationships",
        "description": "Users can craft malicious GraphQL queries with 10+ levels of nesting causing the server to OOM or timeout.",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "High"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform"},
        "labels": ["api", "graphql", "security"],
        "components": ["API Gateway"],
        "resolution": "Implemented graphql-depth-limit set to 5 and added query complexity scoring.",
        "created": (datetime.now(UTC) - timedelta(days=140)).isoformat(),
    },
    "PROJ-905": {
        "id": "9005", "key": "PROJ-905",
        "summary": "Design system buttons lack accessible contrast in dark mode",
        "description": "Primary buttons in dark mode have a contrast ratio of 3.1:1, failing WCAG AA (4.5:1).",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "Medium"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform"},
        "labels": ["design-system", "frontend", "accessibility"],
        "components": ["Design System"],
        "resolution": "Updated --color-primary in dark theme from #3182ce to #63b3ed.",
        "created": (datetime.now(UTC) - timedelta(days=130)).isoformat(),
    },
    "PROJ-906": {
        "id": "9006", "key": "PROJ-906",
        "summary": "Mobile login crash on Face ID cancellation",
        "description": "App crashes if user cancels the Face ID prompt on iOS.",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "High"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform"},
        "labels": ["mobile", "ui"],
        "components": ["Mobile App"],
        "resolution": "Caught LAErrorUserCancel and returned user to password fallback screen.",
        "created": (datetime.now(UTC) - timedelta(days=120)).isoformat(),
    },
    "PROJ-907": {
        "id": "9007", "key": "PROJ-907",
        "summary": "Memory leak in API Gateway",
        "description": "RSS of the API gateway process grows by ~100MB per hour until OOM kill.",
        "status": {"name": "Open", "category": "new"},
        "priority": {"name": "High"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform"},
        "labels": ["production", "performance", "api"],
        "components": ["API Gateway"],
        "created": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
    },
    "PROJ-1001": {
        "id": "10001", "key": "PROJ-1001",
        "summary": "Implement OAuth2 authentication flow with PKCE",
        "description": "We need to implement a secure OAuth2 authentication flow using PKCE.",
        "status": {"name": "In Progress", "category": "indeterminate", "color": "#0052CC"},
        "priority": {"name": "High", "icon": "🔴"},
        "issue_type": {"name": "Story", "icon": "📗"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["security", "authentication", "backend"],
        "components": ["Auth Service", "API Gateway"],
        "created": (datetime.now(UTC) - timedelta(days=14)).isoformat(),
    },
    "PROJ-1002": {
        "id": "10002", "key": "PROJ-1002",
        "summary": "Database connection pool exhaustion under load",
        "description": "Production is experiencing connection pool exhaustion during peak traffic (> 5000 req/min). The PostgreSQL max_connections is set to 100 and we're hitting the limit.",
        "status": {"name": "Open", "category": "new", "color": "#42526E"},
        "priority": {"name": "Critical", "icon": "🔥"},
        "issue_type": {"name": "Bug", "icon": "🐛"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["production", "database", "performance", "incident"],
        "components": ["Database", "Backend API"],
        "service": "postgres-cluster", "environment": "prod",
        "created": (datetime.now(UTC) - timedelta(hours=6)).isoformat(),
        "comments": [{"body": "Escalating to P0. This is affecting 15% of users."}]
    },
    "PROJ-1003": {
        "id": "10003", "key": "PROJ-1003",
        "summary": "Add dark mode support to the design system",
        "description": "Implement comprehensive dark mode support.",
        "status": {"name": "Done", "category": "done", "color": "#00875A"},
        "priority": {"name": "Medium", "icon": "🟡"},
        "issue_type": {"name": "Feature", "icon": "⭐"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["design-system", "frontend", "accessibility"],
        "components": ["Design System", "Frontend"],
        "created": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
    },
    "PROJ-1004": {
        "id": "10004", "key": "PROJ-1004",
        "summary": "Migrate from REST to GraphQL for the product catalog API",
        "description": "The product catalog REST API has grown to 87 endpoints.",
        "status": {"name": "In Review", "category": "indeterminate", "color": "#FF8B00"},
        "priority": {"name": "High", "icon": "🔴"},
        "issue_type": {"name": "Epic", "icon": "🌟"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["api", "graphql", "migration", "backend"],
        "components": ["Product Catalog", "API Gateway"],
        "created": (datetime.now(UTC) - timedelta(days=45)).isoformat(),
    },
    "PROJ-1005": {
        "id": "10005", "key": "PROJ-1005",
        "summary": "Mobile login screen redesign",
        "description": "Redesign the mobile login screen following the new brand guidelines.",
        "status": {"name": "Backlog", "category": "new", "color": "#42526E"},
        "priority": {"name": "Low", "icon": "🟢"},
        "issue_type": {"name": "Story", "icon": "📗"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["mobile", "ui", "design"],
        "components": ["Mobile App"],
        "created": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
    },
    "PROJ-908": {
        "id": "9008", "key": "PROJ-908",
        "summary": "Database connection pool exhaustion during backup",
        "description": "Production database connection pool exhaustion timeout when running pg_dump.",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "Critical"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["production", "database", "incident"],
        "components": ["Database", "Backend API"],
        "service": "postgres-cluster", "environment": "prod",
        "resolution": "Increased pool_size and excluded backup connections.",
        "created": (datetime.now(UTC) - timedelta(days=60)).isoformat(),
    },
    "PROJ-909": {
        "id": "9009", "key": "PROJ-909",
        "summary": "Please help with this issue when you can",
        "description": "I need help with this. Could you please look at it when you have time?",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "Low"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["help"],
        "components": ["Unknown"],
        "created": (datetime.now(UTC) - timedelta(days=50)).isoformat(),
    },
    "PROJ-910": {
        "id": "9010", "key": "PROJ-910",
        "summary": "Frontend performance degradation",
        "description": "The UI is slow.",
        "status": {"name": "Done", "category": "done"},
        "priority": {"name": "High"},
        "issue_type": {"name": "Bug"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "labels": ["production", "database", "performance", "incident"],
        "components": ["Frontend"],
        "created": (datetime.now(UTC) - timedelta(days=40)).isoformat(),
    },
}

def register_mock_jira_tools(mcp: MCPServer) -> None:
    @mcp.tool(
        name="get_ticket",
        description="Retrieve a mock Jira ticket by its ID (e.g., PROJ-1002)."
    )
    async def get_ticket(ticket_id: str) -> dict:
        ticket = _MOCK_TICKETS.get(ticket_id.upper())
        if not ticket:
            return {"error": f"Ticket '{ticket_id}' not found in mock data store."}
        return {"ticket": ticket, "source": "mock"}

    @mcp.tool(
        name="search_tickets",
        description="Search mock Jira tickets by keyword, status, priority, or label."
    )
    async def search_tickets(query: str = "", status: str = "", priority: str = "", label: str = "") -> dict:
        results = []
        for ticket in _MOCK_TICKETS.values():
            match = True
            if query and query.lower() not in (ticket.get("summary", "") + " " + ticket.get("description", "")).lower():
                match = False
            if status and status.lower() != ticket.get("status", {}).get("name", "").lower():
                match = False
            if priority and priority.lower() != ticket.get("priority", {}).get("name", "").lower():
                match = False
            if label and label.lower() not in [l.lower() for l in ticket.get("labels", [])]:
                match = False
            if match:
                results.append(ticket)
        return {"tickets": results, "count": len(results), "source": "mock"}

    @mcp.tool(
        name="find_similar_tickets",
        description="Find historical mock Jira tickets similar to a given ticket ID based on keywords, components, and labels."
    )
    async def find_similar_tickets(ticket_id: str) -> dict:
        target = _MOCK_TICKETS.get(ticket_id.upper())
        if not target:
            return {"error": f"Target ticket '{ticket_id}' not found."}
        
        def extract_words(text):
            if not text: return set()
            words = re.findall(r'\b\w+\b', text.lower())
            stop_words = {
                "the", "is", "at", "which", "on", "and", "a", "an", "to", "in", 
                "of", "for", "with", "from", "this", "that", "please", "help", 
                "when", "how", "can", "could", "need", "wants", "it", "we", "they",
                "are", "be", "have", "has", "do", "does", "did", "but", "by", "or",
                "as", "if", "what", "where", "why", "about", "there", "their", "you", "your"
            }
            return set(w for w in words if w not in stop_words and len(w) > 2)

        target_summary_words = extract_words(target.get("summary", ""))
        target_desc_words = extract_words(target.get("description", ""))
        target_labels = set(l.lower() for l in target.get("labels", []))
        target_components = set(c.lower() for c in target.get("components", []))
        target_service = target.get("service")
        
        scores = []
        for key, t in _MOCK_TICKETS.items():
            if key == target["key"]:
                continue
                
            score = 0
            
            # Summary match (Weight: 3)
            t_summary_words = extract_words(t.get("summary", ""))
            score += len(target_summary_words & t_summary_words) * 3
            
            # Description match (Weight: 1)
            t_desc_words = extract_words(t.get("description", ""))
            score += len(target_desc_words & t_desc_words) * 1
            
            # Labels match (Weight: 2)
            t_labels = set(l.lower() for l in t.get("labels", []))
            score += len(target_labels & t_labels) * 2
            
            # Components match (Weight: 4)
            t_comps = set(c.lower() for c in t.get("components", []))
            score += len(target_components & t_comps) * 4
            
            # Service match (Weight: 5)
            if target_service and target_service == t.get("service"):
                score += 5
                
            if score > 0:
                scores.append({"ticket": t, "score": score, "key": key})
                
        # Deterministic sorting: by score descending, then by key ascending
        scores.sort(key=lambda x: (-x["score"], x["key"]))
        
        top_similar = [s["ticket"] for s in scores[:3]]
        
        return {"tickets": top_similar, "source": "mock"}
