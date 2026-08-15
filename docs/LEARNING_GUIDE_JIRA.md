# Jira Implementation Learning Guide

This guide explains the architecture and data flow of the Jira integration in the `AI-Knowledge-Agent` codebase, specifically focusing on the MCP server implementation.

## 1. `models.py`
**What it does:** Defines the Pydantic data models used throughout the Jira integration.
**Why it exists:** Provides strong typing, validation, and a standardized schema (e.g., `JiraTicket`, `JiraSearchResult`) so that the rest of the application doesn't have to guess the shape of the data returning from Jira.
**Important classes:** `JiraTicket`
**Data Flow:** Raw JSON from the Jira API is passed into these models and transformed into validated Python objects.

## 2. `repository.py`
**What it does:** Defines the `JiraRepository` Protocol (interface).
**Why it exists:** Enforces a strict contract that any Jira provider (mock or real) must implement: `get_ticket`, `search_tickets`, and `find_similar_tickets`.
**Important classes:** `JiraRepository` (Protocol)
**Important Python syntax:** Uses `typing.Protocol` to define structural subtyping (duck typing) without requiring inheritance.

## 3. `mock_repository.py`
**What it does:** Implements `JiraRepository` using hardcoded, static dictionaries instead of making network calls.
**Why it exists:** Allows end-to-end testing, frontend development, and local agent validation without requiring real Jira credentials.
**Important classes:** `MockJiraRepository`

## 4. `real_repository.py`
**What it does:** Implements `JiraRepository` by making actual HTTP requests to a real Jira instance.
**Why it exists:** The production adapter for retrieving live operational data.
**Dependencies:** `httpx`, `tenacity`.
**How it works:**
- **async / await:** Used extensively to ensure HTTP requests don't block the main event loop, allowing the MCP server to handle multiple requests concurrently.
- **`httpx.AsyncClient`:** The modern, async HTTP client used to perform `GET` and `POST` (for JQL searches).
- **timeout & retry:** Configures timeouts on `httpx` to fail fast. Uses the `tenacity` library (`@retry`) to automatically retry on transient network errors or `5xx` status codes.
- **status codes:** Explicitly handles `404` (Ticket not found), `401/403` (Auth errors), and `400` (Bad JQL) and maps them to safe, internal exception types.
- **authentication boundary:** Credentials (`email`, `api_token`) are loaded server-side and injected into the `httpx` client's Basic Auth. They NEVER leave this class.
- **custom fields:** Maps obscure Jira custom field IDs (e.g., `customfield_10015`) to human-readable names (e.g., `cluster`) using the `JiraCustomFields` configuration.

## 5. `factory.py`
**What it does:** Inspects the environment configuration and instantiates the correct repository.
**Why it exists:** Provides dependency injection. The rest of the app just asks `get_jira_repository()` and gets back an instance of `JiraRepository` without needing to know if it's the mock or real one.
**Important functions:** `get_jira_repository(settings)`

## 6. `config.py`
**What it does:** Centralized schema for all environment variables (e.g., `JIRA_PROVIDER`, `JIRA_URL`, credentials).
**Why it exists:** Validates configuration at startup using Pydantic. If a required variable is missing, the application crashes immediately instead of failing silently later.

## 7. `jira_tools.py`
**What it does:** Registers the MCP tools (`get_ticket`, `search_tickets`, `find_similar_tickets`) and wires them to the repository.
**Why it exists:** This is the entry point for the MCP protocol. It translates MCP SDK `@mcp.tool()` calls into calls against `JiraRepository`.

## 8. `tests`
**What they do:** Uses `pytest` and `respx` to validate behavior.
**Why they exist:** Proves the application handles success and failure gracefully. `respx` is used to intercept `httpx` requests in memory so we can simulate Jira returning 404s, 500s, or timing out without making actual network requests.

---

### Architecture & Data Flow

```mermaid
flowchart TD
    A[Knowledge Agent (LLM)] -->|Tool Call| B[MCP Client]
    B -->|HTTP/SSE| C[MCP Server jira_tools.py]
    C -->|get_ticket()| D[JiraRepository Protocol]
    D -->|Dependency Injection| E[factory.py]
    
    E -- JIRA_PROVIDER=mock --> F[MockJiraRepository]
    E -- JIRA_PROVIDER=real --> G[RealJiraRepository]
    
    G -->|httpx.AsyncClient| H[Organizational Jira API]
```
