"""
Mock Jira ticket tools.

Provides realistic Jira-like ticket data without requiring a real Jira instance.
Designed for drop-in replacement: when real Jira credentials are available,
replace this file with jira_tools.py — the MCP interface stays identical.

Tools: get_mock_ticket, search_mock_tickets, get_mock_project
"""

import asyncio
from datetime import UTC, datetime, timedelta

from mcp.server.mcpserver import MCPServer

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Static mock data store
# ---------------------------------------------------------------------------

_MOCK_USERS = [
    {"account_id": "user-001", "display_name": "Alice Chen", "email": "alice.chen@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=alice"},
    {"account_id": "user-002", "display_name": "Bob Martinez", "email": "bob.martinez@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=bob"},
    {"account_id": "user-003", "display_name": "Carol Singh", "email": "carol.singh@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=carol"},
    {"account_id": "user-004", "display_name": "David Kim", "email": "david.kim@acme.com", "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=david"},
]

_MOCK_TICKETS: dict[str, dict] = {
    "PROJ-1001": {
        "id": "10001",
        "key": "PROJ-1001",
        "summary": "Implement OAuth2 authentication flow with PKCE",
        "description": (
            "We need to implement a secure OAuth2 authentication flow using PKCE "
            "(Proof Key for Code Exchange) for our mobile clients. This should support "
            "both authorization code flow and refresh token rotation.\n\n"
            "Acceptance Criteria:\n"
            "- [ ] Authorization endpoint with PKCE challenge\n"
            "- [ ] Token endpoint with refresh token rotation\n"
            "- [ ] Revocation endpoint\n"
            "- [ ] Unit tests with >80% coverage"
        ),
        "status": {"name": "In Progress", "category": "indeterminate", "color": "#0052CC"},
        "priority": {"name": "High", "icon": "🔴"},
        "issue_type": {"name": "Story", "icon": "📗"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "assignee": _MOCK_USERS[0],
        "reporter": _MOCK_USERS[1],
        "labels": ["security", "authentication", "backend"],
        "components": ["Auth Service", "API Gateway"],
        "story_points": 8,
        "sprint": {"name": "Sprint 42", "state": "active"},
        "created": (datetime.now(UTC) - timedelta(days=14)).isoformat(),
        "updated": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
        "due_date": (datetime.now(UTC) + timedelta(days=7)).date().isoformat(),
        "comments": [
            {
                "author": _MOCK_USERS[1],
                "body": "PKCE spec reference: RFC 7636. Make sure to use S256 method only.",
                "created": (datetime.now(UTC) - timedelta(hours=12)).isoformat(),
            },
            {
                "author": _MOCK_USERS[0],
                "body": "Started implementation. PR #247 up for review.",
                "created": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
            },
        ],
        "linked_issues": [
            {"type": "blocks", "key": "PROJ-1005", "summary": "Mobile login screen"},
        ],
    },
    "PROJ-1002": {
        "id": "10002",
        "key": "PROJ-1002",
        "summary": "Database connection pool exhaustion under load",
        "description": (
            "Production is experiencing connection pool exhaustion during peak traffic "
            "(> 5000 req/min). The PostgreSQL max_connections is set to 100 and we're "
            "hitting the limit.\n\n"
            "Root Cause Analysis:\n"
            "- PgBouncer not configured correctly\n"
            "- Long-running transactions holding connections\n"
            "- No connection timeout configured in application layer"
        ),
        "status": {"name": "Open", "category": "new", "color": "#42526E"},
        "priority": {"name": "Critical", "icon": "🔥"},
        "issue_type": {"name": "Bug", "icon": "🐛"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "assignee": _MOCK_USERS[2],
        "reporter": _MOCK_USERS[3],
        "labels": ["production", "database", "performance", "incident"],
        "components": ["Database", "Backend API"],
        "story_points": None,
        "sprint": {"name": "Sprint 42", "state": "active"},
        "created": (datetime.now(UTC) - timedelta(hours=6)).isoformat(),
        "updated": (datetime.now(UTC) - timedelta(minutes=30)).isoformat(),
        "due_date": datetime.now(UTC).date().isoformat(),
        "comments": [
            {
                "author": _MOCK_USERS[3],
                "body": "Escalating to P0. This is affecting 15% of users.",
                "created": (datetime.now(UTC) - timedelta(hours=5)).isoformat(),
            },
        ],
        "linked_issues": [],
    },
    "PROJ-1003": {
        "id": "10003",
        "key": "PROJ-1003",
        "summary": "Add dark mode support to the design system",
        "description": (
            "Implement comprehensive dark mode support across the entire design system. "
            "Should use CSS custom properties (variables) for seamless switching without "
            "page reload. Must meet WCAG 2.1 AA contrast requirements.\n\n"
            "Scope:\n"
            "- Color token definitions (light + dark palettes)\n"
            "- All 47 base components updated\n"
            "- Storybook documentation\n"
            "- Migration guide for consuming teams"
        ),
        "status": {"name": "Done", "category": "done", "color": "#00875A"},
        "priority": {"name": "Medium", "icon": "🟡"},
        "issue_type": {"name": "Feature", "icon": "⭐"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "assignee": _MOCK_USERS[1],
        "reporter": _MOCK_USERS[0],
        "labels": ["design-system", "frontend", "accessibility"],
        "components": ["Design System", "Frontend"],
        "story_points": 13,
        "sprint": {"name": "Sprint 41", "state": "closed"},
        "created": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
        "updated": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
        "due_date": (datetime.now(UTC) - timedelta(days=3)).date().isoformat(),
        "comments": [
            {
                "author": _MOCK_USERS[1],
                "body": "All components updated. Storybook deployed at design.acme.com/storybook",
                "created": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
            },
        ],
        "linked_issues": [],
    },
    "PROJ-1004": {
        "id": "10004",
        "key": "PROJ-1004",
        "summary": "Migrate from REST to GraphQL for the product catalog API",
        "description": (
            "The product catalog REST API has grown to 87 endpoints with significant "
            "over-fetching and under-fetching issues. Migrating to GraphQL will reduce "
            "payload size by ~60% and eliminate N+1 queries.\n\n"
            "Migration Strategy:\n"
            "1. Schema-first design with code generation\n"
            "2. Run REST and GraphQL in parallel (strangler fig pattern)\n"
            "3. Migrate consumers team by team\n"
            "4. Sunset REST endpoints after 6 months"
        ),
        "status": {"name": "In Review", "category": "indeterminate", "color": "#FF8B00"},
        "priority": {"name": "High", "icon": "🔴"},
        "issue_type": {"name": "Epic", "icon": "🌟"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "assignee": _MOCK_USERS[3],
        "reporter": _MOCK_USERS[2],
        "labels": ["api", "graphql", "migration", "backend"],
        "components": ["Product Catalog", "API Gateway"],
        "story_points": 40,
        "sprint": None,
        "created": (datetime.now(UTC) - timedelta(days=45)).isoformat(),
        "updated": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "due_date": (datetime.now(UTC) + timedelta(days=60)).date().isoformat(),
        "comments": [],
        "linked_issues": [
            {"type": "contains", "key": "PROJ-1001", "summary": "Implement OAuth2 authentication flow"},
        ],
    },
    "PROJ-1005": {
        "id": "10005",
        "key": "PROJ-1005",
        "summary": "Mobile login screen redesign",
        "description": (
            "Redesign the mobile login screen following the new brand guidelines. "
            "Must support biometric authentication (Face ID / Fingerprint) in addition "
            "to standard email/password flow."
        ),
        "status": {"name": "Backlog", "category": "new", "color": "#42526E"},
        "priority": {"name": "Low", "icon": "🟢"},
        "issue_type": {"name": "Story", "icon": "📗"},
        "project": {"key": "PROJ", "name": "Platform Engineering"},
        "assignee": None,
        "reporter": _MOCK_USERS[0],
        "labels": ["mobile", "ui", "design"],
        "components": ["Mobile App"],
        "story_points": 5,
        "sprint": None,
        "created": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
        "updated": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
        "due_date": None,
        "comments": [],
        "linked_issues": [
            {"type": "blocked by", "key": "PROJ-1001", "summary": "Implement OAuth2 authentication flow"},
        ],
    },
}

_MOCK_PROJECT = {
    "key": "PROJ",
    "name": "Platform Engineering",
    "description": "Core platform infrastructure and developer tooling for ACME Corp.",
    "lead": _MOCK_USERS[0],
    "url": "https://jira.acme.com/projects/PROJ",
    "issue_types": ["Story", "Bug", "Feature", "Epic", "Task"],
    "versions": [
        {"name": "v2.0.0", "released": False, "release_date": (datetime.now(UTC) + timedelta(days=30)).date().isoformat()},
        {"name": "v1.5.0", "released": True, "release_date": (datetime.now(UTC) - timedelta(days=30)).date().isoformat()},
    ],
    "stats": {
        "total_issues": len(_MOCK_TICKETS),
        "open": sum(1 for t in _MOCK_TICKETS.values() if t["status"]["category"] == "new"),
        "in_progress": sum(1 for t in _MOCK_TICKETS.values() if t["status"]["category"] == "indeterminate"),
        "done": sum(1 for t in _MOCK_TICKETS.values() if t["status"]["category"] == "done"),
    },
}


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_mock_jira_tools(mcp: MCPServer) -> None:
    """Register mock Jira tools on the MCP server."""

    @mcp.tool(
        name="get_mock_ticket",
        description=(
            "Retrieve a mock Jira ticket by its ID (e.g., PROJ-1001). "
            "Returns full ticket details including status, assignee, comments, and linked issues. "
            "Available tickets: PROJ-1001 through PROJ-1005."
        ),
    )
    async def get_mock_ticket(ticket_id: str) -> dict:
        """Fetch a mock Jira ticket by ID."""
        ticket_id = ticket_id.strip().upper()
        logger.info("tool.get_mock_ticket.called", ticket_id=ticket_id)

        delay_ms = settings.mock_ticket_response_delay_ms
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)

        ticket = _MOCK_TICKETS.get(ticket_id)
        if ticket is None:
            available = list(_MOCK_TICKETS.keys())
            logger.warning("tool.get_mock_ticket.not_found", ticket_id=ticket_id)
            return {
                "error": "TICKET_NOT_FOUND",
                "message": f"Ticket '{ticket_id}' not found in mock data store.",
                "available_tickets": available,
                "hint": "Try one of the available tickets listed above.",
            }

        logger.info("tool.get_mock_ticket.success", ticket_id=ticket_id, status=ticket["status"]["name"])
        return {"ticket": ticket, "source": "mock", "retrieved_at": datetime.now(UTC).isoformat()}

    @mcp.tool(
        name="search_mock_tickets",
        description=(
            "Search mock Jira tickets by keyword, status, priority, or label. "
            "Returns a list of matching tickets. "
            "Parameters: query (keyword string), status (e.g., 'In Progress'), "
            "priority (e.g., 'High'), label (e.g., 'security')."
        ),
    )
    async def search_mock_tickets(
        query: str = "",
        status: str = "",
        priority: str = "",
        label: str = "",
    ) -> dict:
        """Search mock Jira tickets with optional filters."""
        logger.info(
            "tool.search_mock_tickets.called",
            query=query,
            status=status,
            priority=priority,
            label=label,
        )

        results = []
        for ticket in _MOCK_TICKETS.values():
            if query:
                search_text = (ticket["summary"] + " " + ticket["description"]).lower()
                if query.lower() not in search_text:
                    continue
            if status and status.lower() not in ticket["status"]["name"].lower():
                continue
            if priority and priority.lower() not in ticket["priority"]["name"].lower():
                continue
            if label and label.lower() not in [lbl.lower() for lbl in ticket["labels"]]:
                continue

            results.append({
                "key": ticket["key"],
                "summary": ticket["summary"],
                "status": ticket["status"]["name"],
                "priority": ticket["priority"]["name"],
                "issue_type": ticket["issue_type"]["name"],
                "assignee": ticket["assignee"]["display_name"] if ticket["assignee"] else "Unassigned",
                "updated": ticket["updated"],
            })

        logger.info("tool.search_mock_tickets.success", result_count=len(results))
        return {
            "total": len(results),
            "tickets": results,
            "source": "mock",
            "searched_at": datetime.now(UTC).isoformat(),
        }

    @mcp.tool(
        name="get_mock_project",
        description=(
            "Retrieve overview information for the mock Jira project (PROJ). "
            "Returns project metadata, team members, versions, and issue statistics."
        ),
    )
    async def get_mock_project() -> dict:
        """Return the mock Jira project overview."""
        logger.info("tool.get_mock_project.called")
        return {
            "project": _MOCK_PROJECT,
            "team": _MOCK_USERS,
            "source": "mock",
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
